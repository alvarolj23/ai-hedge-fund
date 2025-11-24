"""
Enhanced signal detection with advanced indicators
Implements: gap detection, volume velocity, VWAP deviation, multi-timeframe analysis
"""
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from models import Price


@dataclass
class SignalResult:
    """Enhanced signal detection result"""
    triggered: bool
    reasons: list[str]
    confidence: float  # 0.0 to 1.0
    metrics: dict
    priority: str  # "low", "medium", "high", "critical"


def calculate_vwap(prices: list[Price]) -> float:
    """Calculate Volume Weighted Average Price"""
    if not prices:
        return 0.0

    total_volume = sum(p.volume for p in prices)
    if total_volume == 0:
        return 0.0

    vwap = sum(p.close * p.volume for p in prices) / total_volume
    return vwap


def calculate_price_velocity(prices: list[Price], lookback_minutes: int = 5) -> float:
    """Calculate price change per minute over lookback period"""
    if len(prices) < 2:
        return 0.0

    latest = prices[-1]
    lookback_idx = max(0, len(prices) - lookback_minutes - 1)
    previous = prices[lookback_idx]

    if previous.close == 0:
        return 0.0

    time_diff = lookback_minutes if lookback_minutes > 0 else 1
    price_change = abs(latest.close - previous.close) / previous.close
    velocity = price_change / time_diff

    return velocity


def calculate_volume_velocity(prices: list[Price]) -> float:
    """Calculate current volume rate vs average"""
    if len(prices) < 10:
        return 1.0

    latest_volume = prices[-1].volume
    avg_volume = sum(p.volume for p in prices[-10:-1]) / 9

    if avg_volume == 0:
        return 1.0

    return latest_volume / avg_volume


def calculate_atr(prices: list[Price], period: int = 14) -> float:
    """Calculate Average True Range"""
    if len(prices) < period + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(prices)):
        high_low = prices[i].high - prices[i].low
        high_close = abs(prices[i].high - prices[i - 1].close)
        low_close = abs(prices[i].low - prices[i - 1].close)
        true_ranges.append(max(high_low, high_close, low_close))

    if not true_ranges:
        return 0.0

    atr = sum(true_ranges[-period:]) / min(period, len(true_ranges))
    return atr


def calculate_rsi(prices: list[Price], period: int = 14) -> float:
    """
    Calculate RSI (Relative Strength Index) locally without API calls

    Args:
        prices: Price history
        period: RSI period (default 14)

    Returns:
        RSI value (0-100), or 50.0 if insufficient data
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral

    gains = []
    losses = []

    for i in range(1, len(prices)):
        change = prices[i].close - prices[i-1].close
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    # Calculate average gain and loss over the period
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0  # All gains, maximum RSI

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)


def detect_gap(latest: Price, previous_close: float, threshold: float = 0.015) -> Optional[str]:
    """
    Detect gap at market open

    Args:
        latest: Latest price bar
        previous_close: Previous day's close
        threshold: Gap threshold (default 1.5%)

    Returns:
        "gap_up" or "gap_down" if gap detected, None otherwise
    """
    if previous_close == 0:
        return None

    gap = (latest.open - previous_close) / previous_close

    if gap >= threshold:
        return "gap_up"
    elif gap <= -threshold:
        return "gap_down"

    return None


def detect_intraday_breakout(prices: list[Price], lookback_bars: int = 78) -> Optional[str]:
    """
    Detect if price breaks intraday high/low

    Args:
        prices: Price history
        lookback_bars: Number of bars to look back (78 = ~6.5 hours with 5-min bars)

    Returns:
        "breakout_high" or "breakout_low" if breakout detected, None otherwise
    """
    if len(prices) < lookback_bars + 1:
        return None

    historical = prices[-lookback_bars - 1:-1]
    latest = prices[-1]

    intraday_high = max(p.high for p in historical)
    intraday_low = min(p.low for p in historical)

    if latest.high > intraday_high:
        return "breakout_high"
    elif latest.low < intraday_low:
        return "breakout_low"

    return None


def detect_vwap_deviation(prices: list[Price], std_threshold: float = 2.0) -> Optional[str]:
    """
    Detect significant deviation from VWAP

    Args:
        prices: Price history
        std_threshold: Number of standard deviations (default 2.0)

    Returns:
        "above_vwap" or "below_vwap" if significant deviation, None otherwise
    """
    if len(prices) < 20:
        return None

    vwap = calculate_vwap(prices)
    if vwap == 0:
        return None

    # Calculate standard deviation of price from VWAP
    deviations = [(p.close - vwap) for p in prices]
    mean_deviation = sum(deviations) / len(deviations)
    variance = sum((d - mean_deviation) ** 2 for d in deviations) / len(deviations)
    std_dev = math.sqrt(variance)

    latest_price = prices[-1].close
    deviation_zscore = (latest_price - vwap) / std_dev if std_dev > 0 else 0

    if deviation_zscore > std_threshold:
        return "above_vwap"
    elif deviation_zscore < -std_threshold:
        return "below_vwap"

    return None


def calculate_bollinger_position(prices: list[Price], period: int = 20) -> float:
    """
    Calculate where price is relative to Bollinger Bands (0.0 = lower band, 1.0 = upper band)
    """
    if len(prices) < period:
        return 0.5

    recent = prices[-period:]
    closes = [p.close for p in recent]
    mean_price = sum(closes) / len(closes)
    variance = sum((c - mean_price) ** 2 for c in closes) / len(closes)
    std_dev = math.sqrt(variance)

    upper_band = mean_price + (2 * std_dev)
    lower_band = mean_price - (2 * std_dev)

    latest_price = prices[-1].close

    if upper_band == lower_band:
        return 0.5

    position = (latest_price - lower_band) / (upper_band - lower_band)
    return max(0.0, min(1.0, position))


def detect_volatility_expansion(prices: list[Price], lookback: int = 20, threshold: float = 1.5) -> bool:
    """
    Detect if volatility is expanding significantly

    Args:
        prices: Price history
        lookback: Period for ATR calculation
        threshold: Multiplier for volatility expansion (default 1.5x)

    Returns:
        True if volatility expanding, False otherwise
    """
    if len(prices) < lookback * 2:
        return False

    # Calculate recent ATR
    recent_atr = calculate_atr(prices[-lookback:], period=lookback)

    # Calculate historical ATR
    historical_atr = calculate_atr(prices[-lookback * 2:-lookback], period=lookback)

    if historical_atr == 0:
        return False

    atr_ratio = recent_atr / historical_atr
    return atr_ratio >= threshold


def check_multi_timeframe_alignment(prices_1m: list[Price], prices_5m: list[Price],
                                   prices_15m: list[Price]) -> dict:
    """
    Check if trends are aligned across multiple timeframes

    Returns:
        Dict with alignment status and direction
    """
    result = {
        "aligned": False,
        "direction": "neutral",
        "confidence": 0.0
    }

    if len(prices_1m) < 20 or len(prices_5m) < 20 or len(prices_15m) < 20:
        return result

    # Calculate simple trend for each timeframe (recent vs earlier average)
    def get_trend_direction(prices: list[Price]) -> int:
        """Returns 1 for uptrend, -1 for downtrend, 0 for neutral"""
        recent_avg = sum(p.close for p in prices[-5:]) / 5
        earlier_avg = sum(p.close for p in prices[-15:-5]) / 10

        if recent_avg > earlier_avg * 1.005:  # 0.5% threshold
            return 1
        elif recent_avg < earlier_avg * 0.995:
            return -1
        return 0

    trend_1m = get_trend_direction(prices_1m)
    trend_5m = get_trend_direction(prices_5m)
    trend_15m = get_trend_direction(prices_15m)

    # Check alignment
    if trend_1m == trend_5m == trend_15m and trend_1m != 0:
        result["aligned"] = True
        result["direction"] = "bullish" if trend_1m > 0 else "bearish"
        result["confidence"] = 0.9
    elif (trend_1m == trend_5m and trend_1m != 0) or (trend_5m == trend_15m and trend_5m != 0):
        result["aligned"] = True
        result["direction"] = "bullish" if max(trend_1m, trend_5m, trend_15m) > 0 else "bearish"
        result["confidence"] = 0.6

    return result


def enhanced_signal_detection(
    ticker: str,
    prices: list[Price],
    previous_day_close: float = None,
    percent_threshold: float = 0.02,
    volume_multiplier: float = 1.5,
    vwap_std_threshold: float = 2.0,
    velocity_threshold: float = 0.001,  # 0.1% per minute
) -> SignalResult:
    """
    Enhanced signal detection with multiple indicators

    Args:
        ticker: Stock ticker
        prices: Price history (should be intraday bars)
        previous_day_close: Previous day's closing price for gap detection
        percent_threshold: Price change threshold (default 2%)
        volume_multiplier: Volume spike threshold (default 1.5x)
        vwap_std_threshold: VWAP deviation in std devs (default 2.0)
        velocity_threshold: Price velocity threshold (default 0.1% per minute)

    Returns:
        SignalResult with detection results
    """
    if len(prices) < 2:
        return SignalResult(
            triggered=False,
            reasons=[],
            confidence=0.0,
            metrics={},
            priority="low"
        )

    latest = prices[-1]
    previous = prices[-2]

    reasons = []
    confidence_scores = []
    metrics = {}

    # 1. Basic price change detection
    if previous.close > 0:
        percent_change = (latest.close - previous.close) / previous.close
        metrics["percent_change"] = round(percent_change * 100, 2)

        if abs(percent_change) >= percent_threshold:
            reasons.append("price_breakout")
            confidence_scores.append(min(abs(percent_change) / percent_threshold, 1.0))

    # 2. Volume analysis
    if len(prices) >= 10:
        volume_ratio = calculate_volume_velocity(prices)
        metrics["volume_ratio"] = round(volume_ratio, 2)

        if volume_ratio >= volume_multiplier:
            reasons.append("volume_spike")
            confidence_scores.append(min(volume_ratio / volume_multiplier, 1.0) * 0.8)

    # 3. Price velocity (rapid movement)
    velocity = calculate_price_velocity(prices, lookback_minutes=5)
    metrics["price_velocity"] = round(velocity * 100, 4)

    if velocity >= velocity_threshold:
        reasons.append("rapid_movement")
        confidence_scores.append(min(velocity / velocity_threshold, 1.0) * 0.9)

    # 4. Gap detection (if previous close provided)
    if previous_day_close and previous_day_close > 0:
        gap_signal = detect_gap(latest, previous_day_close, threshold=0.015)
        if gap_signal:
            reasons.append(gap_signal)
            gap_pct = abs(latest.open - previous_day_close) / previous_day_close
            metrics["gap_percent"] = round(gap_pct * 100, 2)
            confidence_scores.append(min(gap_pct / 0.02, 1.0) * 0.95)

    # 5. Intraday breakout
    breakout_signal = detect_intraday_breakout(prices, lookback_bars=78)
    if breakout_signal:
        reasons.append(breakout_signal)
        confidence_scores.append(0.85)

    # 6. VWAP deviation
    vwap = calculate_vwap(prices)
    vwap_signal = detect_vwap_deviation(prices, std_threshold=vwap_std_threshold)
    if vwap_signal:
        reasons.append(vwap_signal)
        metrics["vwap"] = round(vwap, 2)
        metrics["vwap_deviation"] = round((latest.close - vwap) / vwap * 100, 2)
        confidence_scores.append(0.75)

    # 7. Bollinger Band position
    bb_position = calculate_bollinger_position(prices)
    metrics["bollinger_position"] = round(bb_position, 2)

    if bb_position <= 0.1 or bb_position >= 0.9:
        reasons.append("bollinger_extreme")
        confidence_scores.append(0.7)

    # 8. Volatility expansion
    if detect_volatility_expansion(prices):
        reasons.append("volatility_expansion")
        confidence_scores.append(0.8)

    # 9. ATR calculation
    atr = calculate_atr(prices)
    if latest.close > 0:
        atr_percent = (atr / latest.close) * 100
        metrics["atr_percent"] = round(atr_percent, 2)

    # Calculate overall confidence
    overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    overall_confidence = min(overall_confidence, 1.0)

    # Determine priority based on number of signals and confidence
    priority = "low"
    if len(reasons) >= 4 and overall_confidence > 0.8:
        priority = "critical"
    elif len(reasons) >= 3 and overall_confidence > 0.7:
        priority = "high"
    elif len(reasons) >= 2 and overall_confidence > 0.6:
        priority = "medium"

    triggered = len(reasons) > 0

    return SignalResult(
        triggered=triggered,
        reasons=reasons,
        confidence=round(overall_confidence, 2),
        metrics=metrics,
        priority=priority
    )
