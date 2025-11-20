#!/usr/bin/env python3
"""
Send a test message to the Azure Storage Queue for testing the hedge fund worker.

Usage:
    python infra/scripts/send_test_message.py
    python infra/scripts/send_test_message.py --ticker MSFT
    python infra/scripts/send_test_message.py --ticker NVDA --user-id my-user --strategy-id my-strategy
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from azure.storage.queue import QueueClient
except ImportError:
    print("ERROR: azure-storage-queue package not installed")
    print("Install it with: pip install azure-storage-queue")
    sys.exit(1)


def load_deployment_info():
    """Load deployment outputs from latest-deployment.json."""
    script_dir = Path(__file__).parent
    deployment_file = script_dir / "latest-deployment.json"

    if not deployment_file.exists():
        print(f"ERROR: Deployment file not found: {deployment_file}")
        print("Run deploy-with-common-infra.ps1 first to create infrastructure.")
        sys.exit(1)

    try:
        with open(deployment_file, "r", encoding="utf-8-sig") as f:
            content = f.read()
            if not content.strip():
                print(f"ERROR: Deployment file is empty: {deployment_file}")
                print("Run deploy-with-common-infra.ps1 to recreate the deployment configuration.")
                sys.exit(1)
            outputs = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in deployment file: {deployment_file}")
        print(f"JSON Error: {e}")
        print("Run deploy-with-common-infra.ps1 to recreate the deployment configuration.")
        sys.exit(1)

    return outputs


def get_connection_string(storage_account_name):
    """Get storage account connection string using Azure CLI."""
    import subprocess
    import platform

    # On Windows, use az.cmd; on Unix, use az
    az_command = "az.cmd" if platform.system() == "Windows" else "az"

    try:
        result = subprocess.run(
            [
                az_command, "storage", "account", "show-connection-string",
                "--name", storage_account_name,
                "--resource-group", "rg-ai-hedge-fund-prod",
                "--output", "tsv"
            ],
            capture_output=True,
            text=True,
            check=True,
            shell=True  # Use shell on Windows to resolve .cmd files
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to get storage account connection string")
        print(f"Make sure you're logged in with: az login")
        print(f"Error: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("ERROR: Azure CLI (az) not found in PATH")
        print("Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli")
        sys.exit(1)


def send_message(queue_client, message_data):
    """Send a message to the queue with proper JSON encoding."""
    # Ensure the message is properly JSON-encoded
    message_json = json.dumps(message_data, separators=(',', ':'))

    print(f"\n📤 Sending message to queue:")
    print(f"   {json.dumps(message_data, indent=2)}")
    print(f"\n🔍 Raw JSON string (what Azure will receive):")
    print(f"   {message_json}")

    # Send the message
    try:
        response = queue_client.send_message(message_json)
        print(f"\n✅ Message sent successfully!")
        print(f"   Message ID: {response['id']}")
        print(f"   Pop Receipt: {response['pop_receipt']}")
        return response
    except Exception as e:
        print(f"\n❌ Failed to send message: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Send a test message to the AI Hedge Fund queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send default AAPL test message
  python infra/scripts/send_test_message.py

  # Test with different ticker
  python infra/scripts/send_test_message.py --ticker MSFT

  # Test with custom user and strategy
  python infra/scripts/send_test_message.py --ticker NVDA --user-id my-user --strategy-id my-strategy

  # Test with multiple tickers
  python infra/scripts/send_test_message.py --tickers AAPL MSFT GOOGL
        """
    )

    parser.add_argument(
        "--ticker",
        type=str,
        help="Ticker symbol to analyze (e.g., AAPL, MSFT, NVDA)"
    )

    parser.add_argument(
        "--tickers",
        nargs="+",
        type=str,
        help="Multiple ticker symbols to analyze (e.g., AAPL MSFT GOOGL)"
    )

    parser.add_argument(
        "--user-id",
        type=str,
        default="test-user",
        help="User ID for the analysis (default: test-user)"
    )

    parser.add_argument(
        "--strategy-id",
        type=str,
        default="default",
        help="Strategy ID for the analysis (default: default)"
    )

    args = parser.parse_args()

    # Load deployment info
    print("📂 Loading deployment information...")
    outputs = load_deployment_info()

    storage_account_name = outputs.get("storageAccountName", {}).get("value")
    queue_name = outputs.get("storageQueueName", {}).get("value")

    if not storage_account_name or not queue_name:
        print("ERROR: Missing storage account or queue name in deployment outputs")
        sys.exit(1)

    print(f"   Storage Account: {storage_account_name}")
    print(f"   Queue Name: {queue_name}")

    # Get connection string
    print(f"\n🔑 Getting storage account credentials...")
    connection_string = get_connection_string(storage_account_name)

    # Create queue client
    print(f"🔗 Connecting to queue '{queue_name}'...")
    queue_client = QueueClient.from_connection_string(connection_string, queue_name)

    # Build message payload
    message_data = {
        "user_id": args.user_id,
        "strategy_id": args.strategy_id
    }

    # Add ticker(s) to message
    if args.tickers:
        message_data["tickers"] = args.tickers
    elif args.ticker:
        message_data["ticker"] = args.ticker
    else:
        # Default to AAPL
        message_data["ticker"] = "AAPL"

    # Send the message
    send_message(queue_client, message_data)

    print(f"\n📊 Next steps:")
    print(f"   1. Check Container Apps Job executions:")
    print(f"      az containerapp job execution list --name aihedgefund-queuejob --resource-group rg-ai-hedge-fund-prod --output table")
    print(f"   2. View logs from latest execution:")
    print(f"      az containerapp job logs show --name aihedgefund-queuejob --resource-group rg-ai-hedge-fund-prod")
    print(f"   3. Check Cosmos DB for results:")
    print(f"      - portfolios container")
    print(f"      - analyst-signals container")
    print(f"      - decisions container")


if __name__ == "__main__":
    main()
