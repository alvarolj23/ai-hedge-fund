"""
Dashboard service for fetching and calculating trading analytics.
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)


class DashboardService:
    """Service for dashboard data aggregation and analytics."""

    def __init__(self):
        """Initialize the dashboard service."""
        self.cosmos_available = self._check_cosmos_available()
        self.alpaca_available = self._check_alpaca_available()

    def _check_cosmos_available(self) -> bool:
        """Check if Cosmos DB credentials are configured."""
        return bool(
            os.getenv("COSMOS_ENDPOINT") and
            os.getenv("COSMOS_KEY") and
            os.getenv("COSMOS_DATABASE")
        )

    def _check_alpaca_available(self) -> bool:
        """Check if Alpaca credentials are configured."""
        return bool(
            os.getenv("APCA_API_KEY_ID") and
            os.getenv("APCA_API_SECRET_KEY")
        )

    async def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get current portfolio summary from Alpaca.

        Returns:
            Portfolio summary with positions, cash, and P&L
        """
        if not self.alpaca_available:
            return {
                "error": "Alpaca credentials not configured",
                "total_value": 0,
                "cash": 0,
                "positions_value": 0,
                "buying_power": 0,
                "positions": []
            }

        try:
            # Import here to avoid circular dependencies
            from src.brokers.portfolio_fetcher import fetch_alpaca_portfolio

            # Fetch portfolio from Alpaca
            portfolio_data = fetch_alpaca_portfolio()

            # Extract account info
            account = portfolio_data.get("account", {})
            positions = portfolio_data.get("positions", [])

            # Calculate totals
            total_value = float(account.get("portfolio_value", 0))
            cash = float(account.get("cash", 0))
            buying_power = float(account.get("buying_power", 0))

            # Calculate positions value
            positions_value = sum(
                float(pos.get("market_value", 0)) for pos in positions
            )

            # Format positions with P&L
            formatted_positions = []
            for pos in positions:
                qty = float(pos.get("qty", 0))
                current_price = float(pos.get("current_price", 0))
                avg_entry = float(pos.get("avg_entry_price", 0))
                market_value = float(pos.get("market_value", 0))
                unrealized_pl = float(pos.get("unrealized_pl", 0))
                unrealized_plpc = float(pos.get("unrealized_plpc", 0))

                formatted_positions.append({
                    "ticker": pos.get("symbol"),
                    "quantity": qty,
                    "avg_cost": avg_entry,
                    "current_price": current_price,
                    "market_value": market_value,
                    "unrealized_pl": unrealized_pl,
                    "unrealized_pl_percent": unrealized_plpc * 100,
                    "side": pos.get("side", "long")
                })

            return {
                "total_value": total_value,
                "cash": cash,
                "positions_value": positions_value,
                "buying_power": buying_power,
                "positions": formatted_positions,
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching Alpaca portfolio: {e}")
            return {
                "error": str(e),
                "total_value": 0,
                "cash": 0,
                "positions_value": 0,
                "buying_power": 0,
                "positions": []
            }

    async def get_performance_metrics(self, days: int = 30) -> Dict[str, Any]:
        """
        Calculate trading performance metrics from historical trades.

        Args:
            days: Number of days to analyze

        Returns:
            Performance metrics including win rate, returns, Sharpe ratio
        """
        if not self.cosmos_available:
            return {
                "error": "Cosmos DB not configured",
                "total_trades": 0,
                "win_rate": 0,
                "total_return": 0
            }

        try:
            # Import Cosmos repository
            from src.data.cosmos_repository import CosmosRepository

            repo = CosmosRepository.from_environment()

            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Query broker-orders from Cosmos DB
            query = """
                SELECT * FROM c
                WHERE c.timestamp >= @start_date
                AND c.timestamp <= @end_date
                ORDER BY c.timestamp DESC
            """

            parameters = [
                {"name": "@start_date", "value": start_date.isoformat()},
                {"name": "@end_date", "value": end_date.isoformat()}
            ]

            # Execute query (assuming broker-orders container)
            container = repo.database.get_container_client("broker-orders")
            trades = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))

            # If no trades, return default metrics
            if not trades:
                return {
                    "period_days": days,
                    "total_trades": 0,
                    "win_rate": 0,
                    "wins": 0,
                    "losses": 0,
                    "avg_win": 0,
                    "avg_loss": 0,
                    "profit_factor": 0,
                    "total_return": 0,
                    "sharpe_ratio": 0,
                    "max_drawdown": 0
                }

            # Calculate metrics
            total_trades = len(trades)

            # Separate wins and losses (simplified - would need actual P&L data)
            # For now, we'll estimate based on filled orders
            wins = [t for t in trades if t.get("status") == "filled"]
            losses = []

            win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0

            return {
                "period_days": days,
                "total_trades": total_trades,
                "win_rate": round(win_rate, 2),
                "wins": len(wins),
                "losses": len(losses),
                "avg_win": 0,  # Would need P&L data
                "avg_loss": 0,  # Would need P&L data
                "profit_factor": 0,  # Would need P&L data
                "total_return": 0,  # Would need portfolio history
                "sharpe_ratio": 0,  # Would need returns history
                "max_drawdown": 0,  # Would need portfolio history
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {
                "error": str(e),
                "total_trades": 0,
                "win_rate": 0
            }

    async def get_trade_history(
        self,
        limit: int = 50,
        offset: int = 0,
        ticker: Optional[str] = None,
        action: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get trade history with optional filters.

        Args:
            limit: Maximum number of trades to return
            offset: Number of trades to skip
            ticker: Filter by ticker
            action: Filter by action (buy/sell)
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            Paginated trade history
        """
        if not self.cosmos_available:
            return {
                "trades": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

        try:
            from src.data.cosmos_repository import CosmosRepository

            repo = CosmosRepository.from_environment()

            # Build query
            query_parts = ["SELECT * FROM c WHERE 1=1"]
            parameters = []

            # Add filters
            if ticker:
                query_parts.append("AND c.ticker = @ticker")
                parameters.append({"name": "@ticker", "value": ticker.upper()})

            if action:
                query_parts.append("AND c.action = @action")
                parameters.append({"name": "@action", "value": action.lower()})

            if start_date:
                query_parts.append("AND c.timestamp >= @start_date")
                parameters.append({"name": "@start_date", "value": start_date})

            if end_date:
                query_parts.append("AND c.timestamp <= @end_date")
                parameters.append({"name": "@end_date", "value": end_date})

            # Add ordering
            query_parts.append("ORDER BY c.timestamp DESC")

            # Add pagination
            query_parts.append(f"OFFSET {offset} LIMIT {limit}")

            query = " ".join(query_parts)

            # Execute query
            container = repo.database.get_container_client("broker-orders")
            trades = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))

            # Get total count (without pagination)
            count_query = " ".join(query_parts[:-1])  # Remove OFFSET/LIMIT
            count_query = count_query.replace("SELECT *", "SELECT VALUE COUNT(1)")

            total = list(container.query_items(
                query=count_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))[0] if trades else 0

            return {
                "trades": trades,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(trades)) < total
            }

        except Exception as e:
            logger.error(f"Error fetching trade history: {e}")
            return {
                "error": str(e),
                "trades": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

    async def get_agent_performance(self, days: int = 30) -> Dict[str, Any]:
        """
        Get AI agent performance leaderboard.

        Args:
            days: Number of days to analyze

        Returns:
            Agent performance rankings
        """
        if not self.cosmos_available:
            return {
                "agents": [],
                "period_days": days
            }

        try:
            from src.data.cosmos_repository import CosmosRepository

            repo = CosmosRepository.from_environment()

            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Query analyst-signals from Cosmos DB
            query = """
                SELECT * FROM c
                WHERE c.timestamp >= @start_date
                AND c.timestamp <= @end_date
            """

            parameters = [
                {"name": "@start_date", "value": start_date.isoformat()},
                {"name": "@end_date", "value": end_date.isoformat()}
            ]

            # Execute query
            container = repo.database.get_container_client("analyst-signals")
            signals = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))

            # Aggregate by agent
            agent_stats = defaultdict(lambda: {
                "total_signals": 0,
                "total_confidence": 0,
                "buy_signals": 0,
                "sell_signals": 0,
                "hold_signals": 0
            })

            for signal in signals:
                agent_name = signal.get("agent_name", "Unknown")
                confidence = signal.get("confidence", 0)
                action = signal.get("signal", "hold").lower()

                agent_stats[agent_name]["total_signals"] += 1
                agent_stats[agent_name]["total_confidence"] += confidence

                if action == "buy":
                    agent_stats[agent_name]["buy_signals"] += 1
                elif action == "sell":
                    agent_stats[agent_name]["sell_signals"] += 1
                else:
                    agent_stats[agent_name]["hold_signals"] += 1

            # Format results
            agents = []
            for agent_name, stats in agent_stats.items():
                avg_confidence = (
                    stats["total_confidence"] / stats["total_signals"]
                    if stats["total_signals"] > 0 else 0
                )

                agents.append({
                    "agent_name": agent_name,
                    "total_signals": stats["total_signals"],
                    "avg_confidence": round(avg_confidence, 2),
                    "buy_signals": stats["buy_signals"],
                    "sell_signals": stats["sell_signals"],
                    "hold_signals": stats["hold_signals"],
                    # TODO: Calculate win rate when we have trade outcomes
                    "win_rate": 0
                })

            # Sort by total signals (most active)
            agents.sort(key=lambda x: x["total_signals"], reverse=True)

            return {
                "agents": agents,
                "period_days": days,
                "total_agents": len(agents),
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching agent performance: {e}")
            return {
                "error": str(e),
                "agents": [],
                "period_days": days
            }

    async def get_system_health(self) -> Dict[str, Any]:
        """
        Get system health metrics.

        Returns:
            System operational metrics
        """
        health_data = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }

        # Check Alpaca connection
        if self.alpaca_available:
            try:
                portfolio = await self.get_portfolio_summary()
                health_data["components"]["alpaca"] = {
                    "status": "healthy" if "error" not in portfolio else "degraded",
                    "last_updated": portfolio.get("last_updated")
                }
            except Exception as e:
                health_data["components"]["alpaca"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            health_data["components"]["alpaca"] = {
                "status": "not_configured"
            }

        # Check Cosmos DB connection
        if self.cosmos_available:
            try:
                from src.data.cosmos_repository import CosmosRepository
                repo = CosmosRepository.from_environment()

                # Try a simple query
                container = repo.database.get_container_client("broker-orders")
                list(container.query_items(
                    query="SELECT TOP 1 * FROM c",
                    enable_cross_partition_query=True
                ))

                health_data["components"]["cosmos_db"] = {
                    "status": "healthy"
                }
            except Exception as e:
                health_data["components"]["cosmos_db"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            health_data["components"]["cosmos_db"] = {
                "status": "not_configured"
            }

        # Check queue (if storage account configured)
        queue_available = bool(
            os.getenv("QUEUE_ACCOUNT") and
            os.getenv("QUEUE_NAME")
        )

        if queue_available:
            try:
                from azure.storage.queue import QueueClient

                account_name = os.getenv("QUEUE_ACCOUNT")
                queue_name = os.getenv("QUEUE_NAME", "analysis-requests")
                sas_token = os.getenv("QUEUE_SAS", "")

                queue_url = f"https://{account_name}.queue.core.windows.net/{queue_name}"
                queue_client = QueueClient.from_queue_url(
                    queue_url=queue_url,
                    credential=sas_token
                )

                properties = queue_client.get_queue_properties()
                queue_depth = properties.approximate_message_count

                health_data["components"]["queue"] = {
                    "status": "healthy",
                    "depth": queue_depth
                }
            except Exception as e:
                health_data["components"]["queue"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            health_data["components"]["queue"] = {
                "status": "not_configured"
            }

        return health_data

    async def get_portfolio_history(self, days: int = 30) -> Dict[str, Any]:
        """
        Get historical portfolio values.

        Args:
            days: Number of days of history

        Returns:
            Portfolio value time series
        """
        if not self.cosmos_available:
            return {
                "history": [],
                "period_days": days
            }

        try:
            from src.data.cosmos_repository import CosmosRepository

            repo = CosmosRepository.from_environment()

            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Query portfolioSnapshots from Cosmos DB
            query = """
                SELECT c.timestamp, c.portfolio
                FROM c
                WHERE c.timestamp >= @start_date
                AND c.timestamp <= @end_date
                ORDER BY c.timestamp ASC
            """

            parameters = [
                {"name": "@start_date", "value": start_date.isoformat()},
                {"name": "@end_date", "value": end_date.isoformat()}
            ]

            # Execute query
            container = repo.database.get_container_client("portfolioSnapshots")
            snapshots = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))

            # Format history
            history = []
            for snapshot in snapshots:
                portfolio = snapshot.get("portfolio", {})
                cash = portfolio.get("cash", 0)
                positions = portfolio.get("positions", {})

                # Calculate total positions value (simplified)
                positions_value = sum(
                    pos.get("quantity", 0) * pos.get("current_price", 0)
                    for pos in positions.values()
                )

                total_value = cash + positions_value

                history.append({
                    "date": snapshot.get("timestamp"),
                    "value": total_value,
                    "cash": cash,
                    "positions_value": positions_value
                })

            return {
                "history": history,
                "period_days": days,
                "data_points": len(history),
                "last_updated": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching portfolio history: {e}")
            return {
                "error": str(e),
                "history": [],
                "period_days": days
            }
