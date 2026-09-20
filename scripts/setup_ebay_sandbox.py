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


def ensure_location():
    print("📦 Checking Inventory Locations...")
    res = httpx.get(f"{EBAY_DOMAIN}/sell/inventory/v1/location", headers=get_headers(), timeout=15.0)
    if res.status_code == 200:
        locations = res.json().get("merchantLocations", [])
        if locations:
            print(f"✅ Location already exists: {locations[0].get('merchantLocationKey')}")
            return

    print("   Creating location DEFAULT...")
    payload = {
        "location": {
            "address": {
                "addressLine1": "2055 Hamilton Ave",
                "city": "San Jose",
                "stateOrProvince": "CA",
                "postalCode": "95125",
                "country": "US",
            },
            "geoCoordinates": {"latitude": 37.2708, "longitude": -121.9121},
        },
        "locationInstructions": "ListingAI warehouse",
        "locationTypes": ["WAREHOUSE"],
        "locationWebUrl": "https://www.ebay.com",
        "merchantLocationStatus": "ENABLED",
        "name": "ListingAI Default Warehouse",
        "phone": "408-555-0100",
    }
    res = httpx.put(f"{EBAY_DOMAIN}/sell/inventory/v1/location/DEFAULT", headers=get_headers(), json=payload, timeout=15.0)
    print("✅ Location created!" if res.status_code in (200, 201, 204) else f"❌ Location Error: {res.text}")


def ensure_fulfillment_policy():
    print("🚚 Checking Fulfillment Policies...")
    res = httpx.get(f"{EBAY_DOMAIN}/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US", headers=get_headers(), timeout=15.0)
    if res.status_code == 200 and res.json().get("fulfillmentPolicies"):
        pol = res.json()["fulfillmentPolicies"][0]
        print(f"✅ Fulfillment Policy already exists: {pol['fulfillmentPolicyId']}")
        return

    print("   Creating fulfillment policy...")
    payload = {
        "categoryGroup": "ALL_EXCLUDING_MOTORS_VEHICLES",
        "description": "Standard shipping",
        "freightShipping": False,
        "globalShipping": False,
        "handlingTime": {"unit": "DAY", "value": 1},
        "localPickup": False,
        "marketplaceId": "EBAY_US",
        "name": "ListingAI Fulfillment Policy",
        "shippingOptions": [
            {
                "optionType": "FLAT",
                "shippingServices": [
                    {
                        "freeShipping": True,
                        "priority": 1,
                        "shippingCarrierCode": "USPS",
                        "shippingServiceCode": "USPSFirstClass",
                    }
                ],
            }
        ],
        "shipToLocations": {
            "regionIncluded": [{"regionName": "US", "regionType": "COUNTRY"}]
        },
    }
    res = httpx.post(f"{EBAY_DOMAIN}/sell/account/v1/fulfillment_policy", headers=get_headers(), json=payload, timeout=15.0)
    print("✅ Fulfillment Policy created!" if res.status_code in (200, 201) else f"❌ Fulfillment Error: {res.text}")


def main():
    if not USER_TOKEN:
        print("❌ Token missing.")
        return
    ensure_location()
    ensure_fulfillment_policy()
    print("\n🎉 Setup complete! Now run: python scripts/test_ebay_publish.py")


if __name__ == "__main__":
    main()