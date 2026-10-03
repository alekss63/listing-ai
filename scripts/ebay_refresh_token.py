import base64
import os
import re
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

APP_ID = os.getenv("EBAY_APP_ID")
CERT_ID = os.getenv("EBAY_CERT_ID")
REFRESH_TOKEN = os.getenv("EBAY_REFRESH_TOKEN")

EBAY_DOMAIN = os.getenv("EBAY_DOMAIN", "https://api.sandbox.ebay.com")
TOKEN_ENDPOINT = f"{EBAY_DOMAIN}/identity/v1/oauth2/token"


def update_env(key: str, value: str):
    text = ENV_PATH.read_text()
    pattern = re.compile(rf"^{key}=.*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(f"{key}={value}", text)
    else:
        text = text.rstrip("\n") + f"\n{key}={value}\n"
    ENV_PATH.write_text(text)


def main():
    if not (APP_ID and CERT_ID and REFRESH_TOKEN):
        print("❌ .env needs EBAY_APP_ID, EBAY_CERT_ID and EBAY_REFRESH_TOKEN.")
        print(
            "   If you never saved the refresh token, run `python scripts/ebay_oauth.py`"
        )
        print("   again and save BOTH tokens it prints (user token AND refresh token).")
        return

    credentials = base64.b64encode(f"{APP_ID}:{CERT_ID}".encode()).decode()
    response = httpx.post(
        TOKEN_ENDPOINT,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": REFRESH_TOKEN,
        },
        timeout=15.0,
    )
    result = response.json()

    if "access_token" in result:
        update_env("EBAY_USER_TOKEN", result["access_token"])
        if "refresh_token" in result:
            update_env("EBAY_REFRESH_TOKEN", result["refresh_token"])
        print("✅ Fresh access token saved to .env automatically!")
        print(f"   It expires in {result.get('expires_in')} seconds (~2 hours).")
    else:
        print("❌ Refresh failed:")
        print(result)
        print("\nRun `python scripts/ebay_oauth.py` to get a brand-new token pair.")


if __name__ == "__main__":
    main()
