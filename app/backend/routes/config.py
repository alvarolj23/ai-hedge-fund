from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


class MarketMonitorConfig(BaseModel):
    """Market monitor configuration schema."""
    watchlist: List[str] = Field(..., description="List of ticker symbols to monitor")
    price_breakout_threshold: float = Field(0.02, ge=0.01, le=0.10, description="Price change threshold (e.g., 0.02 = 2%)")
    volume_spike_multiplier: float = Field(1.5, ge=1.0, le=5.0, description="Volume spike multiplier")
    cooldown_seconds: int = Field(1800, ge=300, le=7200, description="Cooldown period in seconds")
    volume_lookback_days: int = Field(10, ge=5, le=30, description="Days for volume average calculation")


class TradingConfig(BaseModel):
    """Trading configuration schema."""
    confidence_threshold: int = Field(70, ge=0, le=100, description="Minimum confidence to execute trades")
    trade_mode: str = Field("paper", description="Trading mode: 'paper' or 'analysis'")
    dry_run: bool = Field(False, description="Simulate trades without executing")
    enabled_agents: Optional[List[str]] = Field(None, description="List of enabled agent names")


@router.get("/monitor")
async def get_monitor_config() -> MarketMonitorConfig:
    """
    Get current market monitor configuration.

    This reads from environment variables and returns the current settings
    for the Function App market monitor.
    """
    try:
        # Read from environment variables
        watchlist_str = os.getenv("MARKET_MONITOR_WATCHLIST", "AAPL,MSFT,NVDA,GOOGL,TSLA")
        watchlist = [ticker.strip() for ticker in watchlist_str.split(",")]

        price_threshold = float(os.getenv("MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD", "0.02"))
        volume_multiplier = float(os.getenv("MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER", "1.5"))
        cooldown = int(os.getenv("MARKET_MONITOR_COOLDOWN_SECONDS", "1800"))
        volume_lookback = int(os.getenv("MARKET_MONITOR_VOLUME_LOOKBACK", "10"))

        return MarketMonitorConfig(
            watchlist=watchlist,
            price_breakout_threshold=price_threshold,
            volume_spike_multiplier=volume_multiplier,
            cooldown_seconds=cooldown,
            volume_lookback_days=volume_lookback
        )
    except Exception as e:
        logger.error(f"Error reading monitor config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")


@router.put("/monitor")
async def update_monitor_config(config: MarketMonitorConfig):
    """
    Update market monitor configuration.

    NOTE: This endpoint returns the configuration that SHOULD be set,
    but does not actually update the Azure Function App environment variables.

    To apply these changes, you need to manually update the Function App
    settings in Azure Portal or using Azure CLI:

    ```bash
    az functionapp config appsettings set \\
        --name aihedgefund-monitor \\
        --resource-group rg-ai-hedge-fund-prod \\
        --settings \\
            MARKET_MONITOR_WATCHLIST="AAPL,MSFT,NVDA" \\
            MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD="0.03"
    ```

    Args:
        config: New configuration values

    Returns:
        Configuration that should be applied
    """
    try:
        # Validate watchlist
        if not config.watchlist or len(config.watchlist) == 0:
            raise HTTPException(status_code=400, detail="Watchlist cannot be empty")

        # Validate all tickers are uppercase and alphanumeric
        validated_watchlist = []
        for ticker in config.watchlist:
            ticker = ticker.strip().upper()
            if not ticker.isalnum():
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid ticker symbol: {ticker}"
                )
            validated_watchlist.append(ticker)

        # Return the configuration for manual application
        return {
            "status": "configuration_ready",
            "message": "Configuration validated. Apply these settings to your Function App.",
            "environment_variables": {
                "MARKET_MONITOR_WATCHLIST": ",".join(validated_watchlist),
                "MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD": str(config.price_breakout_threshold),
                "MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER": str(config.volume_spike_multiplier),
                "MARKET_MONITOR_COOLDOWN_SECONDS": str(config.cooldown_seconds),
                "MARKET_MONITOR_VOLUME_LOOKBACK": str(config.volume_lookback_days)
            },
            "azure_cli_command": f"""az functionapp config appsettings set \\
    --name aihedgefund-monitor \\
    --resource-group rg-ai-hedge-fund-prod \\
    --settings \\
        MARKET_MONITOR_WATCHLIST="{','.join(validated_watchlist)}" \\
        MARKET_MONITOR_PERCENT_CHANGE_THRESHOLD="{config.price_breakout_threshold}" \\
        MARKET_MONITOR_VOLUME_SPIKE_MULTIPLIER="{config.volume_spike_multiplier}" \\
        MARKET_MONITOR_COOLDOWN_SECONDS="{config.cooldown_seconds}" \\
        MARKET_MONITOR_VOLUME_LOOKBACK="{config.volume_lookback_days}"
"""
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@router.get("/trading")
async def get_trading_config() -> TradingConfig:
    """
    Get current trading configuration defaults.

    Returns the default trading settings used by the queue worker.
    """
    try:
        confidence_threshold = int(os.getenv("CONFIDENCE_THRESHOLD", "70"))
        trade_mode = os.getenv("TRADE_MODE", "paper")
        dry_run = os.getenv("DRY_RUN", "false").lower() == "true"

        return TradingConfig(
            confidence_threshold=confidence_threshold,
            trade_mode=trade_mode,
            dry_run=dry_run,
            enabled_agents=None  # All agents enabled by default
        )
    except Exception as e:
        logger.error(f"Error reading trading config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")


@router.put("/trading")
async def update_trading_config(config: TradingConfig):
    """
    Update trading configuration.

    Similar to monitor config, this validates and returns the configuration
    that should be set, but does not directly update environment variables.

    Args:
        config: New trading configuration

    Returns:
        Configuration to be applied
    """
    try:
        # Validate trade mode
        if config.trade_mode not in ["paper", "analysis"]:
            raise HTTPException(
                status_code=400,
                detail="trade_mode must be 'paper' or 'analysis'"
            )

        return {
            "status": "configuration_ready",
            "message": "Trading configuration validated.",
            "environment_variables": {
                "CONFIDENCE_THRESHOLD": str(config.confidence_threshold),
                "TRADE_MODE": config.trade_mode,
                "DRY_RUN": str(config.dry_run).lower()
            },
            "note": "These settings apply to future queue worker executions"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating trading config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")
