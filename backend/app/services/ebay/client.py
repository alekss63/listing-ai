import os

import httpx
from dotenv import load_dotenv

from backend.app.core.logging import app_logger

load_dotenv()

EBAY_DOMAIN = os.getenv("EBAY_DOMAIN", "https://api.sandbox.ebay.com")
USER_TOKEN = os.getenv("EBAY_USER_TOKEN")


def get_headers() -> dict:
    if not USER_TOKEN:
        raise RuntimeError("EBAY_USER_TOKEN not found in .env")
    return {
        "Authorization": f"Bearer {USER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def test_connection() -> bool:
    """Tests the connection by fetching the user's seller profile."""
    url = f"{EBAY_DOMAIN}/sell/account/v1/program"
    try:
        response = httpx.get(url, headers=get_headers(), timeout=10.0)
        if response.status_code == 200:
            app_logger.info("eBay Sandbox connection successful!")
            return True
        else:
            app_logger.error(
                f"eBay Connection Failed: {response.status_code} - {response.text}"
            )
            return False
    except Exception as e:
        app_logger.error(f"eBay Connection Error: {e}")
        return False
