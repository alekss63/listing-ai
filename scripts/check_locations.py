import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

EBAY_DOMAIN = os.getenv("EBAY_DOMAIN", "https://api.sandbox.ebay.com")
USER_TOKEN = os.getenv("EBAY_USER_TOKEN")


def get_headers():
    return {
        "Authorization": f"Bearer {USER_TOKEN.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }


def main():
    print("1. Fetching existing Sandbox locations...")
    res = httpx.get(
        f"{EBAY_DOMAIN}/sell/inventory/v1/location", headers=get_headers(), timeout=15.0
    )
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}\n")

    print("2. Trying the absolute minimum payload (Postal Code + Country only)...")
    url = f"{EBAY_DOMAIN}/sell/inventory/v1/location/TESTLOC"
    payload = {
        "location": {"address": {"postalCode": "94086", "country": "US"}},
        "name": "TestLoc",
    }
    res = httpx.put(url, headers=get_headers(), json=payload, timeout=15.0)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.text}")


if __name__ == "__main__":
    main()
