"""Fetch real-time portfolio data from Alpaca broker."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.utils.ssl_utils import patch_requests_session

try:
    from alpaca.trading.client import TradingClient
except ImportError as exc:
    raise RuntimeError(
        "The alpaca-py SDK is required. Install with: pip install alpaca-py"
    ) from exc

load_dotenv()

logger = logging.getLogger(__name__)


def _env(*names: str) -> Optional[str]:
    """Get first available environment variable from a list of names."""
    for name in names:
        v = os.getenv(name)
        if v:
            return v
    return None


class AlpacaPortfolioFetcher:
    """Fetches real-time portfolio state from Alpaca Paper Trading API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        paper: bool = True,
    ) -> None:
        self._logger = logger
        self.api_key = api_key or _env("APCA_API_KEY_ID", "ALPACA_API_KEY_ID")
        self.api_secret = api_secret or _env("APCA_API_SECRET_KEY", "ALPACA_API_SECRET_KEY")
        self.paper = paper

        if not self.api_key or not self.api_secret:
            raise ValueError(
                "Missing Alpaca credentials. Set APCA_API_KEY_ID and APCA_API_SECRET_KEY "
                "environment variables or pass them explicitly."
            )

        self._client = TradingClient(self.api_key, self.api_secret, paper=self.paper)
        # If the underlying client exposes a requests session, patch verify to use
        # the combined CA bundle if available. We do not create bundles here; that
        # should be done at application startup (tests or entrypoint) by calling
        # src.utils.ssl_utils.create_combined_cabundle().
        try:
            if hasattr(self._client, "_session"):
                patch_requests_session(self._client._session)
        except Exception:
            self._logger.exception("Failed to patch Alpaca client session for SSL")

    def get_portfolio_snapshot(self, tickers: list[str]) -> Dict[str, Any]:
        """
        Fetch current portfolio state from Alpaca and format it to match
        the internal portfolio structure used by the hedge fund system.

        Args:
            tickers: List of ticker symbols to include in the portfolio structure.
                     Even if positions don't exist, we create empty entries for these tickers.

        Returns:
            Dictionary with portfolio snapshot in the expected format:
            {
                "cash": float,
                "margin_requirement": float,
                "margin_used": float,
                "equity": float,
                "buying_power": float,
                "positions": {
                    "TICKER": {
                        "long": int,
                        "short": int,
                        "long_cost_basis": float,
                        "short_cost_basis": float,
                        "short_margin_used": float,
                    }
                },
                "realized_gains": {
                    "TICKER": {
                        "long": float,
                        "short": float,
                    }
                }
            }
        """
        try:
            # Fetch account information
            account = self._client.get_account()
            
            # Fetch all positions
            positions = self._client.get_all_positions()
            
            # Initialize portfolio structure
            portfolio = {
                "cash": float(account.cash),
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "margin_requirement": 0.5,  # Alpaca default for pattern day traders
                "margin_used": 0.0,
                "positions": {},
                "realized_gains": {},
            }
            
            # Initialize empty positions for all requested tickers
            for ticker in tickers:
                portfolio["positions"][ticker] = {
                    "long": 0,
                    "short": 0,
                    "long_cost_basis": 0.0,
                    "short_cost_basis": 0.0,
                    "short_margin_used": 0.0,
                }
                portfolio["realized_gains"][ticker] = {
                    "long": 0.0,
                    "short": 0.0,
                }
            
            # Populate actual positions from Alpaca
            for position in positions:
                ticker = position.symbol
                qty = float(position.qty)
                avg_entry_price = float(position.avg_entry_price)
                
                # Ensure ticker exists in our structure
                if ticker not in portfolio["positions"]:
                    portfolio["positions"][ticker] = {
                        "long": 0,
                        "short": 0,
                        "long_cost_basis": 0.0,
                        "short_cost_basis": 0.0,
                        "short_margin_used": 0.0,
                    }
                    portfolio["realized_gains"][ticker] = {
                        "long": 0.0,
                        "short": 0.0,
                    }
                
                if qty > 0:
                    # Long position
                    portfolio["positions"][ticker]["long"] = int(qty)
                    portfolio["positions"][ticker]["long_cost_basis"] = avg_entry_price
                elif qty < 0:
                    # Short position
                    portfolio["positions"][ticker]["short"] = int(abs(qty))
                    portfolio["positions"][ticker]["short_cost_basis"] = avg_entry_price
                    # Calculate margin used for short position
                    market_value = abs(float(position.market_value))
                    portfolio["positions"][ticker]["short_margin_used"] = market_value * portfolio["margin_requirement"]
                    portfolio["margin_used"] += portfolio["positions"][ticker]["short_margin_used"]
            
            self._logger.info(
                "Fetched portfolio from Alpaca: cash=%.2f, equity=%.2f, positions=%d",
                portfolio["cash"],
                portfolio["equity"],
                len([p for p in portfolio["positions"].values() if p["long"] > 0 or p["short"] > 0])
            )
            
            return portfolio

        except Exception as exc:
            self._logger.exception("Failed to fetch portfolio from Alpaca")
            raise RuntimeError(f"Failed to fetch Alpaca portfolio: {exc}") from exc

    def get_account_info(self) -> Dict[str, Any]:
        """Fetch basic account information for debugging/logging."""
        try:
            account = self._client.get_account()
            return {
                "account_number": account.account_number,
                "cash": float(account.cash),
                "equity": float(account.equity),
                "buying_power": float(account.buying_power),
                "portfolio_value": float(account.portfolio_value),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "transfers_blocked": account.transfers_blocked,
                "account_blocked": account.account_blocked,
                "currency": account.currency,
            }
        except Exception as exc:
            self._logger.exception("Failed to fetch account info from Alpaca")
            raise RuntimeError(f"Failed to fetch Alpaca account info: {exc}") from exc


def get_alpaca_portfolio(tickers: list[str], paper: bool = True) -> Dict[str, Any]:
    """
    Convenience function to fetch portfolio from Alpaca using environment credentials.
    
    Args:
        tickers: List of ticker symbols to include in portfolio structure
        paper: Whether to use paper trading API (default: True)
    
    Returns:
        Portfolio snapshot dictionary
    """
    fetcher = AlpacaPortfolioFetcher(paper=paper)
    return fetcher.get_portfolio_snapshot(tickers)


__all__ = ["AlpacaPortfolioFetcher", "get_alpaca_portfolio"]
