"""Utilities to handle corporate CA bundles and patch requests sessions.

This module centralizes creating a combined CA bundle (certifi + corporate CA)
and patching requests sessions so callers can opt-in at application startup.
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Optional

import certifi

log = logging.getLogger(__name__)


def create_combined_cabundle(corp_ca_path: Optional[str] = None) -> Optional[str]:
    """Create a combined certificate bundle file (certifi + corporate CA).

    If `corp_ca_path` exists, write a temporary .pem containing certifi's bundle
    followed by the corporate CA contents. Set environment variables used by
    requests/urllib3 (SSL_CERT_FILE, REQUESTS_CA_BUNDLE, CURL_CA_BUNDLE).

    Returns the path to the created bundle, or None if no corporate CA found.
    """
    corp = corp_ca_path or os.getenv("CORP_CA_BUNDLE")
    if not corp:
        return None
    if not os.path.exists(corp):
        log.debug("Corporate CA not found at %s", corp)
        return None

    sys_bundle = certifi.where()
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as tf:
        with open(sys_bundle, "r", encoding="utf-8") as f:
            tf.write(f.read())
        tf.write("\n")
        with open(corp, "r", encoding="utf-8") as f:
            tf.write(f.read())
        combined = tf.name

    os.environ["SSL_CERT_FILE"] = combined
    os.environ["REQUESTS_CA_BUNDLE"] = combined
    os.environ["CURL_CA_BUNDLE"] = combined

    log.info("Created combined CA bundle: %s", combined)
    return combined


def patch_requests_session(session, cert_file: Optional[str] = None) -> None:
    """Patch a requests.Session-like object to use the provided cert_file for verification.

    If cert_file is omitted, the function will look at REQUESTS_CA_BUNDLE then
    SSL_CERT_FILE environment variables. If a usable file path is found, sets
    session.verify to that path. Safe no-op if session or file not present.
    """
    if session is None:
        return

    final = cert_file or os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    if final and os.path.exists(final):
        try:
            session.verify = final
            log.info("Patched session.verify -> %s", final)
        except Exception:
            log.exception("Failed to patch session.verify")
