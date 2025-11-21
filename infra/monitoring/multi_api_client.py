"""
Multi-API client for real-time market data
Integrates: Finnhub, Polygon, Alpha Vantage, yfinance (all free tiers)
"""
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import requests


@dataclass
class Quote:
    """Real-time quote data"""
    ticker: str
    price: float
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    volume: int
    timestamp: datetime
    source: str


@dataclass
class IntradayBar:
    """Intraday OHLCV bar"""
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime
    vwap: Optional[float] = None
    transactions: Optional[int] = None


@dataclass
class TechnicalIndicator:
    """Technical indicator values"""
    ticker: str
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    timestamp: datetime = None


class FinnhubClient:
    """Finnhub API client for real-time quotes and news"""

    BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        if not self.api_key:
            logging.warning("FINNHUB_API_KEY not set, Finnhub integration disabled")

    def get_quote(self, ticker: str) -> Optional[Quote]:
        """Get real-time quote (60 calls/min free tier)"""
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/quote"
            params = {"symbol": ticker, "token": self.api_key}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                logging.warning(f"Finnhub quote failed for {ticker}: {response.status_code}")
                return None

            data = response.json()

            # Finnhub returns: c (current), h (high), l (low), o (open), pc (previous close), t (timestamp)
            return Quote(
                ticker=ticker,
                price=data.get("c", 0.0),
                bid=data.get("c", 0.0),  # Finnhub doesn't provide bid/ask in free tier
                ask=data.get("c", 0.0),
                bid_size=0,
                ask_size=0,
                volume=0,  # Not provided in quote endpoint
                timestamp=datetime.fromtimestamp(data.get("t", time.time()), tz=timezone.utc),
                source="finnhub"
            )
        except Exception as exc:
            logging.error(f"Finnhub error for {ticker}: {exc}")
            return None

    def get_news(self, ticker: str, from_date: str = None, to_date: str = None) -> list[dict]:
        """Get company news (free tier)"""
        if not self.api_key:
            return []

        try:
            url = f"{self.BASE_URL}/company-news"
            params = {
                "symbol": ticker,
                "from": from_date or datetime.now().strftime("%Y-%m-%d"),
                "to": to_date or datetime.now().strftime("%Y-%m-%d"),
                "token": self.api_key
            }
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                return response.json()
            return []
        except Exception as exc:
            logging.error(f"Finnhub news error for {ticker}: {exc}")
            return []


class PolygonClient:
    """Polygon.io API client for aggregates and volume data"""

    BASE_URL = "https://api.polygon.io/v2"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            logging.warning("POLYGON_API_KEY not set, Polygon integration disabled")

    def get_previous_close(self, ticker: str) -> Optional[dict]:
        """Get previous day's close (free tier)"""
        if not self.api_key:
            return None

        try:
            url = f"{self.BASE_URL}/aggs/ticker/{ticker}/prev"
            params = {"apiKey": self.api_key}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get("results"):
                    return data["results"][0]
            return None
        except Exception as exc:
            logging.error(f"Polygon error for {ticker}: {exc}")
            return None

    def get_aggregates(self, ticker: str, multiplier: int = 1, timespan: str = "minute",
                      from_date: str = None, to_date: str = None, limit: int = 120) -> list[IntradayBar]:
        """Get aggregate bars (free tier: limited)"""
        if not self.api_key:
            return []

        try:
            # Format: /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}
            url = f"{self.BASE_URL}/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
            params = {"adjusted": "true", "sort": "asc", "limit": limit, "apiKey": self.api_key}
            response = requests.get(url, params=params, timeout=10)

            if response.status_code != 200:
                logging.warning(f"Polygon aggregates failed for {ticker}: {response.status_code}")
                return []

            data = response.json()
            bars = []

            for bar in data.get("results", []):
                bars.append(IntradayBar(
                    ticker=ticker,
                    open=bar["o"],
                    high=bar["h"],
                    low=bar["l"],
                    close=bar["c"],
                    volume=bar["v"],
                    vwap=bar.get("vw"),
                    transactions=bar.get("n"),
                    timestamp=datetime.fromtimestamp(bar["t"] / 1000, tz=timezone.utc)
                ))

            return bars
        except Exception as exc:
            logging.error(f"Polygon aggregates error for {ticker}: {exc}")
            return []


class AlphaVantageClient:
    """Alpha Vantage API client for technical indicators"""

    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            logging.warning("ALPHA_VANTAGE_API_KEY not set, Alpha Vantage integration disabled")

    def get_rsi(self, ticker: str, interval: str = "5min", time_period: int = 14) -> Optional[float]:
        """Get RSI indicator (25 calls/day free tier)"""
        if not self.api_key:
            return None

        try:
            params = {
                "function": "RSI",
                "symbol": ticker,
                "interval": interval,
                "time_period": time_period,
                "series_type": "close",
                "apikey": self.api_key
            }
            response = requests.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()
                technical_analysis = data.get("Technical Analysis: RSI", {})
                if technical_analysis:
                    # Get most recent value
                    latest_time = sorted(technical_analysis.keys(), reverse=True)[0]
                    return float(technical_analysis[latest_time]["RSI"])
            return None
        except Exception as exc:
            logging.error(f"Alpha Vantage RSI error for {ticker}: {exc}")
            return None

    def get_intraday(self, ticker: str, interval: str = "5min") -> list[IntradayBar]:
        """Get intraday prices (25 calls/day free tier)"""
        if not self.api_key:
            return []

        try:
            params = {
                "function": "TIME_SERIES_INTRADAY",
                "symbol": ticker,
                "interval": interval,
                "apikey": self.api_key,
                "outputsize": "compact"  # Last 100 data points
            }
            response = requests.get(self.BASE_URL, params=params, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            time_series = data.get(f"Time Series ({interval})", {})
            bars = []

            for timestamp_str, values in time_series.items():
                bars.append(IntradayBar(
                    ticker=ticker,
                    open=float(values["1. open"]),
                    high=float(values["2. high"]),
                    low=float(values["3. low"]),
                    close=float(values["4. close"]),
                    volume=int(values["5. volume"]),
                    timestamp=datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                ))

            return sorted(bars, key=lambda x: x.timestamp)
        except Exception as exc:
            logging.error(f"Alpha Vantage intraday error for {ticker}: {exc}")
            return []


class YFinanceClient:
    """yfinance client for fallback/validation (no API key needed)"""

    def get_quote(self, ticker: str) -> Optional[Quote]:
        """Get real-time quote using yfinance"""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            info = stock.info

            return Quote(
                ticker=ticker,
                price=info.get("currentPrice", info.get("regularMarketPrice", 0.0)),
                bid=info.get("bid", 0.0),
                ask=info.get("ask", 0.0),
                bid_size=info.get("bidSize", 0),
                ask_size=info.get("askSize", 0),
                volume=info.get("volume", 0),
                timestamp=datetime.now(timezone.utc),
                source="yfinance"
            )
        except ImportError:
            logging.warning("yfinance not installed, skipping yfinance integration")
            return None
        except Exception as exc:
            logging.error(f"yfinance error for {ticker}: {exc}")
            return None

    def get_intraday(self, ticker: str, period: str = "1d", interval: str = "1m") -> list[IntradayBar]:
        """Get intraday data (1m bars for last 7 days)"""
        try:
            import yfinance as yf

            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)

            bars = []
            for idx, row in hist.iterrows():
                bars.append(IntradayBar(
                    ticker=ticker,
                    open=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=int(row["Volume"]),
                    timestamp=idx.to_pydatetime().replace(tzinfo=timezone.utc)
                ))

            return bars
        except ImportError:
            logging.warning("yfinance not installed")
            return []
        except Exception as exc:
            logging.error(f"yfinance intraday error for {ticker}: {exc}")
            return []


class MultiAPIClient:
    """Unified client that tries multiple APIs with fallback"""

    def __init__(self):
        self.finnhub = FinnhubClient()
        self.polygon = PolygonClient()
        self.alpha_vantage = AlphaVantageClient()
        self.yfinance = YFinanceClient()

    def get_best_quote(self, ticker: str) -> Optional[Quote]:
        """Get quote from the first available source"""
        # Try Finnhub first (fastest, 60/min)
        quote = self.finnhub.get_quote(ticker)
        if quote and quote.price > 0:
            return quote

        # Fallback to yfinance (no rate limit)
        quote = self.yfinance.get_quote(ticker)
        if quote and quote.price > 0:
            return quote

        logging.warning(f"Failed to get quote for {ticker} from all sources")
        return None

    def get_intraday_bars(self, ticker: str, interval_minutes: int = 5, limit: int = 120) -> list[IntradayBar]:
        """Get intraday bars from the best available source"""
        # Try yfinance first (no API key needed, reliable)
        interval_map = {1: "1m", 5: "5m", 15: "15m", 30: "30m", 60: "1h"}
        yf_interval = interval_map.get(interval_minutes, "5m")
        bars = self.yfinance.get_intraday(ticker, period="1d", interval=yf_interval)

        if bars:
            return bars[-limit:]

        # Fallback to Alpha Vantage
        av_interval_map = {1: "1min", 5: "5min", 15: "15min", 30: "30min", 60: "60min"}
        av_interval = av_interval_map.get(interval_minutes, "5min")
        bars = self.alpha_vantage.get_intraday(ticker, interval=av_interval)

        if bars:
            return bars[-limit:]

        logging.warning(f"Failed to get intraday bars for {ticker}")
        return []
