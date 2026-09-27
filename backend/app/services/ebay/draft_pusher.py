# backend/app/services/ebay/draft_pusher.py
import logging

import httpx

from backend.app.schemas import ListingDraft
from backend.app.services.ebay.client import EBAY_DOMAIN, get_headers

logger = logging.getLogger(__name__)

# ⚠️ REPLACE THESE WITH YOUR ACTUAL EBAY POLICY IDs
# Find these in eBay Seller Hub > Account > Business Policies
FULFILLMENT_POLICY_ID = "112630510016"
PAYMENT_POLICY_ID = "112487574016"
RETURN_POLICY_ID = "219198931016"


async def push_draft_to_ebay(sku: str, draft: ListingDraft) -> dict:
    headers = get_headers()

    # CRITICAL: eBay Sell API requires Content-Language
    headers["Content-Language"] = "en-US"
    headers["Content-Type"] = "application/json"
    headers["X-EBAY-C-MARKETPLACE-ID"] = "EBAY_US"

    inventory_url = f"{EBAY_DOMAIN}/sell/inventory/v1/inventory_item/{sku}"

    # Clean up condition string to match eBay's exact enum (e.g., "NEW_WITH_TAGS", "USED")
    clean_condition = draft.condition.upper().replace(" ", "_").replace("-", "_")

    inventory_payload = {
        "product": {
            "title": draft.title,
            "description": draft.description,
            "aspects": {
                k: [str(v)]
                for k, v in draft.item_specifics.model_dump().items()
                if v is not None and k != "custom"
            },
        },
        "condition": clean_condition,
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

            # 2. Create the Offer
            offer_url = f"{EBAY_DOMAIN}/sell/inventory/v1/offer"

            offer_payload = {
                "availableQuantity": 1,
                "format": "FIXED_PRICE",
                "marketplaceId": "EBAY_US",
                "price": {"value": str(draft.suggested_price), "currency": "USD"},
                "listingPolicies": {
                    "fulfillmentPolicyId": FULFILLMENT_POLICY_ID,
                    "paymentPolicyId": PAYMENT_POLICY_ID,
                    "returnPolicyId": RETURN_POLICY_ID,
                },
                "sku": sku,
                "status": "DRAFT",
            }

            logger.info(f"Pushing offer to: {offer_url}")
            offer_response = await client.post(
                offer_url, headers=headers, json=offer_payload, timeout=15.0
            )

            if offer_response.status_code not in [200, 201, 202]:
                logger.error(
                    f"❌ eBay Offer Error ({offer_response.status_code}): {offer_response.text}"
                )
                raise Exception(f"Failed to create eBay Offer: {offer_response.text}")

            offer_data = offer_response.json()

            return {
                "status": "success",
                "message": f"Draft successfully pushed to eBay for SKU {sku}",
                "ebay_inventory_href": inv_response.headers.get("Location", "N/A"),
                "ebay_offer_id": offer_data.get("offerId"),
                "ebay_listing_status": offer_data.get("status"),
            }

    except Exception as e:
        logger.error(f"Push to eBay failed for {sku}: {e}")
        raise Exception(str(e))
