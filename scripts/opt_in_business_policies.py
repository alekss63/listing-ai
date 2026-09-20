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


def main():
    print("🚀 Opting into eBay Business Policies (SELLING_POLICY_MANAGEMENT)...")

    if not USER_TOKEN:
        print("❌ Token is missing from .env")
        return

    url = f"{EBAY_DOMAIN}/sell/account/v1/program/opt_in"
    headers = {
        "Authorization": f"Bearer {USER_TOKEN.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }

    payload = {"programType": "SELLING_POLICY_MANAGEMENT"}

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10.0)
        print(f"HTTP Status Code: {response.status_code}")
        if response.status_code in [200, 204]:
            print("✅ SUCCESS! You are now opted into Business Policies.")
            print(
                "You can now run `python scripts/debug_ebay.py` and it will return 200!"
            )
        else:
            print(f"Response Body:\n{response.text}")
    except Exception as e:
        print(f"Network Error: {e}")


if __name__ == "__main__":
    main()
