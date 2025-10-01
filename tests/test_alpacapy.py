from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
import os
import logging

_LOGGER = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file if present

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


client = TradingClient(
    os.environ["APCA_API_KEY_ID"],
    os.environ["APCA_API_SECRET_KEY"],
    paper=True,
)

order = client.submit_order(
    order_data=MarketOrderRequest(
        symbol="AAPL",
        qty=1,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.DAY,
    )
)

print(order.id, order.status, order.submitted_at, order.filled_at)
