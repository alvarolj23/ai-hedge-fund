#!/usr/bin/env python3
"""
Clear all messages from the Azure Storage Queue.

Usage:
    python infra/scripts/clear_queue.py
    python infra/scripts/clear_queue.py --queue-name analysis-requests
"""

import argparse
import json
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


def clear_queue(queue_client, queue_name):
    """Clear all messages from the queue."""
    print(f"\n🗑️  Clearing all messages from queue '{queue_name}'...")

    try:
        # Get approximate message count first
        properties = queue_client.get_queue_properties()
        message_count = properties.approximate_message_count

        if message_count == 0:
            print(f"   Queue is already empty (0 messages)")
            return

        print(f"   Found approximately {message_count} message(s)")

        # Clear all messages
        queue_client.clear_messages()

        print(f"\n✅ Queue cleared successfully!")
        print(f"   All messages have been deleted from '{queue_name}'")

    except Exception as e:
        print(f"\n❌ Failed to clear queue: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Clear all messages from the AI Hedge Fund queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clear the default analysis-requests queue
  python infra/scripts/clear_queue.py

  # Clear a specific queue
  python infra/scripts/clear_queue.py --queue-name analysis-deadletter

Warning:
  This will DELETE ALL MESSAGES from the queue. This action cannot be undone!
        """
    )

    parser.add_argument(
        "--queue-name",
        type=str,
        help="Queue name to clear (default: from deployment outputs)"
    )

    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )

    args = parser.parse_args()

    # Load deployment info
    print("📂 Loading deployment information...")
    outputs = load_deployment_info()

    storage_account_name = outputs.get("storageAccountName", {}).get("value")
    queue_name = args.queue_name or outputs.get("storageQueueName", {}).get("value")

    if not storage_account_name or not queue_name:
        print("ERROR: Missing storage account or queue name")
        sys.exit(1)

    print(f"   Storage Account: {storage_account_name}")
    print(f"   Queue Name: {queue_name}")

    # Confirmation prompt
    if not args.yes:
        print(f"\n⚠️  WARNING: This will DELETE ALL MESSAGES from queue '{queue_name}'")
        response = input("   Are you sure you want to continue? (yes/no): ")
        if response.lower() not in ["yes", "y"]:
            print("\n❌ Operation cancelled")
            sys.exit(0)

    # Get connection string
    print(f"\n🔑 Getting storage account credentials...")
    connection_string = get_connection_string(storage_account_name)

    # Create queue client
    print(f"🔗 Connecting to queue '{queue_name}'...")
    queue_client = QueueClient.from_connection_string(connection_string, queue_name)

    # Clear the queue
    clear_queue(queue_client, queue_name)

    print(f"\n📊 What happens next:")
    print(f"   - Container Apps Job should stop triggering (no messages in queue)")
    print(f"   - You can now send a properly formatted test message")
    print(f"   - Use: python infra/scripts/send_test_message.py")


if __name__ == "__main__":
    main()
