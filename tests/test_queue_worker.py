"""
Local queue worker test runner with certificate setup.

This script allows running the queue worker locally for testing,
similar to test_alpacapy.py but for queue processing.

Usage:
    python tests/test_queue_worker.py

Environment Variables Required:
    - QUEUE_ACCOUNT: Azure Storage account name
    - QUEUE_NAME: Queue name to poll
    - QUEUE_SAS: SAS token for queue access
    - COSMOS_ENDPOINT: Cosmos DB endpoint
    - COSMOS_KEY: Cosmos DB key
    - COSMOS_DATABASE: Database name
    - CORP_CA_BUNDLE: Path to corporate CA bundle (optional)
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if present

_LOGGER = logging.getLogger(__name__)

# Trust store injection (Windows / corporate root cert scenarios)
try:
    from windows_cert_helpers import patch_ssl_with_windows_trust_store
    patch_ssl_with_windows_trust_store()
    _LOGGER.info("Windows certificate store integration enabled")
except Exception:
    pass

# --- SSL / Certificate setup (corporate CA + certifi) ---
import ssl, certifi, tempfile, urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CORP_CA_BUNDLE = os.getenv(
    "CORP_CA_BUNDLE",
    r"C:\Users\ama5332\OneDrive - Toyota Motor Europe\Documents\certs\TME_certificates_chain.crt"
)


def _create_combined_cert_bundle() -> str:
    sys_bundle = certifi.where()
    if not os.path.exists(CORP_CA_BUNDLE):
        return sys_bundle
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as tf:
        with open(sys_bundle, "r") as f:
            tf.write(f.read())
        tf.write("\n")
        with open(CORP_CA_BUNDLE, "r") as f:
            tf.write(f.read())
        return tf.name


CERT_FILE = _create_combined_cert_bundle()
os.environ["SSL_CERT_FILE"] = CERT_FILE
os.environ["REQUESTS_CA_BUNDLE"] = CERT_FILE
os.environ["CURL_CA_BUNDLE"] = CERT_FILE


def _debug_ssl_environment():
    _LOGGER.info(f"SSL_CERT_FILE={os.environ.get('SSL_CERT_FILE')}")
    _LOGGER.info(f"REQUESTS_CA_BUNDLE={os.environ.get('REQUESTS_CA_BUNDLE')}")
    _LOGGER.info(f"CERT_FILE exists? {os.path.exists(CERT_FILE)}  path={CERT_FILE}")
    _LOGGER.info(f"certifi.where()={certifi.where()}")


# Now import and run the queue worker
from src.jobs.queue_worker import QueueWorker


def run_local_queue_worker():
    """Run the queue worker locally for testing."""
    print("🔧 Setting up local queue worker...")
    print("📋 Environment check:")

    required_env_vars = [
        "QUEUE_ACCOUNT",
        "QUEUE_NAME",
        "QUEUE_SAS",
        "COSMOS_ENDPOINT",
        "COSMOS_KEY",
        "COSMOS_DATABASE",
    ]

    missing_vars = []
    for var in required_env_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * len(value)}")
        else:
            print(f"   ❌ {var}: NOT SET")
            missing_vars.append(var)

    if missing_vars:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("   Please set these in your .env file or environment")
        return

    print("\n🔐 SSL/Certificate setup:")
    _debug_ssl_environment()

    print("\n🚀 Initializing queue worker...")

    try:
        worker = QueueWorker.from_environment()
        print("✅ Queue worker initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize queue worker: {e}")
        return

    print(f"\n📡 Listening for messages on queue: {worker.config.queue_name}")
    print("💡 Send a test message using: infra\\test-queue.ps1 -Tickers \"NVDA\" -LookbackDays 30")
    print("🔄 Worker will process messages as they arrive. Press Ctrl+C to stop.\n")

    # Run in a loop for local testing
    message_count = 0
    try:
        while True:
            try:
                print(f"🔍 Checking for messages... ({message_count} processed so far)")
                processed = worker.run()  # This will process one message and return True/False
                if processed:
                    message_count += 1
                    print("✅ Message processed")
                else:
                    print("⏳ No messages available, waiting...")
                    time.sleep(5)  # Wait 5 seconds before checking again
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                print("⏳ Waiting before retry...")
                time.sleep(5)  # Brief pause before retry...
    except KeyboardInterrupt:
        print("\n🛑 Queue worker stopped by user")

    print(f"\n📊 Session summary: {message_count} messages processed")


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        stream=sys.stdout,
    )

    try:
        run_local_queue_worker()
    except Exception as e:
        print(f"\n💥 Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
