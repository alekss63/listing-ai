import base64
import os
import time

import httpx
from dotenv import load_dotenv

from backend.app.core.logging import app_logger

load_dotenv()

EBAY_DOMAIN = os.getenv("EBAY_DOMAIN", "https://api.sandbox.ebay.com")
TOKEN_ENDPOINT = f"{EBAY_DOMAIN}/identity/v1/oauth2/token"

# Refresh this many seconds before eBay's stated expiry to avoid edge-of-expiry 401s
_EXPIRY_MARGIN = 60

_cached_token: str | None = None
_cached_expiry: float = 0.0


def _refresh_access_token() -> tuple[str, int]:
    """Exchanges EBAY_REFRESH_TOKEN for a new access token. Returns (token, expires_in)."""
    # Re-read .env so a refresh token saved by scripts/ebay_oauth.py is picked up
    # without restarting the server
    load_dotenv(override=True)
    app_id = os.getenv("EBAY_APP_ID")
    cert_id = os.getenv("EBAY_CERT_ID")
    refresh_token = os.getenv("EBAY_REFRESH_TOKEN")

    credentials = base64.b64encode(f"{app_id}:{cert_id}".encode()).decode()
    response = httpx.post(
        TOKEN_ENDPOINT,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        timeout=15.0,
    )
    result = response.json()
    if "access_token" not in result:
        raise RuntimeError(
            f"eBay token refresh failed: {result}. "
            "Run `python scripts/ebay_oauth.py` to get a new refresh token."
        )
    app_logger.info("Refreshed eBay access token.")
    return result["access_token"], int(result.get("expires_in", 7200))


def get_access_token() -> str:
    """
    Returns a valid user access token. If EBAY_REFRESH_TOKEN is set, tokens are
    minted and renewed automatically; otherwise falls back to the static
    EBAY_USER_TOKEN (which expires after ~2 hours).
    """
    global _cached_token, _cached_expiry

    if os.getenv("EBAY_REFRESH_TOKEN"):
        if not _cached_token or time.time() >= _cached_expiry:
            token, expires_in = _refresh_access_token()
            _cached_token = token
            _cached_expiry = time.time() + expires_in - _EXPIRY_MARGIN
        return _cached_token

    user_token = os.getenv("EBAY_USER_TOKEN")
    if not user_token:
        raise RuntimeError(
            "No eBay credentials: set EBAY_REFRESH_TOKEN (recommended) or "
            "EBAY_USER_TOKEN in .env"
        )
    return user_token.strip()


def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {get_access_token()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def test_connection() -> bool:
    """Tests the connection by fetching the user's seller profile."""
    url = f"{EBAY_DOMAIN}/sell/account/v1/program"
    try:
        response = httpx.get(url, headers=get_headers(), timeout=10.0)
        if response.status_code == 200:
            app_logger.info("eBay connection successful!")
            return True
        else:
            app_logger.error(
                f"eBay Connection Failed: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        app_logger.error(f"eBay Connection Error: {e}")
        return False
