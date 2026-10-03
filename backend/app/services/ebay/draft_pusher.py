# backend/app/services/ebay/draft_pusher.py
import logging
from urllib.parse import quote

import httpx

from backend.app.schemas import ListingDraft
from backend.app.services.ebay.client import EBAY_DOMAIN, get_headers

logger = logging.getLogger(__name__)

# ⚠️ REPLACE THESE WITH YOUR ACTUAL EBAY POLICY IDs
# Find these in eBay Seller Hub > Account > Business Policies
FULFILLMENT_POLICY_ID = "112630510016"
PAYMENT_POLICY_ID = "112487574016"
RETURN_POLICY_ID = "219198931016"

# eBay Inventory API condition enums, keyed by the start of our condition text.
# Checked in order, so the more specific "new ..." phrases come before plain "new".
CONDITION_PREFIXES = [
    ("new with tags", "NEW"),
    ("new without tags", "NEW_OTHER"),
    ("new with imperfections", "NEW_WITH_DEFECTS"),
    ("new with defects", "NEW_WITH_DEFECTS"),
    ("new other", "NEW_OTHER"),
    ("new", "NEW"),
    ("pre-owned", "USED_EXCELLENT"),
    ("used", "USED_EXCELLENT"),
]
CONDITION_ENUMS = {"NEW", "NEW_OTHER", "NEW_WITH_DEFECTS", "USED_EXCELLENT"}

# Our ItemSpecifics field names -> eBay aspect names
ASPECT_NAMES = {
    "brand": "Brand",
    "size": "Size",
    "color": "Color",
    "material": "Material",
}


def to_ebay_condition(condition: str) -> str:
    """Maps a human condition ("New without tags, Store Display") to an eBay enum."""
    if condition.strip().upper() in CONDITION_ENUMS:
        return condition.strip().upper()
    normalized = condition.strip().lower()
    for prefix, enum in CONDITION_PREFIXES:
        if normalized.startswith(prefix):
            return enum
    raise ValueError(
        f"Unrecognized condition '{condition}'. Use e.g. 'New with tags', "
        "'New without tags', 'New with imperfections' or 'Pre-owned'."
    )


def build_aspects(
    draft: ListingDraft, base_aspects: dict | None = None
) -> dict[str, list[str]]:
    """
    eBay aspects from the draft, layered over base_aspects (the manifest's
    item_specifics, which carry required ones like Department and Size Type).
    """
    aspects = {
        name: [str(value)]
        for name, value in (base_aspects or {}).items()
        # Condition is a top-level inventory field, not an aspect
        if value and name != "Condition"
    }
    specifics = draft.item_specifics
    aspects.update(
        {
            ebay_name: [str(getattr(specifics, field))]
            for field, ebay_name in ASPECT_NAMES.items()
            if getattr(specifics, field)
        }
    )
    aspects.update({k: [str(v)] for k, v in specifics.custom.items() if v})
    return aspects


async def _get_location_key(client: httpx.AsyncClient, headers: dict) -> str | None:
    """Returns the first merchant location key on the account, if any."""
    response = await client.get(
        f"{EBAY_DOMAIN}/sell/inventory/v1/location", headers=headers, timeout=15.0
    )
    if response.status_code != 200:
        logger.warning(f"Location lookup failed ({response.status_code})")
        return None
    # eBay returns these under "locations" (not "merchantLocations")
    enabled = [
        loc["merchantLocationKey"]
        for loc in response.json().get("locations", [])
        if loc.get("merchantLocationStatus") == "ENABLED"
    ]
    return enabled[0] if enabled else None


async def _suggest_category_id(
    client: httpx.AsyncClient, headers: dict, title: str
) -> str | None:
    """Asks eBay's Taxonomy API for the best-matching EBAY_US category for a title."""
    response = await client.get(
        f"{EBAY_DOMAIN}/commerce/taxonomy/v1/category_tree/0/get_category_suggestions",
        headers=headers,
        params={"q": title},
        timeout=15.0,
    )
    if response.status_code != 200:
        logger.warning(f"Category suggestion failed ({response.status_code})")
        return None
    suggestions = response.json().get("categorySuggestions", [])
    return suggestions[0]["category"]["categoryId"] if suggestions else None


async def suggest_category_id(title: str) -> str | None:
    """Best-matching EBAY_US category for a title (standalone, own HTTP client)."""
    async with httpx.AsyncClient() as client:
        return await _suggest_category_id(client, _sell_headers(), title)


def _sell_headers() -> dict:
    headers = get_headers()
    # CRITICAL: eBay Sell API requires Content-Language
    headers["Content-Language"] = "en-US"
    headers["Content-Type"] = "application/json"
    headers["X-EBAY-C-MARKETPLACE-ID"] = "EBAY_US"
    return headers


async def push_draft_to_ebay(
    sku: str,
    draft: ListingDraft,
    image_urls: list[str] | None = None,
    base_aspects: dict | None = None,
) -> dict:
    """
    Creates/updates the inventory item and an UNPUBLISHED offer. Nothing is
    visible to buyers until publish_offer() is called.
    """
    headers = _sell_headers()

    # quote() safely encodes SKUs that contain spaces (e.g. "CAP3340 RR29854")
    inventory_url = f"{EBAY_DOMAIN}/sell/inventory/v1/inventory_item/{quote(sku)}"

    inventory_payload = {
        "product": {
            "title": draft.title,
            "description": draft.description,
            "aspects": build_aspects(draft, base_aspects),
            # EPS URLs from media.ensure_listing_images; first one is the main photo
            "imageUrls": image_urls or [],
        },
        "condition": to_ebay_condition(draft.condition),
        "availability": {"shipToLocationAvailability": {"quantity": 1}},
    }

    try:
        async with httpx.AsyncClient() as client:
            # 1. Create/Update Inventory Item
            logger.info(f"Pushing inventory item to: {inventory_url}")
            inv_response = await client.put(
                inventory_url, headers=headers, json=inventory_payload, timeout=15.0
            )

            if inv_response.status_code not in [200, 204]:
                logger.error(
                    f"❌ eBay Inventory Item Error ({inv_response.status_code}): {inv_response.text}"
                )
                raise Exception(
                    f"Failed to create eBay Inventory Item: {inv_response.text}"
                )

            # 2. Create the Offer, or update it if this SKU was pushed before
            offer_url = f"{EBAY_DOMAIN}/sell/inventory/v1/offer"

            offer_payload = {
                "availableQuantity": 1,
                "pricingSummary": {
                    "price": {"value": str(draft.suggested_price), "currency": "USD"}
                },
                "listingPolicies": {
                    "fulfillmentPolicyId": FULFILLMENT_POLICY_ID,
                    "paymentPolicyId": PAYMENT_POLICY_ID,
                    "returnPolicyId": RETURN_POLICY_ID,
                },
            }
            # Both are optional for an unpublished offer but required to publish it
            location_key = await _get_location_key(client, headers)
            if location_key:
                offer_payload["merchantLocationKey"] = location_key
            category_id = await _suggest_category_id(client, headers, draft.title)
            if category_id:
                offer_payload["categoryId"] = category_id

            existing_response = await client.get(
                offer_url, headers=headers, params={"sku": sku}, timeout=15.0
            )
            existing_offers = (
                existing_response.json().get("offers", [])
                if existing_response.status_code == 200
                else []
            )

            if existing_offers:
                offer_id = existing_offers[0]["offerId"]
                logger.info(f"Updating existing offer {offer_id} for {sku}")
                offer_response = await client.put(
                    f"{offer_url}/{offer_id}",
                    headers=headers,
                    json=offer_payload,
                    timeout=15.0,
                )
            else:
                offer_payload.update(
                    {"sku": sku, "marketplaceId": "EBAY_US", "format": "FIXED_PRICE"}
                )
                logger.info(f"Pushing offer to: {offer_url}")
                offer_response = await client.post(
                    offer_url, headers=headers, json=offer_payload, timeout=15.0
                )

            if offer_response.status_code not in [200, 201, 202, 204]:
                logger.error(
                    f"❌ eBay Offer Error ({offer_response.status_code}): {offer_response.text}"
                )
                raise Exception(f"Failed to create eBay Offer: {offer_response.text}")

            # updateOffer returns 204 with no body
            offer_data = offer_response.json() if offer_response.content else {}
            if existing_offers:
                offer_data.setdefault("offerId", existing_offers[0]["offerId"])
                offer_data.setdefault("status", existing_offers[0].get("status"))

            return {
                "status": "success",
                "message": f"Draft successfully pushed to eBay for SKU {sku}",
                "ebay_inventory_href": inv_response.headers.get("Location", "N/A"),
                "ebay_offer_id": offer_data.get("offerId"),
                "ebay_listing_status": offer_data.get("status"),
                "ebay_category_id": category_id,
                "ebay_location_key": location_key,
            }

    except Exception as e:
        logger.error(f"Push to eBay failed for {sku}: {e}")
        raise


async def publish_offer(offer_id: str) -> dict:
    """
    Publishes an offer, turning it into a LIVE eBay listing. eBay validates
    everything here (photos, category, required aspects, policies, location),
    so errors from this call list exactly what the listing is still missing.
    """
    url = f"{EBAY_DOMAIN}/sell/inventory/v1/offer/{offer_id}/publish"
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=_sell_headers(), timeout=30.0)
    if response.status_code != 200:
        logger.error(f"❌ eBay Publish Error ({response.status_code}): {response.text}")
        raise Exception(f"eBay rejected the publish: {response.text}")
    data = response.json()
    return {"listing_id": data["listingId"], "warnings": data.get("warnings", [])}
