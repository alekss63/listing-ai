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
    print("🔄 Creating Return Policy...")
    url = f"{EBAY_DOMAIN}/sell/account/v1/return_policy"
    payload = {
        "categoryGroup": "ALL_EXCLUDING_MOTORS_VEHICLES",
        "marketplaceId": "EBAY_US",
        "name": "ListingAI Return Policy",
        "returnsAccepted": True,
        "returnMethod": "MONEY_BACK",
        "returnPeriod": {"value": 30, "unit": "DAY"},
        "returnShippingCostPayer": "BUYER"
    }
    res = httpx.post(url, headers=get_headers(), json=payload, timeout=15.0)
    print(f"Return: {res.status_code} -> {res.text[:200]}")

    print("\n💳 Creating Payment Policy...")
    url = f"{EBAY_DOMAIN}/sell/account/v1/payment_policy"
    payload = {
        "categoryGroup": "ALL_EXCLUDING_MOTORS_VEHICLES",
        "marketplaceId": "EBAY_US",
        "name": "ListingAI Payment Policy"
    }
    res = httpx.post(url, headers=get_headers(), json=payload, timeout=15.0)
    print(f"Payment: {res.status_code} -> {res.text[:200]}")

if __name__ == "__main__":
    main()