import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Explicitly load the .env file from the project root
load_dotenv(PROJECT_ROOT / ".env")

EBAY_DOMAIN = os.getenv("EBAY_DOMAIN", "https://api.sandbox.ebay.com")
USER_TOKEN = os.getenv("EBAY_USER_TOKEN")


def main():
    print("🔍 eBay API Diagnostic Check")
    print(f"Domain: {EBAY_DOMAIN}")
    print(f"Token Found: {'Yes' if USER_TOKEN else 'No'}")
    print(f"Token Length: {len(USER_TOKEN) if USER_TOKEN else 0} characters")
    if USER_TOKEN:
        print(f"Token starts with: {USER_TOKEN[:10].strip()}...")
        if USER_TOKEN != USER_TOKEN.strip():
            print("⚠️  WARNING: Your token has invisible leading or trailing spaces!")
    print("-" * 40)

    if not USER_TOKEN:
        print("❌ Token is missing from .env")
        return

    # SELLING API TEST (Proves we can fetch policies)
    url = f"{EBAY_DOMAIN}/sell/account/v1/return_policy?marketplace_id=EBAY_US"

    headers = {
        "Authorization": f"Bearer {USER_TOKEN.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }

    try:
        response = httpx.get(url, headers=headers, timeout=10.0)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Response Body:\n{response.text}")
    except Exception as e:
        print(f"Network Error: {e}")


if __name__ == "__main__":
    main()
