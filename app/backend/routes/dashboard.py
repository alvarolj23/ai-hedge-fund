from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
import logging

from app.backend.services.dashboard_service import DashboardService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/portfolio")
async def get_portfolio_summary():
    """
    Get current portfolio summary from Alpaca Paper Trading API.

    Returns:
        - Total account value
        - Cash available
        - Buying power
        - Current positions with P&L
    """
    try:
        service = DashboardService()
        portfolio = await service.get_portfolio_summary()
        return portfolio
    except Exception as e:
        logger.error(f"Error fetching portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio: {str(e)}")


@router.get("/metrics")
async def get_performance_metrics(days: int = Query(30, ge=1, le=365)):
    """
    Get trading performance metrics over the specified time period.

    Args:
        days: Number of days to analyze (default: 30)

    Returns:
        - Total trades
        - Win rate
        - Average win/loss
        - Profit factor
        - Sharpe ratio
        - Total return
        - Max drawdown
    """
    try:
        service = DashboardService()
        metrics = await service.get_performance_metrics(days)
        return metrics
    except Exception as e:
        logger.error(f"Error calculating performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate metrics: {str(e)}")


@router.get("/trades")
async def get_trade_history(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    ticker: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get trade history from Cosmos DB broker-orders container.

    Args:
        limit: Maximum number of trades to return
        offset: Number of trades to skip (pagination)
        ticker: Filter by ticker symbol (optional)
        action: Filter by action (buy, sell, short) (optional)
        start_date: Filter by start date (YYYY-MM-DD) (optional)
        end_date: Filter by end date (YYYY-MM-DD) (optional)

    Returns:
        List of trades with details and pagination info
    """
    try:
        service = DashboardService()
        trades = await service.get_trade_history(
            limit=limit,
            offset=offset,
            ticker=ticker,
            action=action,
            start_date=start_date,
            end_date=end_date
        )
        return trades
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch trades: {str(e)}")


@router.get("/agent-performance")
async def get_agent_performance(days: int = Query(30, ge=1, le=365)):
    """
    Get AI agent performance leaderboard.

    Analyzes which agents provide the most accurate signals by comparing
    their recommendations against actual trade outcomes.

    Args:
        days: Number of days to analyze (default: 30)

    Returns:
        List of agents with:
        - Agent name
        - Total signals
        - Win rate
        - Average confidence
        - P&L contribution
    """
    try:
        service = DashboardService()
        leaderboard = await service.get_agent_performance(days)
        return leaderboard
    except Exception as e:
        logger.error(f"Error fetching agent performance: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch agent performance: {str(e)}")


@router.get("/system-health")
async def get_system_health():
    """
    Get system health and operational metrics.

    Returns:
        - Queue depth
        - Recent analysis success rate
        - Average analysis time
        - Failed analyses count
        - LLM cost tracking (if LangSmith enabled)
    """
    try:
        service = DashboardService()
        health = await service.get_system_health()
        return health
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch system health: {str(e)}")


@router.get("/portfolio-history")
async def get_portfolio_history(days: int = Query(30, ge=1, le=365)):
    """
    Get historical portfolio values for charting.

    Args:
        days: Number of days of history (default: 30)

    Returns:
        Array of {date, value} objects for portfolio value over time
    """
    try:
        service = DashboardService()
        history = await service.get_portfolio_history(days)
        return history
    except Exception as e:
        logger.error(f"Error fetching portfolio history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch portfolio history: {str(e)}")
