"""
Azure Functions App - Market Monitoring (Enhanced with Multi-API Support)
Uses Python v2 programming model with decorators

Features:
- 1-minute fast monitoring for immediate signal detection
- 5-minute comprehensive analysis with enhanced indicators
- 15-minute validation and confirmation
- Multi-API support (Finnhub, Polygon, Alpha Vantage, yfinance)
- Market holiday handling
- VWAP, ATR, gap detection, volume velocity, and more
"""
import datetime as dt
import json
import logging
import os
from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Sequence, Optional
from zoneinfo import ZoneInfo

import azure.functions as func
from azure.cosmos import CosmosClient, PartitionKey, exceptions as cosmos_exceptions
from azure.storage.queue import QueueClient

# Import local modules (no external src dependencies)
from models import Price
from api_client import get_prices
from multi_api_client import MultiAPIClient, Quote, IntradayBar
from signal_detection import enhanced_signal_detection, SignalResult
from market_calendar import is_market_open, is_market_holiday, previous_trading_day


EASTERN = ZoneInfo("America/New_York")

# Initialize the Azure Functions app
app = func.FunctionApp()


@dataclass
class SignalSummary:
    ticker: str
    percent_change: float
    volume_ratio: float | None
    latest: Price
    previous: Price
    average_volume: float | None
    reasons: list[str]

    @property
    def triggered(self) -> bool:
        return bool(self.reasons)


class CosmosCooldownStore:
    """Persist ticker trigger timestamps in Cosmos DB."""

    def __init__(self, endpoint: str, key: str, database: str, container: str) -> None:
        self._client = CosmosClient(url=endpoint, credential=key)
        self._database = self._client.create_database_if_not_exists(id=database)
        self._container = self._database.create_container_if_not_exists(
            id=container,
            partition_key=PartitionKey(path="/ticker")
        )

    def get_last_trigger(self, ticker: str) -> dt.datetime | None:
        try:
            item = self._container.read_item(item=ticker, partition_key=ticker)
        except cosmos_exceptions.CosmosResourceNotFoundError:
            return None
        except cosmos_exceptions.CosmosHttpResponseError as exc:
            logging.error("Cosmos read failed for %s: %s", ticker, exc)
            return None

        timestamp = item.get("last_triggered_utc")
        if not timestamp:
            return None
        try:
            parsed = dt.datetime.fromisoformat(timestamp)
        except ValueError:
            logging.warning("Invalid timestamp stored for %s: %s", ticker, timestamp)
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)

    def upsert_trigger(self, ticker: str, triggered_at: dt.datetime, reasons: list[str]) -> None:
        payload = {
            "id": ticker,
            "ticker": ticker,
            "last_triggered_utc": triggered_at.isoformat(),
            "last_reasons": reasons,
        }
        try:
            self._container.upsert_item(payload)
        except cosmos_exceptions.CosmosHttpResponseError as exc:
            logging.error("Failed to persist trigger for %s: %s", ticker, exc)


def _parse_watchlist(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [token.strip().upper() for token in raw.split(",") if token.strip()]


def _parse_price_time(value: str) -> dt.datetime:
    sanitized = value.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(sanitized)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                parsed = dt.datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        else:
            logging.warning("Unable to parse price timestamp: %s", value)
            parsed = dt.datetime.utcnow()
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _isoformat(timestamp: dt.datetime) -> str:
    return timestamp.replace(microsecond=0).isoformat()


def _load_queue_client() -> QueueClient:
    connection = (
        os.getenv("MARKET_MONITOR_QUEUE_CONNECTION_STRING")
        or os.getenv("AZURE_STORAGE_QUEUE_CONNECTION_STRING")
        or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        or os.getenv("AzureWebJobsStorage")
    )
    queue_name = (
        os.getenv("MARKET_MONITOR_QUEUE_NAME")
        or os.getenv("ALERT_QUEUE_NAME")
        or os.getenv("AZURE_STORAGE_QUEUE_NAME")
    )
    if not connection or not queue_name:
        raise RuntimeError("Queue storage configuration is missing")
    client = QueueClient.from_connection_string(connection, queue_name)
    try:
        client.create_queue()
    except Exception:  # Queue may already exist
        pass
    return client


def _ensure_cosmos_store() -> CosmosCooldownStore:
    endpoint = os.getenv("COSMOS_ENDPOINT")
    key = os.getenv("COSMOS_KEY")
    database = os.getenv("COSMOS_DATABASE")
    container = os.getenv("COSMOS_CONTAINER")
    if not all([endpoint, key, database, container]):
        raise RuntimeError("Cosmos DB configuration is missing required settings")
    return CosmosCooldownStore(endpoint, key, database, container)


def _is_market_hours(now_utc: dt.datetime) -> bool:
    """Check if market is currently open (with holiday support)"""
    return is_market_open(now_utc)


def _history_window_days(volume_window: int) -> int:
    # Changed default from 30 to 180 days to match queue worker requirements
    # Queue worker needs 180 days (126 trading days) for technical indicators
    default_days = int(os.getenv("MARKET_MONITOR_LOOKBACK_DAYS", "180"))
    return max(default_days, volume_window + 2)


def _fetch_price_history(ticker: str, start_date: str, end_date: str, interval: str = "day", interval_multiplier: int = 1) -> list[Price]:
    """Fetch price history with configurable intervals"""
    prices = get_prices(ticker=ticker, start_date=start_date, end_date=end_date, interval=interval, interval_multiplier=interval_multiplier)
    prices = sorted(prices, key=lambda price: _parse_price_time(price.time))
    return prices


def _evaluate_signals(
    ticker: str,
    prices: Sequence[Price],
    percent_threshold: float,
    volume_multiplier: float,
    volume_window: int,
) -> SignalSummary | None:
    if len(prices) < 2:
        logging.info("Not enough price history for %s to compute signals", ticker)
        return None

    sorted_prices = list(prices)
    latest = sorted_prices[-1]
    previous = sorted_prices[-2]
    if previous.close == 0:
        logging.warning("Previous close is zero for %s; skipping", ticker)
        return None

    percent_change = (latest.close - previous.close) / previous.close

    historical_window = sorted_prices[max(0, len(sorted_prices) - volume_window - 1) : -1]
    average_volume = None
    volume_ratio = None
    if historical_window:
        average_volume = mean(price.volume for price in historical_window)
        if average_volume > 0:
            volume_ratio = latest.volume / average_volume

    reasons: list[str] = []
    if percent_change >= percent_threshold:
        reasons.append("price_breakout")
    if volume_ratio is not None and volume_ratio >= volume_multiplier:
        reasons.append("volume_spike")

    summary = SignalSummary(
        ticker=ticker,
        percent_change=percent_change,
        volume_ratio=volume_ratio,
        latest=latest,
        previous=previous,
        average_volume=average_volume,
        reasons=reasons,
    )
    return summary


def _compose_queue_payload(
    ticker: str,
    triggered_at: dt.datetime,
    analysis_window_minutes: int,
    summary: SignalSummary,
    watchlist: Iterable[str],
) -> dict:
    # Calculate proper date range for analysis (not timestamps)
    # Technical analysis requires at least 126 trading days (6 months) for momentum indicators
    # 180 calendar days ≈ 130 trading days, providing sufficient buffer
    lookback_days = int(os.getenv("MARKET_MONITOR_ANALYSIS_LOOKBACK_DAYS", "180"))

    # End date is today, start date is lookback_days ago
    eastern_now = triggered_at.astimezone(EASTERN)
    end_date = eastern_now.date().isoformat()
    start_date = (eastern_now.date() - dt.timedelta(days=lookback_days)).isoformat()

    # Build the payload compatible with queue_worker.py expectations
    payload = {
        # Required fields
        "tickers": [ticker],

        # Date range for analysis (YYYY-MM-DD format)
        "analysis_window": {
            "start": start_date,
            "end": end_date,
        },

        # User and strategy identification
        "user_id": os.getenv("MARKET_MONITOR_USER_ID", "market-monitor"),
        "strategy_id": os.getenv("MARKET_MONITOR_STRATEGY_ID", "auto-signal"),

        # Market monitoring metadata (preserved for future use)
        "market_snapshot": {
            "percent_change": round(summary.percent_change, 6),
            "volume_ratio": round(summary.volume_ratio, 6) if summary.volume_ratio is not None else None,
            "latest_close": summary.latest.close,
            "previous_close": summary.previous.close,
            "latest_volume": summary.latest.volume,
            "average_volume": summary.average_volume,
        },
        "signals": summary.reasons,
        "triggered_at": _isoformat(triggered_at),
        "correlation_hints": {
            "related_watchlist": [symbol for symbol in watchlist if symbol != ticker],
            "basis": summary.reasons,
        },
    }
    return payload


def _format_schedule_status(timer: func.TimerRequest | None) -> str:
    if not timer:
        return "unknown"

    status = getattr(timer, "schedule_status", None)
    if not status:
        return "unknown"

    if isinstance(status, dict):
        for key in ("last", "Last", "lastUpdated", "LastUpdated"):
            if key in status and status[key]:
                return str(status[key])
        return "unknown"

    for attr in ("last", "Last", "last_updated", "LastUpdated"):
        value = getattr(status, attr, None)
        if value:
            return str(value)

    return "unknown"


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="market_timer", run_on_startup=False, use_monitor=False)
def market_monitor(market_timer: func.TimerRequest) -> None:
    """
    Market monitoring timer function.
    Runs every 5 minutes during market hours to detect price breakouts and volume spikes.
    """
    logging.info("Market monitor timer triggered at %s", _format_schedule_status(market_timer))

    now_utc = dt.datetime.now(dt.timezone.utc)
    eastern_now = now_utc.astimezone(EASTERN)
    logging.info("Current time - UTC: %s, ET: %s, Day of week: %d", now_utc, eastern_now, eastern_now.weekday())
    
    if not _is_market_hours(now_utc):
        logging.info("Outside market hours - skipping execution")
        return
    
    logging.info("Within market hours - proceeding with monitoring")

    watchlist_env = (
        os.getenv("MARKET_MONITOR_WATCHLIST")
        or os.getenv("WATCHLIST_TICKERS")
        or os.getenv("DEFAULT_WATCHLIST")
    )
    watchlist = _parse_watchlist(watchlist_env)
    if not watchlist:
        watchlist = ["AAPL", "MSFT", "NVDA"]
        logging.warning("No watchlist configured; falling back to default %s", watchlist)

    percent_threshold = float(os.getenv("MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD", "0.02"))
    volume_multiplier = float(os.getenv("MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER", "1.5"))
    volume_window = int(os.getenv("MARKET_MONITOR_VOLUME_LOOKBACK", "10"))
    analysis_window_minutes = int(os.getenv("MARKET_MONITOR_ANALYSIS_WINDOW_MINUTES", "120"))
    cooldown_seconds = int(os.getenv("MARKET_MONITOR_COOLDOWN_SECONDS", str(30 * 60)))

    try:
        queue_client = _load_queue_client()
    except RuntimeError as exc:
        logging.error("Queue client initialization failed: %s", exc)
        return

    try:
        cooldown_store = _ensure_cosmos_store()
    except RuntimeError as exc:
        logging.error("Cosmos configuration error: %s", exc)
        return

    cooldown_window = dt.timedelta(seconds=cooldown_seconds)
    history_days = _history_window_days(volume_window)
    today_eastern = now_utc.astimezone(EASTERN).date()
    start_date = (today_eastern - dt.timedelta(days=history_days)).isoformat()
    end_date = today_eastern.isoformat()

    logging.info("Monitoring %d tickers: %s (date range: %s to %s)", 
                 len(watchlist), watchlist, start_date, end_date)
    logging.info("Thresholds - Price change: %.2f%%, Volume multiplier: %.1fx, Cooldown: %ds",
                 percent_threshold * 100, volume_multiplier, cooldown_seconds)

    # Get interval settings for intraday monitoring
    interval = os.getenv("MARKET_MONITOR_INTERVAL", "minute")
    interval_multiplier = int(os.getenv("MARKET_MONITOR_INTERVAL_MULTIPLIER", "5"))

    for ticker in watchlist:
        logging.info("Processing ticker: %s", ticker)
        try:
            # Fetch intraday prices (5-minute bars by default)
            prices = _fetch_price_history(ticker, start_date, end_date, interval=interval, interval_multiplier=interval_multiplier)
            logging.info("Fetched %d price records for %s (%s/%d interval)", len(prices), ticker, interval, interval_multiplier)

            # Get previous day close for gap detection
            prev_day = previous_trading_day(today_eastern)
            prev_day_prices = _fetch_price_history(ticker, prev_day.isoformat(), prev_day.isoformat(), interval="day", interval_multiplier=1)
            previous_close = prev_day_prices[-1].close if prev_day_prices else None

        except Exception as exc:  # noqa: BLE001 - log and continue on data failure
            logging.exception("Failed to fetch prices for %s: %s", ticker, exc)
            continue

        summary = _evaluate_signals(ticker, prices, percent_threshold, volume_multiplier, volume_window)
        if not summary:
            logging.info("No summary generated for %s (insufficient data)", ticker)
            continue
            
        if not summary.triggered:
            logging.info("%s: No signals triggered (change: %.2f%%, vol ratio: %s)", 
                        ticker, summary.percent_change * 100, 
                        f"{summary.volume_ratio:.2f}x" if summary.volume_ratio else "N/A")
            continue

        logging.info("%s: SIGNALS DETECTED - %s (change: %.2f%%, vol ratio: %.2fx)", 
                    ticker, summary.reasons, summary.percent_change * 100, summary.volume_ratio or 0)

        last_trigger = cooldown_store.get_last_trigger(ticker)
        if last_trigger and now_utc - last_trigger < cooldown_window:
            logging.info("Ticker %s skipped due to cooldown (last trigger at %s)", ticker, last_trigger)
            continue

        payload = _compose_queue_payload(ticker, now_utc, analysis_window_minutes, summary, watchlist)
        try:
            queue_client.send_message(json.dumps(payload))
            logging.info("✓ Enqueued analysis request for %s with reasons %s", ticker, summary.reasons)
            cooldown_store.upsert_trigger(ticker, now_utc, summary.reasons)
        except Exception as exc:  # noqa: BLE001 - surface queue issues
            logging.exception("Failed to enqueue analysis for %s: %s", ticker, exc)
    
    logging.info("Market monitor execution completed")


@app.timer_trigger(schedule="0 * * * * *", arg_name="fast_timer", run_on_startup=False, use_monitor=False)
def fast_monitor(fast_timer: func.TimerRequest) -> None:
    """
    Fast 1-minute monitoring using real-time APIs (Finnhub, yfinance)
    Runs every 1 minute to catch rapid price movements
    Triggers the main 5-minute function for full analysis if signals detected
    """
    logging.info("Fast monitor (1-min) triggered at %s", _format_schedule_status(fast_timer))

    now_utc = dt.datetime.now(dt.timezone.utc)

    if not _is_market_hours(now_utc):
        logging.info("Outside market hours - skipping fast monitor")
        return

    logging.info("Fast monitor active - checking for immediate signals")

    watchlist_env = (
        os.getenv("MARKET_MONITOR_WATCHLIST")
        or os.getenv("WATCHLIST_TICKERS")
        or os.getenv("DEFAULT_WATCHLIST")
    )
    watchlist = _parse_watchlist(watchlist_env)
    if not watchlist:
        watchlist = ["AAPL", "MSFT", "NVDA"]

    # Use multi-API client for real-time quotes
    multi_client = MultiAPIClient()

    # Fast detection thresholds (more aggressive)
    fast_percent_threshold = float(os.getenv("FAST_MONITOR_PERCENT_THRESHOLD", "0.005"))  # 0.5%
    fast_velocity_threshold = float(os.getenv("FAST_MONITOR_VELOCITY_THRESHOLD", "0.002"))  # 0.2% per minute

    try:
        cooldown_store = _ensure_cosmos_store()
    except RuntimeError as exc:
        logging.error("Cosmos configuration error: %s", exc)
        return

    cooldown_seconds = int(os.getenv("FAST_MONITOR_COOLDOWN_SECONDS", str(5 * 60)))  # 5 minutes
    cooldown_window = dt.timedelta(seconds=cooldown_seconds)

    for ticker in watchlist:
        logging.info("Fast checking: %s", ticker)

        try:
            # Get real-time quote
            quote = multi_client.get_best_quote(ticker)
            if not quote or quote.price <= 0:
                logging.warning("No valid quote for %s", ticker)
                continue

            # Get recent intraday bars for context (1-minute bars from yfinance)
            intraday_bars = multi_client.get_intraday_bars(ticker, interval_minutes=1, limit=60)

            if not intraday_bars or len(intraday_bars) < 5:
                logging.warning("Insufficient intraday data for %s", ticker)
                continue

            # Convert to Price objects for signal detection
            prices = [
                Price(
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume,
                    time=bar.timestamp.isoformat()
                )
                for bar in intraday_bars
            ]

            # Quick checks for immediate signals
            latest_price = quote.price
            previous_price = prices[-1].close if prices else latest_price

            if previous_price > 0:
                instant_change = abs(latest_price - previous_price) / previous_price

                if instant_change >= fast_percent_threshold:
                    logging.info("%s: Fast signal - Instant change %.2f%%", ticker, instant_change * 100)

                    # Check cooldown
                    last_trigger = cooldown_store.get_last_trigger(ticker)
                    if last_trigger and now_utc - last_trigger < cooldown_window:
                        logging.info("Ticker %s in cooldown (last: %s)", ticker, last_trigger)
                        continue

                    # This is a fast signal - log it for the 5-minute function to pick up
                    logging.info("🚨 FAST ALERT: %s moved %.2f%% in last minute", ticker, instant_change * 100)

                    # Update a "fast signal" marker in Cosmos that the 5-min function can check
                    # The 5-minute function will do the full analysis
                    cooldown_store.upsert_trigger(ticker, now_utc, ["fast_movement"])

        except Exception as exc:
            logging.error("Fast monitor error for %s: %s", ticker, exc)
            continue

    logging.info("Fast monitor execution completed")


@app.timer_trigger(schedule="0 */15 * * * *", arg_name="validation_timer", run_on_startup=False, use_monitor=False)
def validation_monitor(validation_timer: func.TimerRequest) -> None:
    """
    15-minute validation and confirmation monitor
    Uses Alpha Vantage for technical indicators validation
    Checks for false positives and provides additional context
    """
    logging.info("Validation monitor (15-min) triggered at %s", _format_schedule_status(validation_timer))

    now_utc = dt.datetime.now(dt.timezone.utc)

    if not _is_market_hours(now_utc):
        logging.info("Outside market hours - skipping validation monitor")
        return

    logging.info("Validation monitor active - checking recent signals")

    watchlist_env = (
        os.getenv("MARKET_MONITOR_WATCHLIST")
        or os.getenv("WATCHLIST_TICKERS")
        or os.getenv("DEFAULT_WATCHLIST")
    )
    watchlist = _parse_watchlist(watchlist_env)
    if not watchlist:
        watchlist = ["AAPL", "MSFT", "NVDA"]

    try:
        cooldown_store = _ensure_cosmos_store()
    except RuntimeError as exc:
        logging.error("Cosmos configuration error: %s", exc)
        return

    # Check which tickers have triggered in the last 15 minutes
    lookback_window = dt.timedelta(minutes=15)
    multi_client = MultiAPIClient()

    for ticker in watchlist:
        try:
            last_trigger = cooldown_store.get_last_trigger(ticker)
            if not last_trigger:
                continue

            if now_utc - last_trigger > lookback_window:
                continue

            logging.info("Validating recent signal for %s (triggered %s ago)",
                        ticker, now_utc - last_trigger)

            # Get RSI from Alpha Vantage for validation
            rsi = multi_client.alpha_vantage.get_rsi(ticker, interval="5min", time_period=14)

            if rsi:
                logging.info("%s validation - RSI(14): %.2f", ticker, rsi)

                # Log overbought/oversold conditions
                if rsi >= 70:
                    logging.info("⚠️  %s: RSI indicates overbought (%.2f)", ticker, rsi)
                elif rsi <= 30:
                    logging.info("⚠️  %s: RSI indicates oversold (%.2f)", ticker, rsi)
                else:
                    logging.info("✓ %s: RSI neutral (%.2f)", ticker, rsi)

            # Get recent intraday bars for trend confirmation
            bars = multi_client.get_intraday_bars(ticker, interval_minutes=5, limit=12)  # Last hour

            if len(bars) >= 6:
                recent_trend = sum(1 if bars[i].close > bars[i-1].close else -1 for i in range(1, 6))

                if recent_trend >= 4:
                    logging.info("✓ %s: Strong uptrend confirmed (last 30 min)", ticker)
                elif recent_trend <= -4:
                    logging.info("✓ %s: Strong downtrend confirmed (last 30 min)", ticker)
                else:
                    logging.info("⚠️  %s: Mixed signals, trend unclear", ticker)

        except Exception as exc:
            logging.error("Validation error for %s: %s", ticker, exc)
            continue

    logging.info("Validation monitor execution completed")
