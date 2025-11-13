"""
Python script to send test messages to the Azure Storage Queue.

This script sends properly formatted messages to the analysis-requests queue
for testing the queue worker.

Usage:
    python test_queue_python.py --tickers AAPL --lookback-days 30

Environment Variables Required:
    - QUEUE_ACCOUNT: Azure Storage account name
    - QUEUE_NAME: Queue name to send messages to (default: analysis-requests)
    - QUEUE_SAS: SAS token for queue access
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv

try:
    from azure.core.exceptions import AzureError
    from azure.storage.queue import QueueClient, TextBase64EncodePolicy
except ImportError as exc:
    raise RuntimeError(
        "The Azure Storage Queue SDK is required. Install with: pip install azure-storage-queue"
    ) from exc

load_dotenv()


def create_queue_client():
    """Create and return a QueueClient using environment variables."""
    account = os.getenv("QUEUE_ACCOUNT")
    queue_name = os.getenv("QUEUE_NAME", "analysis-requests")
    sas_token = os.getenv("QUEUE_SAS")

    if not all([account, queue_name, sas_token]):
        missing = [
            name
            for name, value in [
                ("QUEUE_ACCOUNT", account),
                ("QUEUE_NAME", queue_name),
                ("QUEUE_SAS", sas_token),
            ]
            if not value
        ]
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    account_url = f"https://{account}.queue.core.windows.net"

    # Use the same encoding policy as the queue worker
    encode_policy = TextBase64EncodePolicy()

    return QueueClient(
        account_url=account_url,
        queue_name=queue_name,
        credential=sas_token,
        message_encode_policy=encode_policy,
    )


def send_test_message(tickers, lookback_days=30, show_reasoning=True, trade_mode="analysis", dry_run=False):
    """Send a test message to the queue."""
    client = create_queue_client()

    # Build the message payload matching the queue_worker expected format
    now = datetime.now(timezone.utc)

    message_payload = {
        "lookback_days": lookback_days,
        "overrides": {
            "show_reasoning": show_reasoning,
            "trade_mode": trade_mode,  # "analysis" or "paper"
            "dry_run": dry_run,  # If true, simulates orders without executing
        },
        "triggered_at": now.isoformat(),
        "source": "python_test_script"
    }

    # Handle single ticker vs multiple tickers
    if len(tickers) == 1:
        message_payload["ticker"] = tickers[0]
    else:
        message_payload["tickers"] = tickers

    # Convert to JSON
    message_json = json.dumps(message_payload, indent=2)

    print("📤 Sending test message to queue...")
    print(f"Queue: {client.queue_name}")
    print(f"Account: {client.account_name}")
    print("Message payload:")
    print(message_json)
    print()

    try:
        # Send the message - the SDK will handle base64 encoding
        response = client.send_message(message_json)
        print("✅ Message sent successfully!")
        print(f"Message ID: {response.id}")
        print(f"Enqueued at: {response.inserted_on}")
        print()
        print("💡 The queue worker should process this message shortly.")
        print("   Check the logs or Cosmos DB for results.")

    except AzureError as e:
        print(f"❌ Failed to send message: {e}")
        return False

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Send test messages to the Azure Storage Queue"
    )
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=["AAPL"],
        help="Ticker symbols to analyze (space-separated, default: AAPL)"
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=30,
        help="Number of days to look back for analysis (default: 30)"
    )
    parser.add_argument(
        "--no-reasoning",
        action="store_true",
        help="Disable reasoning output in the analysis"
    )
    parser.add_argument(
        "--trade-mode",
        choices=["analysis", "paper"],
        default="analysis",
        help="Trading mode: 'analysis' (no trades) or 'paper' (execute via Alpaca paper trading)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate orders without actually submitting to broker (only relevant if trade-mode=paper)"
    )

    args = parser.parse_args()

    # Validate tickers
    tickers = [ticker.upper().strip() for ticker in args.tickers if ticker.strip()]
    if not tickers:
        print("❌ No valid tickers provided")
        return 1

    print("🔧 Preparing to send test message...")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Lookback days: {args.lookback_days}")
    print(f"Show reasoning: {not args.no_reasoning}")
    print(f"Trade mode: {args.trade_mode}")
    print(f"Dry run: {args.dry_run}")
    print()

    success = send_test_message(
        tickers=tickers,
        lookback_days=args.lookback_days,
        show_reasoning=not args.no_reasoning,
        trade_mode=args.trade_mode,
        dry_run=args.dry_run
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())