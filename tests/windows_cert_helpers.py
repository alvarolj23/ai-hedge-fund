# windows_cert_helpers.py
import ssl
import ctypes
import sys

# This forces Python's SSLContext to honor the Windows trust store
def patch_ssl_with_windows_trust_store():
    if sys.platform != "win32":
        return

    try:
        # Load the Windows system trusted CA store
        import certifi
        cafile = certifi.where()

        # OpenSSL 1.1+ allows setting default verify locations via APIs
        import ssl
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(cafile)
        # Patch the default context
        ssl._create_default_https_context = ssl.create_default_context
    except Exception as e:
        print("Warning: Couldn't patch SSL trust; HTTPS may fail", e)
