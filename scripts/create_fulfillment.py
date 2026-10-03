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
        "Content-Language": "en-US",
        "Accept-Language": "en-US",
    }


VARIANTS = {
    "E: shippingOptions WITHOUT optionType": {
        "categoryGroup": "ALL_EXCLUDING_MOTORS_VEHICLES",
        "marketplaceId": "EBAY_US",
        "name": "ListingAI Fulfillment E",
        "description": "Flat shipping",
        "handlingTime": {"unit": "DAY", "value": 1},
        "shippingOptions": [
            {
                "costTypes": "FLAT",
                "shippingServices": [
                    {
                        "priority": 1,
                        "shippingServiceCode": "USPSFirstClass",
                        "shippingCost": {"value": "5.00", "currency": "USD"},
                    }
                ],
            }
        ],
        "shipToLocations": {
            "regionIncluded": [{"regionName": "US", "regionType": "COUNTRY"}]
        },
    },
    "D: NO shippingOptions at all": {
        "categoryGroup": "ALL_EXCLUDING_MOTORS_VEHICLES",
        "marketplaceId": "EBAY_US",
        "name": "ListingAI Fulfillment D",
        "description": "Handling time only",
        "handlingTime": {"unit": "DAY", "value": 1},
    },
}


def main():
    if not USER_TOKEN:
        print("❌ Token missing.")
        return

    url = f"{EBAY_DOMAIN}/sell/account/v1/fulfillment_policy"

    for label, payload in VARIANTS.items():
        print(f"\n🚚 Trying variant {label}...")
        res = httpx.post(url, headers=get_headers(), json=payload, timeout=15.0)
        if res.status_code in (200, 201):
            print(
                f"✅ SUCCESS! Fulfillment Policy ID: {res.json().get('fulfillmentPolicyId')}"
            )
            return
        print(f"   ❌ {res.status_code}: {res.text[:300]}")

    print(
        "\nBoth variants failed — paste this output and we switch to the API Explorer."
    )


if __name__ == "__main__":
    main()
