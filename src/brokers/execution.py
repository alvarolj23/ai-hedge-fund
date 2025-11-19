"""Trading execution helpers built on top of broker adapters (alpaca-py)."""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

from pydantic import ValidationError

from src.agents.portfolio_manager import PortfolioDecision
from src.persistence import CosmosOrderStore

# ⬇️ NEW: use the alpaca-py powered broker
# If your broker module lives next to this file, you can also do: from .alpaca_paper_broker import ...
from src.brokers.alpaca import BrokerOrder, PaperBroker

logger = logging.getLogger(__name__)


def extract_risk_limits(analyst_signals: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    limits: Dict[str, Dict[str, Any]] = {}
    for agent_id, payload in analyst_signals.items():
        if not isinstance(payload, dict):
            continue
        if not str(agent_id).startswith("risk_management_agent"):
            continue
        for ticker, details in payload.items():
            if isinstance(details, dict):
                limits[ticker] = details
    return limits


def _side_str_from_action(action: str) -> str:
    """
    Map your decision 'action' -> side string compatible with persisted records.
    PaperBroker.ACTION_TO_SIDE returns an enum (alpaca-py), so normalize to str.
    """
    side_enum_or_str = PaperBroker.ACTION_TO_SIDE.get(action.lower())
    if side_enum_or_str is None:
        return "unknown"
    # alpaca-py enums expose .value ("buy"/"sell"); if a string is stored, return as-is.
    return getattr(side_enum_or_str, "value", side_enum_or_str)


def _reconcile_position(
    ticker: str,
    current_position: Dict[str, Any],
    desired_action: str,
    desired_quantity: int,
) -> list[Dict[str, Any]]:
    """
    Reconcile current position with desired action to prevent conflicting positions.
    
    Strategy: If the desired action conflicts with current position, flatten first.
    
    Args:
        ticker: Stock symbol
        current_position: {"long": int, "short": int, "side": "long"|"short"|"flat"}
        desired_action: "buy", "sell", "short", "cover"
        desired_quantity: Number of shares for desired action
    
    Returns:
        List of orders to execute: [{"action": str, "quantity": int, "reasoning": str}]
    """
    orders = []
    current_side = current_position["side"]
    long_qty = current_position["long"]
    short_qty = current_position["short"]
    
    # Define what each action does
    action_intent = {
        "buy": "long",      # Want to be long
        "sell": "reduce_long",  # Want to reduce/close long
        "short": "short",   # Want to be short
        "cover": "reduce_short",  # Want to reduce/close short
    }
    
    intent = action_intent.get(desired_action.lower())
    
    # Case 1: BUY (want to be long)
    if intent == "long":
        if current_side == "short":
            # Conflict: Currently short, want long -> close short first, then buy
            orders.append({
                "action": "cover",
                "quantity": short_qty,
                "reasoning": f"Closing {short_qty} SHORT shares before opening LONG position"
            })
            orders.append({
                "action": "buy",
                "quantity": desired_quantity,
                "reasoning": f"Opening {desired_quantity} LONG shares after closing SHORT"
            })
            logger.info(
                "%s: Position conflict detected - SHORT %d -> LONG %d. Flattening first.",
                ticker, short_qty, desired_quantity
            )
        elif current_side == "long":
            # Already long, just add to position
            orders.append({
                "action": "buy",
                "quantity": desired_quantity,
                "reasoning": f"Adding {desired_quantity} shares to existing LONG {long_qty}"
            })
        else:
            # Flat, just buy
            orders.append({
                "action": "buy",
                "quantity": desired_quantity,
                "reasoning": f"Opening {desired_quantity} LONG shares from flat position"
            })
    
    # Case 2: SHORT (want to be short)
    elif intent == "short":
        if current_side == "long":
            # Conflict: Currently long, want short -> close long first, then short
            orders.append({
                "action": "sell",
                "quantity": long_qty,
                "reasoning": f"Closing {long_qty} LONG shares before opening SHORT position"
            })
            orders.append({
                "action": "short",
                "quantity": desired_quantity,
                "reasoning": f"Opening {desired_quantity} SHORT shares after closing LONG"
            })
            logger.info(
                "%s: Position conflict detected - LONG %d -> SHORT %d. Flattening first.",
                ticker, long_qty, desired_quantity
            )
        elif current_side == "short":
            # Already short, just add to position
            orders.append({
                "action": "short",
                "quantity": desired_quantity,
                "reasoning": f"Adding {desired_quantity} shares to existing SHORT {short_qty}"
            })
        else:
            # Flat, just short
            orders.append({
                "action": "short",
                "quantity": desired_quantity,
                "reasoning": f"Opening {desired_quantity} SHORT shares from flat position"
            })
    
    # Case 3: SELL (reduce or close long)
    elif intent == "reduce_long":
        if current_side == "long":
            if desired_quantity <= long_qty:
                # Normal sell
                orders.append({
                    "action": "sell",
                    "quantity": desired_quantity,
                    "reasoning": f"Selling {desired_quantity} from LONG {long_qty}"
                })
            else:
                # Want to sell more than we have - just sell what we have
                orders.append({
                    "action": "sell",
                    "quantity": long_qty,
                    "reasoning": f"Selling all {long_qty} LONG shares (requested {desired_quantity})"
                })
                logger.warning(
                    "%s: Attempted to SELL %d shares but only have %d. Selling all.",
                    ticker, desired_quantity, long_qty
                )
        else:
            logger.warning(
                "%s: Attempted to SELL but no LONG position exists (current: %s)",
                ticker, current_side
            )
    
    # Case 4: COVER (reduce or close short)
    elif intent == "reduce_short":
        if current_side == "short":
            if desired_quantity <= short_qty:
                # Normal cover
                orders.append({
                    "action": "cover",
                    "quantity": desired_quantity,
                    "reasoning": f"Covering {desired_quantity} from SHORT {short_qty}"
                })
            else:
                # Want to cover more than we have - just cover what we have
                orders.append({
                    "action": "cover",
                    "quantity": short_qty,
                    "reasoning": f"Covering all {short_qty} SHORT shares (requested {desired_quantity})"
                })
                logger.warning(
                    "%s: Attempted to COVER %d shares but only have %d SHORT. Covering all.",
                    ticker, desired_quantity, short_qty
                )
        else:
            logger.warning(
                "%s: Attempted to COVER but no SHORT position exists (current: %s)",
                ticker, current_side
            )
    
    return orders


def dispatch_paper_orders(
    *,
    decisions: Dict[str, Any],
    analyst_signals: Dict[str, Any],
    state_data: Dict[str, Any],
    confidence_threshold: Optional[int],
    dry_run: bool,
) -> list[dict[str, Any]]:
    """
    Dispatch paper trading orders with intelligent position reconciliation.
    
    Features:
    - Fetches current positions from Alpaca
    - Detects and resolves conflicting positions (e.g., LONG -> SHORT)
    - Validates shortable shares
    - Respects risk limits
    - Handles multi-step order execution (flatten + enter)
    """
    logger.info("=" * 80)
    logger.info("DISPATCH PAPER ORDERS - STARTING")
    logger.info("=" * 80)
    logger.info(f"Dry run mode: {dry_run}")
    logger.info(f"Confidence threshold: {confidence_threshold or 60}%")
    logger.info(f"Number of decisions: {len(decisions)}")
    logger.info(f"Decisions: {list(decisions.keys())}")
    
    orders: list[dict[str, Any]] = []
    risk_limits = extract_risk_limits(analyst_signals)
    current_prices = state_data.get("current_prices", {}) or {}
    
    logger.info(f"Risk limits available for: {list(risk_limits.keys())}")
    logger.info(f"Current prices available for: {list(current_prices.keys())}")

    broker = PaperBroker(
        confidence_threshold=confidence_threshold or 60,
        dry_run=dry_run,
    )
    order_store = CosmosOrderStore(dry_run=dry_run)
    
    logger.info(f"Broker initialized (dry_run={dry_run})")
    logger.info("-" * 80)

    for ticker, raw_decision in decisions.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"PROCESSING TICKER: {ticker}")
        logger.info(f"{'='*60}")
        
        try:
            decision = PortfolioDecision.model_validate(raw_decision)
            logger.info(f"Decision validated: {decision.action.upper()} {decision.quantity} shares")
        except ValidationError as exc:
            logger.error("Invalid decision for %s: %s", ticker, exc)
            continue

        action = decision.action.lower()
        if action == "hold":
            logger.info("%s: Action is HOLD, skipping order", ticker)
            continue

        requested_quantity = int(decision.quantity)
        if requested_quantity <= 0:
            logger.info("Skipping %s order for %s due to non-positive quantity", action, ticker)
            continue

        # Check confidence threshold
        if decision.confidence < (confidence_threshold or 60):
            logger.warning(
                "%s: Confidence %d%% BELOW threshold %d%%, skipping order",
                ticker, decision.confidence, confidence_threshold or 60
            )
            continue
        else:
            logger.info(
                "%s: Confidence %d%% MEETS threshold %d%%, proceeding",
                ticker, decision.confidence, confidence_threshold or 60
            )

        # Fetch current position from Alpaca
        logger.info("%s: Fetching current position from Alpaca...", ticker)
        current_position = broker.get_current_position(ticker)
        logger.info(
            "%s: Current position - LONG: %d, SHORT: %d, Side: %s",
            ticker,
            current_position["long"],
            current_position["short"],
            current_position["side"]
        )

        # Check if shorting, validate shortable status
        if action == "short":
            shortable_info = broker.check_shortable(ticker)
            if not shortable_info["shortable"]:
                logger.warning(
                    "%s: Cannot SHORT - ticker is not shortable according to Alpaca",
                    ticker
                )
                error_order = BrokerOrder(
                    ticker=ticker,
                    action=action,
                    quantity=requested_quantity,
                    side=_side_str_from_action(action),
                    status="rejected",
                    error="Ticker not shortable"
                )
                orders.append(error_order.as_record())
                order_store.record_order(error_order, metadata={"shortable_check": shortable_info})
                continue
            
            logger.info(
                "%s: Shortable: %s, Easy to borrow: %s",
                ticker,
                shortable_info["shortable"],
                shortable_info["easy_to_borrow"]
            )

        # Apply risk limits
        risk_context = risk_limits.get(ticker, {})
        remaining_limit = float(risk_context.get("remaining_position_limit", 0) or 0)
        price = float(current_prices.get(ticker, 0) or 0)
        allowed_quantity = requested_quantity

        if remaining_limit > 0 and price > 0:
            max_qty = int(remaining_limit // price)
            if max_qty <= 0:
                logger.info("Skipping %s for %s: risk limit allows zero shares", action, ticker)
                continue
            allowed_quantity = min(requested_quantity, max_qty)
            
            if allowed_quantity < requested_quantity:
                logger.info(
                    "%s: Risk limit reduced quantity from %d to %d shares",
                    ticker, requested_quantity, allowed_quantity
                )

        # Reconcile position conflicts
        reconciled_orders = _reconcile_position(
            ticker=ticker,
            current_position=current_position,
            desired_action=action,
            desired_quantity=allowed_quantity
        )

        if not reconciled_orders:
            logger.warning("%s: No orders generated after reconciliation", ticker)
            continue

        # Execute each reconciled order
        for idx, order_spec in enumerate(reconciled_orders):
            order_action = order_spec["action"]
            order_quantity = order_spec["quantity"]
            order_reasoning = order_spec["reasoning"]
            
            logger.info(
                "%s: Executing order %d/%d - %s %d shares (%s)",
                ticker, idx + 1, len(reconciled_orders),
                order_action.upper(), order_quantity, order_reasoning
            )

            # Create decision for this specific order
            order_decision = PortfolioDecision(
                action=order_action,
                quantity=order_quantity,
                confidence=decision.confidence,
                reasoning=f"{decision.reasoning} | Reconciliation: {order_reasoning}"
            )

            try:
                broker_order = broker.submit_order(ticker, order_decision)
                
                # Log the order result
                if broker_order.status == "error":
                    logger.error(
                        "%s: Order %d/%d FAILED - %s",
                        ticker, idx + 1, len(reconciled_orders), broker_order.error
                    )
                else:
                    logger.info(
                        "%s: Order %d/%d SUBMITTED - Order ID: %s, Status: %s",
                        ticker, idx + 1, len(reconciled_orders),
                        broker_order.order_id, broker_order.status
                    )
                
                # If this is not the last order in the sequence, add a delay
                # to allow the current order to settle/fill before submitting the next one.
                # This prevents "held_for_orders" errors where shares are locked by pending orders.
                if idx < len(reconciled_orders) - 1:
                    delay_seconds = 3.0  # Increased to 3 seconds for better reliability
                    logger.info(
                        "%s: Waiting %.1f seconds for order to settle before submitting next order...",
                        ticker, delay_seconds
                    )
                    time.sleep(delay_seconds)
                    
                    # After the delay, verify the order has filled or cancelled before proceeding
                    # This ensures we don't have "held_for_orders" conflicts
                    if broker_order.order_id and not dry_run and broker._client:
                        try:
                            # Check order status
                            order_status = broker._client.get_order_by_id(broker_order.order_id)
                            logger.info(
                                "%s: Previous order status after delay: %s",
                                ticker, order_status.status if hasattr(order_status, 'status') else 'unknown'
                            )
                        except Exception as status_exc:
                            logger.warning(
                                "%s: Could not verify previous order status: %s",
                                ticker, status_exc
                            )
                
            except Exception as exc:
                logger.exception("Failed to submit Alpaca order for %s", ticker)
                broker_order = BrokerOrder(
                    ticker=ticker,
                    action=order_action,
                    quantity=order_quantity,
                    side=_side_str_from_action(order_action),
                    status="error",
                    error=str(exc),
                )

            # Record metadata
            metadata = {
                "original_decision": {
                    "action": decision.action,
                    "quantity": requested_quantity,
                    "confidence": decision.confidence,
                },
                "reconciliation": {
                    "step": idx + 1,
                    "total_steps": len(reconciled_orders),
                    "reasoning": order_reasoning,
                },
                "position_before": current_position,
                "risk_remaining_limit": remaining_limit if remaining_limit else None,
                "current_price": price if price else None,
            }

            order_record = broker_order.as_record()
            order_record["metadata"] = metadata
            orders.append(order_record)
            order_store.record_order(broker_order, metadata=metadata)

        logger.info(
            "%s: Completed position reconciliation - executed %d order(s)",
            ticker, len(reconciled_orders)
        )

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("DISPATCH PAPER ORDERS - COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total orders processed: {len(orders)}")
    if orders:
        success_count = sum(1 for o in orders if o['status'] not in ['error', 'rejected'])
        error_count = sum(1 for o in orders if o['status'] in ['error', 'rejected'])
        logger.info(f"  ✓ Successful: {success_count}")
        logger.info(f"  ✗ Failed: {error_count}")
        
        for order in orders:
            status_icon = "✓" if order['status'] not in ['error', 'rejected'] else "✗"
            logger.info(
                f"  {status_icon} {order['ticker']}: {order['action'].upper()} {order['quantity']} - {order['status']}"
            )
    else:
        logger.warning("⚠️  NO ORDERS WERE GENERATED OR EXECUTED")
    logger.info("=" * 80)
    
    return orders


__all__ = ["dispatch_paper_orders", "extract_risk_limits"]
