import io
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps

from backend.app.core.paths import PRODUCTS
from backend.app.schemas import ProductSearchRequest, ProductSearchResponse
from backend.app.services.ebay.search import search_ebay

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

THUMBNAIL_SIZE = 400


def get_manifest_path(sku: str) -> Path:
    path = PRODUCTS / sku / "manifest.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Manifest not found")
    return path


@router.get("/products")
def list_products():
    """Returns a list of all processed products."""
    products = []
    if not PRODUCTS.exists():
        return products

    for product_dir in PRODUCTS.iterdir():
        if product_dir.is_dir():
            manifest_file = product_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file, encoding="utf-8") as f:
                        data = json.load(f)
                        products.append(
                            {
                                "sku": data.get("sku", product_dir.name),
                                "title": data.get("title", "No Title"),
                                "status": data.get("status", "discovered"),
                                "garment_type": data.get("garment_type"),
                                "condition": data.get("condition"),
                            }
                        )
                except json.JSONDecodeError:
                    # Skip corrupted or empty JSON files so the dashboard still loads
                    continue
    return products


@router.get("/products/search", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest = Depends()):
    """
    Search for products on eBay.
    Example: GET /api/products/search?query=vintage+jacket&max_price=100&limit=5

    NOTE: This route MUST be defined before /products/{sku} so FastAPI
    matches the static "search" path before trying to match it as a dynamic {sku}.
    """
    try:
        return await search_ebay(
            query=request.query,
            category=request.category,
            max_price=request.max_price,
            min_price=request.min_price,
            sort=request.sort,
            page=request.page,
            limit=request.limit,
        )
    except Exception as e:
        logger.error(f"eBay search failed for query='{request.query}': {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch products from eBay: {str(e)}",
        ) from e


@router.get("/products/{sku}")
def get_product(sku: str):
    """Returns the full manifest data for a specific product."""
    manifest_path = get_manifest_path(sku)
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


@router.get("/products/{sku}/images/{filename}")
def get_product_image(sku: str, filename: str, thumb: bool = False):
    """Serves a product photo; ?thumb=true returns a small JPEG for previews."""
    # Both parts become path segments, so reject anything that could escape them
    parts = (sku, filename)
    if any(p in ("", ".", "..") or Path(p).name != p for p in parts):
        raise HTTPException(status_code=400, detail="Invalid path")
    image_path = PRODUCTS / sku / "images" / filename
    if not image_path.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    if not thumb:
        return FileResponse(image_path)

    # Phone originals are ~9 MB; a grid of them would crawl
    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=80)
    return Response(
        buffer.getvalue(),
        media_type="image/jpeg",
        headers={"Cache-Control": "max-age=3600"},
    )


@router.post("/products/{sku}")
def update_product(sku: str, updated_data: dict = Body(...)):
    """Merges edited fields into the manifest.json file."""
    manifest_path = get_manifest_path(sku)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    # Merge rather than replace, so a partial or placeholder body (e.g. the
    # Swagger UI default {"additionalProp1": {}}) can't wipe the product data
    manifest.update(updated_data)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)
    return {"status": "success", "message": f"Successfully updated {sku}"}


# Add this to backend/app/api/routes.py (you can delete it later)


@router.get("/test-ebay-token")
async def test_ebay_token():
    """Tests if the current eBay token is valid by fetching account info."""
    import httpx

    from backend.app.services.ebay.client import EBAY_DOMAIN, get_headers

    headers = get_headers()
    headers.pop("Content-Type", None)  # Remove for GET request

    # Try a simple GET request to verify the token
    url = f"{EBAY_DOMAIN}/sell/account/v1/privilege"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10.0)

        return {
            "status_code": response.status_code,
            "token_valid": response.status_code == 200,
            "response": (
                response.json() if response.status_code == 200 else response.text
            ),
            "ebay_domain": EBAY_DOMAIN,
        }
