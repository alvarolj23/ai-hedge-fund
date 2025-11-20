"""Queue-based job runner for the AI hedge fund."""

from __future__ import annotations

import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Iterable, Optional

from dotenv import load_dotenv

try:  # pragma: no cover - imported lazily for environments without Azure SDK
    from azure.core.exceptions import AzureError, ResourceExistsError, ServiceRequestError, ServiceResponseError
    from azure.storage.queue import QueueClient, TextBase64EncodePolicy
    from azure.storage.queue._models import QueueMessage
    from azure.storage.queue._message_encoding import DecodeError, TextBase64DecodePolicy
    try:
        from azure.cosmos.exceptions import CosmosHttpResponseError
    except ImportError:  # pragma: no cover
        CosmosHttpResponseError = AzureError  # type: ignore[misc,assignment]
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "The Azure Storage Queue SDK is required to run the queue worker."
        " Install the project with the 'azure-storage-queue' extra."
    ) from exc

import httpx

from src.brokers.execution import dispatch_paper_orders
from src.brokers.portfolio_fetcher import get_alpaca_portfolio
from src.data.cosmos_repository import CosmosRepository
from src.main import run_hedge_fund

logger = logging.getLogger(__name__)


class PoisonMessageError(Exception):
    """Raised when a queue message cannot be processed and should be dead-lettered."""


class FlexibleTextDecodePolicy(TextBase64DecodePolicy):
    """Decode queue messages encoded as base64 while tolerating plain text payloads."""

    def decode(self, content, response):  # type: ignore[override]
        try:
            return super().decode(content, response)
        except Exception:
            # Catch ALL exceptions including DecodeError and AttributeError
            # Messages pushed via CLI or other tooling may already be plain JSON.
            # Fall back to the raw content so we can still process them.
            logger.debug("Failed to decode base64 message, using raw content: %s", content[:100])
            return content


@dataclass(slots=True)
class QueueConfig:
    """Configuration required to connect to Azure Storage Queues."""

    account: str
    queue_name: str
    sas_token: str
    dead_letter_queue_name: str
    visibility_timeout: int = 300
    max_attempts: int = 5
    base_backoff_seconds: float = 2.0
    max_backoff_seconds: float = 30.0

    @classmethod
    def from_environment(cls) -> "QueueConfig":
        """Load queue configuration from environment variables."""

        account = os.getenv("QUEUE_ACCOUNT")
        queue_name = os.getenv("QUEUE_NAME")
        sas_token = os.getenv("QUEUE_SAS")

        if not all([account, queue_name, sas_token]):
            missing = [
                name
                for name, value in [
                    ("QUEUE_ACCOUNT", account),
                    ("QUEUE_NAME", queue_name),
                    ("QUEUE_SAS", sas_token),
                ]
                if not value
            ]
            raise RuntimeError(
                "Missing Azure Storage Queue configuration."
                f" Ensure the following variables are set: {', '.join(missing)}"
            )

        dead_letter_queue = os.getenv("QUEUE_DEAD_LETTER_NAME", f"{queue_name}-deadletter")
        visibility_timeout = int(os.getenv("QUEUE_VISIBILITY_TIMEOUT", "300"))
        max_attempts = int(os.getenv("QUEUE_MAX_ATTEMPTS", "5"))
        base_backoff = float(os.getenv("QUEUE_BACKOFF_SECONDS", "2"))
        max_backoff = float(os.getenv("QUEUE_BACKOFF_MAX_SECONDS", "30"))

        return cls(
            account=account,
            queue_name=queue_name,
            sas_token=sas_token.lstrip("?"),
            dead_letter_queue_name=dead_letter_queue,
            visibility_timeout=visibility_timeout,
            max_attempts=max_attempts,
            base_backoff_seconds=base_backoff,
            max_backoff_seconds=max_backoff,
        )


class QueueWorker:
    """Dequeues hedge-fund jobs, orchestrates processing, and reports completion."""

    RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
        ServiceRequestError,
        ServiceResponseError,
        AzureError,
        CosmosHttpResponseError,  # type: ignore[arg-type]
        httpx.HTTPError,
        TimeoutError,
    )

    def __init__(
        self,
        queue_client: QueueClient,
        repository: CosmosRepository,
        *,
        dead_letter_client: Optional[QueueClient] = None,
        config: Optional[QueueConfig] = None,
    ) -> None:
        self.queue_client = queue_client
        self.repository = repository
        self.dead_letter_client = dead_letter_client
        self.config = config or QueueConfig.from_environment()

    @classmethod
    def from_environment(cls) -> "QueueWorker":
        """Create a worker using environment variables."""

        config = QueueConfig.from_environment()
        account_url = f"https://{config.account}.queue.core.windows.net"

        encode_policy = TextBase64EncodePolicy()
        decode_policy = FlexibleTextDecodePolicy()

        queue_client = QueueClient(
            account_url=account_url,
            queue_name=config.queue_name,
            credential=config.sas_token,
            message_encode_policy=encode_policy,
            message_decode_policy=decode_policy,
        )

        dead_letter_client: Optional[QueueClient] = None
        try:
            dead_letter_client = QueueClient(
                account_url=account_url,
                queue_name=config.dead_letter_queue_name,
                credential=config.sas_token,
                message_encode_policy=encode_policy,
                message_decode_policy=decode_policy,
            )
            dead_letter_client.create_queue()
        except ResourceExistsError:
            pass
        except AzureError as exc:
            logger.warning("Unable to create or connect to dead-letter queue: %s", exc, exc_info=True)
            dead_letter_client = None

        repository = CosmosRepository.from_environment()
        return cls(
            queue_client=queue_client,
            repository=repository,
            dead_letter_client=dead_letter_client,
            config=config,
        )

    def run(self) -> bool:
        """Receive and process a single queue message.

        Returns:
            True if a message was processed, False if no messages were available.
        """

        message = self._receive_message()
        if message is None:
            logger.info("No messages available on queue '%s'", self.config.queue_name)
            return False

        logger.info("Processing message %s", message.id)
        
        # Delete message immediately to prevent reprocessing
        # This ensures it only executes once, even if processing fails
        self._delete_message(message)
        
        try:
            payload = self._parse_message(message)
        except PoisonMessageError as exc:
            logger.error("Poison message detected: %s", exc)
            self._dead_letter(message, reason=str(exc))
            return True

        try:
            self._process_with_retries(message, payload)
            logger.info("Message %s processed successfully", message.id)
            return True
        except PoisonMessageError as exc:
            logger.error("Poison message after validation: %s", exc)
            self._dead_letter(message, reason=str(exc))
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to process message %s", message.id)
            self._dead_letter(message, reason=f"processing_error: {type(exc).__name__}")
            return True

    def _receive_message(self) -> Optional[QueueMessage]:
        return self._execute_with_backoff(
            lambda: self.queue_client.receive_message(visibility_timeout=self.config.visibility_timeout),
            operation_name="receive_message",
        )

    def _delete_message(self, message: QueueMessage) -> None:
        if not message:
            return
        self._execute_with_backoff(
            lambda: self.queue_client.delete_message(message.id, message.pop_receipt),
            operation_name="delete_message",
            suppress_errors=True,
        )

    def _dead_letter(self, message: QueueMessage, *, reason: str) -> None:
        if not self.dead_letter_client:
            logger.warning(
                "Dead-letter queue not configured. Message %s will be dropped. Reason: %s",
                getattr(message, "id", "<unknown>"),
                reason,
            )
            return

        payload = {
            "originalMessageId": getattr(message, "id", None),
            "reason": reason,
            "content": getattr(message, "content", None),
            "deadLetteredAt": datetime.now(timezone.utc).isoformat(),
        }

        def _send() -> None:
            self.dead_letter_client.send_message(json.dumps(payload))

        try:
            self._execute_with_backoff(_send, operation_name="send_dead_letter")
            logger.info(
                "Message %s moved to dead-letter queue '%s'",
                getattr(message, "id", "<unknown>"),
                self.config.dead_letter_queue_name,
            )
        except AzureError:
            logger.exception(
                "Failed to send message %s to dead-letter queue '%s'",
                getattr(message, "id", "<unknown>"),
                self.config.dead_letter_queue_name,
            )

    def _parse_message(self, message: QueueMessage) -> Dict[str, Any]:
        try:
            content = message.content
            if not isinstance(content, str):
                raise PoisonMessageError("Queue message content must be text")
            payload = json.loads(content)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive programming
            raise PoisonMessageError("Message content is not valid JSON") from exc

        if not isinstance(payload, dict):
            raise PoisonMessageError("Queue message payload must be a JSON object")

        tickers: Iterable[Any] | None = payload.get("tickers")
        if isinstance(tickers, (str, bytes)):
            tickers = [tickers]

        if not tickers:
            ticker = payload.get("ticker") or payload.get("symbol") or payload.get("asset")
            if ticker:
                tickers = [ticker]

        if not tickers:
            raise PoisonMessageError("Queue message must include 'tickers' or a single 'ticker'/'symbol'")

        normalised_tickers = [str(t).strip().upper() for t in tickers if str(t).strip()]
        if not normalised_tickers:
            raise PoisonMessageError("Queue message included an empty ticker list")

        analysis_window = payload.get("analysis_window") if isinstance(payload.get("analysis_window"), dict) else {}

        start_date = (
            analysis_window.get("start")
            or analysis_window.get("start_date")
            or payload.get("start")
            or payload.get("start_date")
        )
        end_date = (
            analysis_window.get("end")
            or analysis_window.get("end_date")
            or payload.get("end")
            or payload.get("end_date")
        )

        if not (start_date and end_date):
            lookback_days = payload.get("lookback_days") or payload.get("lookback") or os.getenv("QUEUE_DEFAULT_LOOKBACK_DAYS", "30")
            try:
                lookback_days_int = int(lookback_days)
            except (TypeError, ValueError):
                lookback_days_int = 30

            now = datetime.now(timezone.utc)
            start_date = (now - timedelta(days=lookback_days_int)).isoformat()
            end_date = now.isoformat()

        overrides = payload.get("overrides") or {}
        if overrides and not isinstance(overrides, dict):
            raise PoisonMessageError("'overrides' must be a JSON object when provided")

        return {
            "tickers": normalised_tickers,
            "start_date": start_date,
            "end_date": end_date,
            "overrides": overrides,
            "raw": payload,
        }

    def _process_with_retries(self, message: QueueMessage, payload: Dict[str, Any]) -> None:
        self._process_message(message, payload)

    def _process_message(self, message: QueueMessage, payload: Dict[str, Any]) -> None:
        # Check if we should use Alpaca for portfolio data (default: True)
        use_alpaca = os.getenv("USE_ALPACA_PORTFOLIO", "true").lower() == "true"
        
        if use_alpaca:
            # Fetch real-time portfolio from Alpaca
            logger.info("Fetching portfolio from Alpaca Paper Trading API")
            try:
                portfolio_data = get_alpaca_portfolio(
                    tickers=payload["tickers"],
                    paper=True  # Always use paper trading
                )
                portfolio_snapshot_id = "alpaca-live"
            except Exception as exc:
                logger.error("Failed to fetch portfolio from Alpaca: %s", exc)
                raise RuntimeError(f"Failed to fetch Alpaca portfolio: {exc}") from exc
        else:
            # Fallback to Cosmos DB (legacy mode)
            logger.info("Fetching portfolio from Cosmos DB")
            portfolio_snapshot = self.repository.get_latest_portfolio_snapshot()
            if not portfolio_snapshot:
                raise RuntimeError("No portfolio snapshot available in Cosmos DB")

            portfolio_data = portfolio_snapshot.get("portfolio") if isinstance(portfolio_snapshot, dict) else None
            if portfolio_data is None:
                raise RuntimeError("Portfolio snapshot payload is missing the 'portfolio' field")
            portfolio_snapshot_id = portfolio_snapshot.get("id")

        overrides = payload.get("overrides", {})
        raw_payload = payload.get("raw", {})

        run_kwargs = {
            "tickers": payload["tickers"],
            "start_date": payload["start_date"],
            "end_date": payload["end_date"],
            "portfolio": portfolio_data,
            "show_reasoning": bool(overrides.get("show_reasoning", False)),
            "selected_analysts": overrides.get("selected_analysts", []) or [],
            "model_name": overrides.get("model_name", "gpt-4.1"),
            "model_provider": overrides.get("model_provider", "OpenAI"),
            # Trade execution parameters
            "trade_mode": overrides.get("trade_mode", "paper" if use_alpaca else "analysis"),
            "dry_run": bool(overrides.get("dry_run", False)),
            "confidence_threshold": overrides.get("confidence_threshold"),
            # Tracking parameters
            "user_id": raw_payload.get("user_id") or "queue-worker",
            "strategy_id": raw_payload.get("strategy_id") or "default",
            "run_id": message.id,
        }

        hedge_result = run_hedge_fund(**run_kwargs)
        processed_at = datetime.now(timezone.utc).isoformat()

        result_record = {
            "id": message.id,
            "messageId": message.id,
            "tickers": payload["tickers"],
            "analysisWindow": {
                "start": payload["start_date"],
                "end": payload["end_date"],
            },
            "portfolioSnapshotId": portfolio_snapshot_id,
            "portfolioSource": "alpaca" if use_alpaca else "cosmos",
            "decisions": hedge_result.get("decisions"),
            "analystSignals": hedge_result.get("analyst_signals"),
            "processedAt": processed_at,
            "metadata": {
                "rawMessage": payload["raw"],
            },
        }

        # Check if trade_mode is enabled in overrides
        trade_mode = overrides.get("trade_mode", "analysis")
        if trade_mode == "paper":
            logger.info("Trade mode is 'paper' - executing orders via Alpaca")
            analyst_signals = hedge_result.get("analyst_signals", {})
            current_prices = hedge_result.get("current_prices", {})
            state_data = {"current_prices": current_prices}

            orders = dispatch_paper_orders(
                decisions=hedge_result.get("decisions", {}),
                analyst_signals=analyst_signals,
                state_data=state_data,
                confidence_threshold=overrides.get("confidence_threshold", 60),
                dry_run=overrides.get("dry_run", False),
            )
            
            result_record["broker_orders"] = orders
            result_record["trade_mode"] = "paper"
            logger.info("Executed %d broker orders", len(orders))
        else:
            logger.info("Trade mode is 'analysis' - no orders will be executed")
            result_record["trade_mode"] = "analysis"

        # Save results to Cosmos DB (optional - can be disabled)
        save_to_cosmos = os.getenv("SAVE_TO_COSMOS", "false").lower() == "true"
        if save_to_cosmos:
            self.repository.save_run_result(message.id, result_record)

            summary = self._summarise_decisions(hedge_result.get("decisions"))
            status_payload = {
                "id": message.id,
                "messageId": message.id,
                "status": "completed",
                "summary": summary,
                "tickers": payload["tickers"],
                "processedAt": processed_at,
            }
            self.repository.publish_status(message.id, status_payload)
            logger.info("Saved results to Cosmos DB")
        else:
            logger.info("Skipping Cosmos DB persistence (SAVE_TO_COSMOS=false)")

        # Log final summary
        logger.info(
            "Processing complete for message %s: tickers=%s, decisions=%d, trade_mode=%s",
            message.id,
            payload["tickers"],
            len(hedge_result.get("decisions", {})),
            trade_mode
        )

    def _compute_backoff(self, attempt: int) -> float:
        capped_attempt = max(0, attempt - 1)
        delay = self.config.base_backoff_seconds * (2**capped_attempt)
        delay = min(delay, self.config.max_backoff_seconds)
        jitter = random.uniform(0, self.config.base_backoff_seconds)
        return delay + jitter

    def _summarise_decisions(self, decisions: Optional[Dict[str, Any]]) -> str:
        if not decisions or not isinstance(decisions, dict):
            return "Decisions recorded for tickers." if decisions else "No decisions produced."

        summaries: list[str] = []
        for ticker, decision in decisions.items():
            if isinstance(decision, dict):
                action = decision.get("action") or decision.get("recommendation") or "decision"
                summaries.append(f"{ticker}:{action}")
            else:
                summaries.append(f"{ticker}:{decision}")
        return ", ".join(summaries) if summaries else "Decisions recorded for tickers."

    def _execute_with_backoff(
        self,
        func,
        *,
        operation_name: str,
        suppress_errors: bool = False,
    ):
        attempt = 0
        while True:
            attempt += 1
            try:
                return func()
            except self.RETRYABLE_EXCEPTIONS as exc:
                if attempt >= self.config.max_attempts:
                    if suppress_errors:
                        logger.warning(
                            "Operation %s failed after %s attempts: %s",
                            operation_name,
                            attempt,
                            exc,
                        )
                        return None
                    raise
                delay = self._compute_backoff(attempt)
                logger.debug(
                    "Retryable error during %s (attempt %s/%s): %s. Sleeping %.2fs",
                    operation_name,
                    attempt,
                    self.config.max_attempts,
                    exc,
                    delay,
                )
                time.sleep(delay)
            except Exception:
                if suppress_errors:
                    logger.exception("Non-retryable error during %s", operation_name)
                    return None
                raise

    def _update_portfolio_from_orders(self, portfolio_data: dict, orders: list, current_prices: dict) -> dict:
        """Update the portfolio based on executed orders."""
        updated_portfolio = dict(portfolio_data)  # Copy
        positions = dict(updated_portfolio.get("positions", {}))
        total_cash = float(updated_portfolio.get("total_cash", 0.0))

        for order in orders:
            if order.get("status") in ["error", "skipped", "skipped_confidence"]:
                continue  # Skip failed orders

            ticker = order.get("ticker")
            action = order.get("action", "").lower()
            quantity = int(order.get("quantity", 0))
            price = float(current_prices.get(ticker, 0.0))

            if not ticker or quantity <= 0 or price <= 0:
                continue

            cost = quantity * price

            if action in ["buy", "cover"]:
                if total_cash >= cost:
                    total_cash -= cost
                    positions[ticker] = positions.get(ticker, 0) + quantity
                else:
                    logger.warning(f"Insufficient cash for {action} {quantity} {ticker} at {price}")
            elif action in ["sell", "short"]:
                current_qty = positions.get(ticker, 0)
                if current_qty >= quantity:
                    total_cash += cost
                    positions[ticker] = current_qty - quantity
                    if positions[ticker] <= 0:
                        positions.pop(ticker, None)
                else:
                    logger.warning(f"Insufficient position for {action} {quantity} {ticker}")

        updated_portfolio["positions"] = positions
        updated_portfolio["total_cash"] = total_cash
        return updated_portfolio


def main() -> None:
    """Entry point for running the queue worker as a module."""

    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )

    worker = QueueWorker.from_environment()
    worker.run()


if __name__ == "__main__":
    main()
