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

# This is the absolute bare minimum required payload
MINIMAL_PAYLOAD = {
    "location": {
        "address": {
            "addressLine1": "123 Main St",
            "city": "San Jose",
            "stateOrProvince": "CA",
            "postalCode": "95125",
            "country": "US"
        }
    },
    "name": "ListingAI Warehouse",
    "merchantLocationStatus": "ENABLED"
}

VARIANTS = {
    "A: Key 'MAINWH' (No optional fields)": ("MAINWH", MINIMAL_PAYLOAD),
    "B: Key 'DEFAULT' (No optional fields)": ("DEFAULT", MINIMAL_PAYLOAD),
    "C: Key 'MAINWH' with simple WebUrl": ("MAINWH", {
        **MINIMAL_PAYLOAD,
        "locationWebUrl": "http://localhost"
    }),
}

def main():
    if not USER_TOKEN:
        print("❌ Token missing.")
        return

    for label, (key, payload) in VARIANTS.items():
        print(f"\n📦 Trying variant {label}...")
        url = f"{EBAY_DOMAIN}/sell/inventory/v1/location/{key}"
        res = httpx.put(url, headers=get_headers(), json=payload, timeout=15.0)
        
        if res.status_code in (200, 201, 204):
            print(f"✅ SUCCESS! Location created with key: {key}")
            return
        print(f"   ❌ {res.status_code}: {res.text[:300]}")

    print("\nAll variants failed.")

if __name__ == "__main__":
    main()