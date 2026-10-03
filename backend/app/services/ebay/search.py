# backend/app/services/ebay/search.py
from urllib.parse import urlencode

import httpx

from backend.app.core.logging import app_logger
from backend.app.schemas import Product, ProductSearchResponse
from backend.app.services.ebay.client import EBAY_DOMAIN, get_headers

# eBay Browse API endpoint for item summary search
SEARCH_ENDPOINT = f"{EBAY_DOMAIN}/buy/browse/v1/item_summary/search"


async def search_ebay(
    query: str,
    category: str | None = None,
    max_price: float | None = None,
    min_price: float | None = None,
    sort: str | None = None,
    page: int = 1,
    limit: int = 10,
) -> ProductSearchResponse:
    """Searches eBay and returns a formatted ProductSearchResponse."""

    # Build query parameters for eBay Browse API
    params = {
        "q": query,
        "limit": limit,
        "offset": (page - 1) * limit,
    }
    if category:
        params["category_ids"] = category
    if max_price or min_price:
        min_str = str(min_price) if min_price else ""
        max_str = str(max_price) if max_price else ""
        params["price"] = f"[{min_str}..{max_str}]"
    if sort:
        params["sort"] = sort

    # 1. Get your existing headers
    headers = get_headers()

    # 2. ADD REQUIRED EBAY HEADER
    headers["X-EBAY-C-MARKETPLACE-ID"] = "EBAY_US"

    # 3. REMOVE Content-Type (eBay rejects GET requests that have a Content-Type header but no body)
    headers.pop("Content-Type", None)

    try:
        # Using AsyncClient so it doesn't block the FastAPI event loop
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SEARCH_ENDPOINT}?{urlencode(params)}", headers=headers, timeout=15.0
            )

            # Print the exact error from eBay to your terminal if it fails
            if response.status_code != 200:
                app_logger.error(f"eBay API Error Details: {response.text}")
                response.raise_for_status()

            data = response.json()

    except httpx.HTTPStatusError as e:
        raise Exception(
            f"eBay API rejected the request (Status {e.response.status_code}). Check server logs."
        ) from e
    except Exception as e:
        app_logger.error(f"eBay Search Error: {e}")
        raise Exception("Failed to connect to eBay") from e

    # Map eBay response to our Pydantic models
    products = []
    for item in data.get("itemSummaries", []):
        products.append(
            Product(
                id=str(item.get("itemId", "")),
                title=item.get("title", "Unknown Title"),
                price=float(item.get("price", {}).get("value", 0.0)),
                currency=item.get("price", {}).get("currency", "USD"),
                url=item.get("itemWebUrl", ""),
                image_url=item.get("image", {}).get("imageUrl", None),
            )
        )

    return ProductSearchResponse(
        products=products,
        total_results=data.get("total", len(products)),
        page=page,
        limit=limit,
    )
