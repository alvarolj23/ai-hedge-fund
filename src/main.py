import sys
import requests
import logging
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging EARLY - before any other imports
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# SSL / Certificate setup for corporate environments (must be done early)
from src.utils.ssl_utils import create_combined_cabundle

try:
    # Try Windows certificate store integration first
    try:
        from windows_cert_helpers import patch_ssl_with_windows_trust_store
        patch_ssl_with_windows_trust_store()
        logger = logging.getLogger(__name__)
        logger.info("Windows certificate store integration enabled")
    except Exception:
        pass
    
    # Create combined CA bundle (certifi + corporate CA)
    CORP_CA_BUNDLE = os.getenv(
        "CORP_CA_BUNDLE",
        r"C:\Users\ama5332\OneDrive - Toyota Motor Europe\Documents\certs\TME_certificates_chain.crt"
    )
    combined_bundle = create_combined_cabundle(CORP_CA_BUNDLE)
    if combined_bundle:
        logger = logging.getLogger(__name__)
        logger.info(f"Combined CA bundle created: {combined_bundle}")
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"SSL setup warning: {e}")

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from colorama import Fore, Style, init
import questionary
from src.agents.portfolio_manager import portfolio_management_agent
from src.agents.risk_manager import risk_management_agent
from src.graph.state import AgentState
from src.utils.display import print_trading_output
from src.utils.analysts import ANALYST_ORDER, get_analyst_nodes
from src.utils.progress import progress
from src.utils.visualize import save_graph_as_png
from src.brokers import dispatch_paper_orders
from typing import Any, Dict, Optional
from src.cli.input import (
    parse_cli_inputs,
)
from src.services.persistence.cosmos import get_cosmos_persistence
from src.utils.portfolio import merge_portfolio_structures
from src.llm.models import LLM_ORDER, OLLAMA_LLM_ORDER, ModelProvider, get_model_info
from src.utils.ollama import ensure_ollama_and_model

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
import json
from uuid import uuid4

# Load environment variables from .env file
load_dotenv()

init(autoreset=True)

logger = logging.getLogger(__name__)

# Create a session with SSL configuration for API requests
_http_session = requests.Session()
from src.utils.ssl_utils import patch_requests_session
patch_requests_session(_http_session)


def parse_hedge_fund_response(response):
    """Parses a JSON string and returns a dictionary."""
    try:
        return json.loads(response)
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}\nResponse: {repr(response)}")
        return None
    except TypeError as e:
        print(f"Invalid response type (expected string, got {type(response).__name__}): {e}")
        return None
    except Exception as e:
        print(f"Unexpected error while parsing response: {e}\nResponse: {repr(response)}")
        return None


def get_current_prices(tickers: list[str]) -> dict[str, float]:
    """Fetch current prices for the given tickers using Yahoo Finance API."""
    prices = {}
    for ticker in tickers:
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
            response = _http_session.get(url, timeout=10)
            data = response.json()
            price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
            prices[ticker] = float(price)
        except Exception as e:
            logger.warning(f"Failed to fetch price for {ticker}: {e}")
            prices[ticker] = 100.0  # Default
    return prices


##### Run the Hedge Fund #####
def run_hedge_fund(
    tickers: list[str],
    start_date: str,
    end_date: str,
    portfolio: dict,
    show_reasoning: bool = False,
    selected_analysts: list[str] = [],
    model_name: str = "gpt-4.1",
    model_provider: str = "OpenAI",
    trade_mode: Optional[str] = None,
    dry_run: bool = False,
    confidence_threshold: Optional[int] = None,
    user_id: str | None = None,
    strategy_id: str | None = None,
    run_id: str | None = None,
):
    persistence = get_cosmos_persistence()
    persistence_enabled = persistence.is_configured

    # Use a deterministic partition identifier even when no user is provided.
    resolved_user_id = user_id or "cli"
    run_identifier = run_id or str(uuid4())
    run_timestamp = datetime.now(timezone.utc).isoformat()

    working_portfolio = deepcopy(portfolio)
    if persistence_enabled:
        persisted_portfolio = persistence.portfolios.load_portfolio(resolved_user_id, strategy_id)
        if persisted_portfolio:
            working_portfolio = merge_portfolio_structures(working_portfolio, persisted_portfolio)

    # Start progress tracking
    progress.start()

    try:
        # Create a new workflow if analysts are customized
        if selected_analysts:
            workflow = create_workflow(selected_analysts)
            agent = workflow.compile()
        else:
            agent = app

        metadata_payload = {
            "show_reasoning": show_reasoning,
            "model_name": model_name,
            "model_provider": model_provider,
            "run_id": run_identifier,
            "run_at": run_timestamp,
            "user_id": resolved_user_id,
        }
        if strategy_id:
            metadata_payload["strategy_id"] = strategy_id

        final_state = agent.invoke(
            {
                "messages": [
                    HumanMessage(
                        content="Make trading decisions based on the provided data.",
                    )
                ],
                "data": {
                    "tickers": tickers,
                    "portfolio": working_portfolio,
                    "start_date": start_date,
                    "end_date": end_date,
                    "analyst_signals": {},
                },
                "metadata": metadata_payload,
            },
        )
        final_state.setdefault("metadata", {}).update(metadata_payload)

        decisions = parse_hedge_fund_response(final_state["messages"][-1].content)
        analyst_signals = final_state["data"].get("analyst_signals", {})
        portfolio_from_state = final_state.get("data", {}).get("portfolio")
        if isinstance(portfolio_from_state, dict):
            working_portfolio = merge_portfolio_structures(working_portfolio, portfolio_from_state)

        decisions_payload = decisions or {}
        analyst_payload = analyst_signals or {}

        if persistence_enabled:
            metadata_document = {
                "tickers": tickers,
                "start_date": start_date,
                "end_date": end_date,
                "model_name": model_name,
                "model_provider": model_provider,
            }

            persistence.analyst_documents.upsert_document(
                run_identifier,
                resolved_user_id,
                analyst_payload,
                strategy_id=strategy_id,
                metadata=metadata_document,
                timestamp=run_timestamp,
            )
            persistence.decision_documents.upsert_document(
                run_identifier,
                resolved_user_id,
                decisions_payload,
                strategy_id=strategy_id,
                metadata=metadata_document,
                timestamp=run_timestamp,
            )
            persistence.portfolios.save_portfolio(
                resolved_user_id,
                working_portfolio,
                strategy_id=strategy_id,
            )

        decisions = parse_hedge_fund_response(final_state["messages"][-1].content)
        analyst_signals = final_state["data"]["analyst_signals"]

        broker_orders: list[dict[str, Any]] = []
        
        # TRADE EXECUTION SECTION
        if trade_mode and trade_mode.lower() == "paper":
            print("\n" + "=" * 80)
            print("TRADE EXECUTION MODE: PAPER TRADING")
            print("=" * 80)
            
            if not decisions:
                print("❌ No trading decisions generated - skipping trade execution")
                logger.warning("Trade mode is 'paper' but no decisions were generated")
            else:
                print(f"✅ Trading decisions generated for {len(decisions)} ticker(s)")
                print(f"📊 Confidence threshold: {confidence_threshold or 60}%")
                print(f"🔧 Dry run mode: {dry_run}")
                
                # Log decisions before execution
                print("\n📋 DECISIONS TO EXECUTE:")
                for ticker, decision in decisions.items():
                    action = decision.get('action', 'unknown')
                    quantity = decision.get('quantity', 0)
                    confidence = decision.get('confidence', 0)
                    print(f"   • {ticker}: {action.upper()} {quantity} shares (confidence: {confidence}%)")
                
                print("\n🚀 Dispatching orders to Alpaca Paper Trading API...")
                print("-" * 80)
                
                try:
                    broker_orders = dispatch_paper_orders(
                        decisions=decisions,
                        analyst_signals=analyst_signals,
                        state_data=final_state["data"],
                        confidence_threshold=confidence_threshold,
                        dry_run=dry_run,
                    )
                    
                    print("-" * 80)
                    if broker_orders:
                        print(f"\n✅ TRADE EXECUTION COMPLETE: {len(broker_orders)} order(s) processed")
                        print("\n📊 ORDER SUMMARY:")
                        for idx, order in enumerate(broker_orders, 1):
                            status_icon = "✅" if order['status'] in ['filled', 'accepted', 'accepted_dry_run'] else "❌"
                            print(f"   {status_icon} Order {idx}: {order['action'].upper()} {order['quantity']} {order['ticker']}")
                            print(f"      Status: {order['status']}")
                            if order.get('error'):
                                print(f"      Error: {order['error']}")
                            if order.get('order_id'):
                                print(f"      Order ID: {order['order_id']}")
                    else:
                        print("\n⚠️  NO ORDERS EXECUTED")
                        print("   Possible reasons:")
                        print("   • Decisions didn't meet confidence threshold")
                        print("   • Risk limits prevented execution")
                        print("   • All actions were 'hold'")
                        
                except Exception as e:
                    print(f"\n❌ ERROR DURING TRADE EXECUTION: {e}")
                    logger.exception("Failed to dispatch paper orders")
                
                print("=" * 80 + "\n")
        else:
            if trade_mode:
                logger.info(f"Trade mode is '{trade_mode}' (not 'paper') - skipping trade execution")
            else:
                logger.info("No trade mode specified - analysis only")

        current_prices = get_current_prices(tickers)

        return {
            "decisions": decisions,
            "analyst_signals": analyst_signals,
            "broker_orders": broker_orders,
            "current_prices": current_prices,
            "run_id": run_identifier,
            "run_at": run_timestamp,
            "user_id": resolved_user_id,
            "strategy_id": strategy_id,
            "portfolio_snapshot": deepcopy(working_portfolio),
        }
    finally:
        # Stop progress tracking
        progress.stop()


def start(state: AgentState):
    """Initialize the workflow with the input message."""
    return state


def create_workflow(selected_analysts=None):
    """Create the workflow with selected analysts."""
    workflow = StateGraph(AgentState)
    workflow.add_node("start_node", start)

    # Get analyst nodes from the configuration
    analyst_nodes = get_analyst_nodes()

    # Default to all analysts if none selected
    if selected_analysts is None:
        selected_analysts = list(analyst_nodes.keys())
    # Add selected analyst nodes
    for analyst_key in selected_analysts:
        node_name, node_func = analyst_nodes[analyst_key]
        workflow.add_node(node_name, node_func)
        workflow.add_edge("start_node", node_name)

    # Always add risk and portfolio management
    workflow.add_node("risk_management_agent", risk_management_agent)
    workflow.add_node("portfolio_manager", portfolio_management_agent)

    # Connect selected analysts to risk management
    for analyst_key in selected_analysts:
        node_name = analyst_nodes[analyst_key][0]
        workflow.add_edge(node_name, "risk_management_agent")

    workflow.add_edge("risk_management_agent", "portfolio_manager")
    workflow.add_edge("portfolio_manager", END)

    workflow.set_entry_point("start_node")
    return workflow


# Create default compiled workflow for use when no analysts are specified
# This is used by the queue worker and other non-CLI entry points
app = create_workflow().compile()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the hedge fund trading system")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Initial cash position. Defaults to 100000.0)")
    parser.add_argument("--margin-requirement", type=float, default=0.0, help="Initial margin requirement. Defaults to 0.0")
    parser.add_argument("--tickers", type=str, required=True, help="Comma-separated list of stock ticker symbols")
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD). Defaults to 3 months before end date",
    )
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD). Defaults to today")
    parser.add_argument("--show-reasoning", action="store_true", help="Show reasoning from each agent")
    parser.add_argument("--show-agent-graph", action="store_true", help="Show the agent graph")
    parser.add_argument("--ollama", action="store_true", help="Use Ollama for local LLM inference")
    parser.add_argument(
        "--trade-mode",
        choices=["analysis", "paper"],
        default="analysis",
        help="Choose 'paper' to execute trades via Alpaca's paper trading API",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip actual broker submission even when trade mode is paper",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=int,
        default=None,
        help="Minimum confidence (0-100) required before submitting a broker order",
    )

    args = parser.parse_args()

    # Parse tickers from comma-separated string
    tickers = [ticker.strip() for ticker in args.tickers.split(",")]

    # Select analysts
    selected_analysts = None
    choices = questionary.checkbox(
        "Select your AI analysts.",
        choices=[questionary.Choice(display, value=value) for display, value in ANALYST_ORDER],
        instruction="\n\nInstructions: \n1. Press Space to select/unselect analysts.\n2. Press 'a' to select/unselect all.\n3. Press Enter when done to run the hedge fund.\n",
        validate=lambda x: len(x) > 0 or "You must select at least one analyst.",
        style=questionary.Style(
            [
                ("checkbox-selected", "fg:green"),
                ("selected", "fg:green noinherit"),
                ("highlighted", "noinherit"),
                ("pointer", "noinherit"),
            ]
        ),
    ).ask()

    if not choices:
        print("\n\nInterrupt received. Exiting...")
        sys.exit(0)
    else:
        selected_analysts = choices
        print(f"\nSelected analysts: {', '.join(Fore.GREEN + choice.title().replace('_', ' ') + Style.RESET_ALL for choice in choices)}\n")

    # Select LLM model based on whether Ollama is being used
    model_name = ""
    model_provider = ""

    if args.ollama:
        print(f"{Fore.CYAN}Using Ollama for local LLM inference.{Style.RESET_ALL}")

        # Select from Ollama-specific models
        model_name: str = questionary.select(
            "Select your Ollama model:",
            choices=[questionary.Choice(display, value=value) for display, value, _ in OLLAMA_LLM_ORDER],
            style=questionary.Style(
                [
                    ("selected", "fg:green bold"),
                    ("pointer", "fg:green bold"),
                    ("highlighted", "fg:green"),
                    ("answer", "fg:green bold"),
                ]
            ),
        ).ask()

        if not model_name:
            print("\n\nInterrupt received. Exiting...")
            sys.exit(0)

        if model_name == "-":
            model_name = questionary.text("Enter the custom model name:").ask()
            if not model_name:
                print("\n\nInterrupt received. Exiting...")
                sys.exit(0)

        # Ensure Ollama is installed, running, and the model is available
        if not ensure_ollama_and_model(model_name):
            print(f"{Fore.RED}Cannot proceed without Ollama and the selected model.{Style.RESET_ALL}")
            sys.exit(1)

        model_provider = ModelProvider.OLLAMA.value
        print(f"\nSelected {Fore.CYAN}Ollama{Style.RESET_ALL} model: {Fore.GREEN + Style.BRIGHT}{model_name}{Style.RESET_ALL}\n")
    else:
        # Use the standard cloud-based LLM selection
        model_choice = questionary.select(
            "Select your LLM model:",
            choices=[questionary.Choice(display, value=(name, provider)) for display, name, provider in LLM_ORDER],
            style=questionary.Style(
                [
                    ("selected", "fg:green bold"),
                    ("pointer", "fg:green bold"),
                    ("highlighted", "fg:green"),
                    ("answer", "fg:green bold"),
                ]
            ),
        ).ask()

        if not model_choice:
            print("\n\nInterrupt received. Exiting...")
            sys.exit(0)

        model_name, model_provider = model_choice

        # Get model info using the helper function
        model_info = get_model_info(model_name, model_provider)
        if model_info:
            if model_info.is_custom():
                model_name = questionary.text("Enter the custom model name:").ask()
                if not model_name:
                    print("\n\nInterrupt received. Exiting...")
                    sys.exit(0)

            print(f"\nSelected {Fore.CYAN}{model_provider}{Style.RESET_ALL} model: {Fore.GREEN + Style.BRIGHT}{model_name}{Style.RESET_ALL}\n")
        else:
            model_provider = "Unknown"
            print(f"\nSelected model: {Fore.GREEN + Style.BRIGHT}{model_name}{Style.RESET_ALL}\n")

    # Create the workflow with selected analysts
    workflow = create_workflow(selected_analysts)
    app = workflow.compile()

    if args.show_agent_graph:
        file_path = ""
        if selected_analysts is not None:
            for selected_analyst in selected_analysts:
                file_path += selected_analyst + "_"
            file_path += "graph.png"
        save_graph_as_png(app, file_path)

    # Validate dates if provided
    if args.start_date:
        try:
            datetime.strptime(args.start_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Start date must be in YYYY-MM-DD format")

    if args.end_date:
        try:
            datetime.strptime(args.end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("End date must be in YYYY-MM-DD format")

    # Set the start and end dates
    end_date = args.end_date or datetime.now().strftime("%Y-%m-%d")
    if not args.start_date:
        # Calculate 3 months before end_date
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        start_date = (end_date_obj - relativedelta(months=3)).strftime("%Y-%m-%d")
    else:
        start_date = args.start_date

    # Initialize portfolio with cash amount and stock positions
    portfolio = {
        "cash": args.initial_cash,
        "margin_requirement": args.margin_requirement,
        "margin_used": 0.0,
        "positions": {
            ticker: {
                "long": 0,
                "short": 0,
                "long_cost_basis": 0.0,
                "short_cost_basis": 0.0,
                "short_margin_used": 0.0,
            }
            for ticker in tickers
        },
        "realized_gains": {
            ticker: {
                "long": 0.0,
                "short": 0.0,
            }
            for ticker in tickers
        },
    }

    result = run_hedge_fund(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        portfolio=portfolio,
        show_reasoning=args.show_reasoning,
        selected_analysts=selected_analysts,
        model_name=model_name,
        model_provider=model_provider,
        trade_mode=args.trade_mode,
        dry_run=args.dry_run,
        confidence_threshold=args.confidence_threshold,
    )
    print_trading_output(result)
