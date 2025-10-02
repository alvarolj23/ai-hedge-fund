#!/usr/bin/env python3
"""
Simple standalone test script to verify Alpaca integration by submitting a small paper trade order.
"""

#!/usr/bin/env python3
import os
from datetime import datetime
from dotenv import load_dotenv

from typing_extensions import Literal

from src.brokers.alpaca import PaperBroker
from src.agents.portfolio_manager import PortfolioDecision

import logging

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
# _debug_ssl_environment()


load_dotenv()

# Use the project's PortfolioDecision model so Broker.model_validate() receives
# the exact Pydantic class it expects (avoid duplicate/local model definitions).

def main():
    print("Testing Alpaca (paper) with alpaca-py…")
    print(f"Current time: {datetime.now()}")
    broker = PaperBroker(dry_run=False)
    print(f"Dry run mode: {broker.dry_run}")

    decision = PortfolioDecision(action="buy", quantity=1, confidence=100, reasoning="Smoke test")
    order = broker.submit_order("AAPL", decision)
    print("Order:", order.as_record())

    ok = order.status in {"accepted", "accepted_dry_run", "submitted", "new"}
    print("\n✅ PASS" if ok else "\n❌ FAIL")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
