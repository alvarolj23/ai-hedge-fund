# src/brokers/alpaca_paper_broker.py
from __future__ import annotations

import logging, os, time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import ValidationError

# --- alpaca-py ---
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from src.agents.portfolio_manager import PortfolioDecision

_LOGGER = logging.getLogger(__name__)

def _env(*names: str) -> Optional[str]:
    for name in names:
        v = os.getenv(name)
        if v:
            return v
    return None

def _isoformat(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str):
        return value
    return str(value)

def _serialize_response(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    # alpaca-py returns dataclasses / pydantic-like model objects with __dict__
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"value": str(obj)}

@dataclass
class BrokerOrder:
    ticker: str
    action: str
    quantity: int
    side: str
    order_id: Optional[str] = None
    status: str = "skipped"
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    error: Optional[str] = None
    dry_run: bool = False
    raw: Dict[str, Any] = field(default_factory=dict)

    def as_record(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker, "action": self.action, "side": self.side,
            "quantity": self.quantity, "order_id": self.order_id, "status": self.status,
            "submitted_at": self.submitted_at, "filled_at": self.filled_at,
            "error": self.error, "dry_run": self.dry_run, "raw": self.raw,
        }

class PaperBroker:
    """Wrapper around Alpaca's Trading API tuned for paper trading (alpaca-py)."""

    ACTION_TO_SIDE = {
        "buy": OrderSide.BUY,
        "sell": OrderSide.SELL,
        "short": OrderSide.SELL,   # market short requires margin + shortable; you may add checks
        "cover": OrderSide.BUY,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        *,
        confidence_threshold: int = 60,
        dry_run: bool = False,
        time_in_force: TimeInForce = TimeInForce.DAY,
    ) -> None:
        self._logger = _LOGGER
        self.dry_run = dry_run
        self.confidence_threshold = confidence_threshold
        self.time_in_force = time_in_force

        self.api_key = api_key or _env("APCA_API_KEY_ID", "ALPACA_API_KEY_ID")
        self.api_secret = api_secret or _env("APCA_API_SECRET_KEY", "ALPACA_API_SECRET_KEY")

        # If not forcing dry-run, create the TradingClient with paper=True (targets paper environment).
        self._client: Optional[TradingClient] = None
        if not self.dry_run:
            if not self.api_key or not self.api_secret:
                self._logger.warning("Missing Alpaca credentials. Falling back to dry-run mode.")
                self.dry_run = True
            else:
                try:
                    # paper=True -> uses paper environment regardless of APCA_API_BASE_URL value
                    self._client = TradingClient(self.api_key, self.api_secret, paper=True)
                except Exception as exc:
                    self._logger.error("Failed to initialize TradingClient: %s", exc)
                    self._client = None
                    self.dry_run = True

        # Optional: env override for confidence threshold
        confidence_override = os.getenv("ALPACA_CONFIDENCE_THRESHOLD")
        if confidence_override:
            try:
                self.confidence_threshold = int(confidence_override)
            except ValueError:
                self._logger.warning("Invalid ALPACA_CONFIDENCE_THRESHOLD=%s", confidence_override)

    # -------------------- Public API --------------------
    def submit_order(
        self,
        ticker: str,
        decision: PortfolioDecision | Dict[str, Any],
        *,
        time_in_force: Optional[str] = None,
    ) -> BrokerOrder:
        parsed = self._coerce_decision(decision)
        if parsed is None:
            return BrokerOrder(
                ticker=ticker, action=str(getattr(decision, "action", "unknown")),
                quantity=0, side="unknown", status="invalid_decision",
                error="Unable to parse decision",
            )

        action = parsed.action.lower()
        side_enum = self.ACTION_TO_SIDE.get(action)
        quantity = int(parsed.quantity)

        if side_enum is None:
            return BrokerOrder(ticker, parsed.action, quantity, "unknown",
                               status="skipped", error=f"Unsupported action: {parsed.action}")

        if quantity <= 0:
            return BrokerOrder(ticker, parsed.action, quantity, side_enum.value,
                               status="skipped", error="Non-positive quantity")

        if parsed.confidence is not None and parsed.confidence < self.confidence_threshold:
            return BrokerOrder(ticker, parsed.action, quantity, side_enum.value,
                               status="skipped_confidence", error="Decision confidence below threshold")

        tif = TimeInForce(time_in_force.upper()) if time_in_force else self.time_in_force

        if self.dry_run or self._client is None:
            now = datetime.now(timezone.utc).isoformat()
            return BrokerOrder(
                ticker=ticker, action=parsed.action, quantity=quantity, side=side_enum.value,
                order_id=f"dry-{ticker}-{int(time.time()*1000)}", status="accepted_dry_run",
                submitted_at=now, dry_run=True,
            )

        try:
            req = MarketOrderRequest(symbol=ticker, qty=quantity, side=side_enum, time_in_force=tif)
            resp = self._client.submit_order(order_data=req)
            return self._to_broker_order(ticker=ticker, action=parsed.action,
                                         quantity=quantity, side=side_enum.value, response=resp)
        except Exception as exc:
            self._logger.exception("Error submitting Alpaca order")
            return BrokerOrder(ticker, parsed.action, quantity, side_enum.value, status="error", error=str(exc))

    # -------------------- Internals --------------------
    def _coerce_decision(self, decision: PortfolioDecision | Dict[str, Any]) -> Optional[PortfolioDecision]:
        if isinstance(decision, PortfolioDecision):
            return decision
        try:
            return PortfolioDecision.model_validate(decision)
        except ValidationError as exc:
            self._logger.error("Invalid PortfolioDecision payload: %s", exc)
            return None

    def _to_broker_order(self, *, ticker: str, action: str, quantity: int, side: str, response: Any) -> BrokerOrder:
        order_id = getattr(response, "id", None)
        status = getattr(response, "status", "submitted")
        submitted_at = _isoformat(getattr(response, "submitted_at", None))
        filled_at = _isoformat(getattr(response, "filled_at", None))
        raw = _serialize_response(response)
        return BrokerOrder(
            ticker=ticker, action=action, quantity=quantity, side=side,
            order_id=order_id, status=status, submitted_at=submitted_at, filled_at=filled_at, raw=raw
        )
