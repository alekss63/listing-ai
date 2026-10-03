import json
from pathlib import Path
from urllib.parse import quote

import httpx

from backend.app.core.logging import app_logger
from backend.app.services.ebay.client import EBAY_DOMAIN, get_headers

# eBay Condition Enum mapping
CONDITION_MAP = {
    "New without tags, Store Display": "NEW_OTHER",
    "New with imperfections": "NEW_WITH_DEFECTS",
    "Pre-owned": "USED",
    "New with tags": "NEW",
}


def get_default_policy_ids() -> dict:
    """Fetches the default Return, Fulfillment, and Payment policy IDs for the sandbox user."""
    headers = get_headers()
    headers["X-EBAY-C-MARKETPLACE-ID"] = "EBAY_US"

    policies = {}

    # Fetch Return Policies
    url = f"{EBAY_DOMAIN}/sell/account/v1/return_policy?marketplace_id=EBAY_US"
    try:
        res = httpx.get(url, headers=headers, timeout=15.0).json()
        policies["return"] = res["returnPolicies"][0]["returnPolicyId"]
    except Exception as e:
        app_logger.error(f"Return policy fetch failed: {e}")
        policies["return"] = None

    # Fetch Fulfillment Policies
    url = f"{EBAY_DOMAIN}/sell/account/v1/fulfillment_policy?marketplace_id=EBAY_US"
    try:
        res = httpx.get(url, headers=headers, timeout=15.0).json()
        policies["fulfillment"] = res["fulfillmentPolicies"][0]["fulfillmentPolicyId"]
    except Exception as e:
        app_logger.error(f"Fulfillment policy fetch failed: {e}")
        policies["fulfillment"] = None

    # Fetch Payment Policies
    url = f"{EBAY_DOMAIN}/sell/account/v1/payment_policy?marketplace_id=EBAY_US"
    try:
        res = httpx.get(url, headers=headers, timeout=15.0).json()
        policies["payment"] = res["paymentPolicies"][0]["paymentPolicyId"]
    except Exception as e:
        app_logger.error(f"Payment policy fetch failed: {e}")
        policies["payment"] = None

    app_logger.info(f"Fetched Policy IDs: {policies}")
    return policies


def get_first_location_key() -> str:
    """Finds the first available merchant location key in the account."""
    try:
        res = httpx.get(
            f"{EBAY_DOMAIN}/sell/inventory/v1/location",
            headers=get_headers(),
            timeout=15.0,
        ).json()
        locations = res.get("locations", [])
        if locations:
            key = locations[0].get("merchantLocationKey", "DEFAULT")
            app_logger.info(f"Using existing location key: {key}")
            return key
    except Exception as e:
        app_logger.error(f"Location fetch error: {e}")
    return "DEFAULT"


def create_inventory_item(sku: str, manifest: dict) -> bool:
    """Step 1: Create the raw product data."""
    # quote() safely encodes SKUs that contain spaces (e.g. "CAP3340 RR29854")
    url = f"{EBAY_DOMAIN}/sell/inventory/v1/inventory_item/{quote(sku)}"
    headers = get_headers()
    headers["Content-Language"] = "en-US"
    headers["Accept-Language"] = "en-US"

    condition_enum = CONDITION_MAP.get(manifest.get("condition", ""), "USED")

    payload = {
        "product": {
            "title": manifest.get("title"),
            "description": manifest.get("description"),
            "aspects": {
                "Brand": [manifest.get("brand", "Unbranded")],
                "Size Type": ["Regular"],
                "Size": [manifest.get("size", "M")],
                "Color": [manifest.get("color", "Black")],
                "Department": [manifest.get("department", "Men")],
            },
            "condition": condition_enum,
            "conditionDescription": manifest.get("condition_notes", ""),
        },
        "condition": condition_enum,
        "availability": {"shipToLocationAvailability": {"quantity": 1}},
    }

    try:
        response = httpx.put(url, headers=headers, json=payload, timeout=15.0)
        if response.status_code in [200, 201, 204]:
            app_logger.info(f"Inventory Item {sku} created successfully.")
            return True
        else:
            app_logger.error(f"Failed to create inventory item: {response.text}")
            return False
    except Exception as e:
        app_logger.error(f"Error creating inventory item: {e}")
        return False


def create_offer(
    sku: str, manifest: dict, policies: dict, location_key: str
) -> str | None:
    """Step 2: Create the Offer (The Draft)."""
    url = f"{EBAY_DOMAIN}/sell/inventory/v1/offer"
    headers = get_headers()
    headers["Content-Language"] = "en-US"
    headers["Accept-Language"] = "en-US"

    payload = {
        "sku": sku,
        "marketplaceId": "EBAY_US",
        "format": "FIXED_PRICE",
        "availableQuantity": 1,
        "pricingSummary": {
            "price": {
                "value": "29.99",  # Default placeholder price
                "currency": "USD",
            }
        },
        "categoryId": "1539",  # Men's Shirts category
        "merchantLocationKey": location_key,
        "returnPolicyId": policies.get("return"),
        "fulfillmentPolicyId": policies.get("fulfillment"),
        "paymentPolicyId": policies.get("payment"),
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=15.0)
        if response.status_code in [200, 201]:
            data = response.json()
            offer_id = data.get("offerId")
            app_logger.info(f"Offer created successfully! Offer ID: {offer_id}")
            return offer_id
        else:
            app_logger.error(f"Failed to create offer: {response.text}")
            return None
    except Exception as e:
        app_logger.error(f"Error creating offer: {e}")
        return None


def publish_to_ebay(manifest_path: Path):
    """Main entry point to push a manifest to eBay."""
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    sku = manifest.get("sku")
    app_logger.info(f"Starting eBay publish for {sku}...")

    # 1. Get Policies
    policies = get_default_policy_ids()
    if not all(policies.values()):
        app_logger.error(
            "Could not fetch all required policy IDs. "
            "Run scripts/setup_ebay_sandbox.py first."
        )
        return

    # 2. Create Inventory Item
    if not create_inventory_item(sku, manifest):
        return

    # 3. Create Offer (This leaves it as a Draft/Unpublished Offer)
    location_key = get_first_location_key()
    offer_id = create_offer(sku, manifest, policies, location_key)

    if offer_id:
        app_logger.info(
            f"SUCCESS! {sku} is now in your eBay Sandbox Drafts folder as Offer ID: {offer_id}"
        )
