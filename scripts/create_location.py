"""
Creates the ship-from location eBay requires before any listing can be published.

Buyers see the city/state as "Item location" and eBay uses the ZIP for shipping
estimates, so this asks for your real details rather than using a placeholder.
"""

import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.ebay.client import EBAY_DOMAIN, get_headers  # noqa: E402

LOCATION_KEY = "MAINWH"


def headers() -> dict:
    return {
        **get_headers(),
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Content-Language": "en-US",
    }


def main():
    print(f"Environment: {EBAY_DOMAIN}\n")

    existing = httpx.get(
        f"{EBAY_DOMAIN}/sell/inventory/v1/location", headers=headers(), timeout=15.0
    ).json()
    locations = existing.get("locations", [])
    if locations:
        print("✅ You already have a location - nothing to do:")
        for loc in locations:
            address = loc.get("location", {}).get("address", {})
            print(
                f"   {loc['merchantLocationKey']}: {address.get('city')}, "
                f"{address.get('stateOrProvince')} {address.get('postalCode')}"
            )
        return

    print("Where do you ship from? (buyers see the city and state)\n")
    city = input("City: ").strip()
    state = input("State (2 letters, e.g. NY): ").strip().upper()
    postal_code = input("ZIP code: ").strip()
    street = input("Street address (optional, press Enter to skip): ").strip()

    address = {
        "city": city,
        "stateOrProvince": state,
        "postalCode": postal_code,
        "country": "US",
    }
    if street:
        address["addressLine1"] = street

    print(f"\nCreating location '{LOCATION_KEY}' at {city}, {state} {postal_code}...")
    response = httpx.post(
        f"{EBAY_DOMAIN}/sell/inventory/v1/location/{LOCATION_KEY}",
        headers=headers(),
        json={
            "location": {"address": address},
            "name": "ListingAI Ship-From",
            "merchantLocationStatus": "ENABLED",
            "locationTypes": ["WAREHOUSE"],
        },
        timeout=15.0,
    )

    if response.status_code == 204:
        print("✅ Location created. Pushes will now attach it to every offer.")
    else:
        print(f"❌ {response.status_code}: {response.text}")


if __name__ == "__main__":
    main()
