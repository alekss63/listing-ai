# backend/app/services/ebay/media.py
"""
Uploads product photos to eBay Picture Services (EPS) via the Media API.

eBay listings can't reference local files - every picture must be hosted on
EPS first. The Media API returns an EPS URL per upload; those URLs go into the
inventory item's product.imageUrls. Unused EPS images expire, so uploads are
cached with their expiration date and only re-done once stale.
"""

import io
import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
from PIL import Image, ImageOps

from backend.app.services.ebay.client import EBAY_DOMAIN, get_headers

logger = logging.getLogger(__name__)

# The Media API lives on apim.* rather than api.* (same for sandbox)
MEDIA_DOMAIN = EBAY_DOMAIN.replace("://api.", "://apim.")
UPLOAD_URL = f"{MEDIA_DOMAIN}/commerce/media/v1_beta/image/create_image_from_file"

# eBay's recommended size for zoomable photos; phone originals (4284px, ~9 MB)
# are far larger than needed and slow to upload
MAX_DIMENSION = 1600
JPEG_QUALITY = 90
MAX_LISTING_PHOTOS = 24

# Listing photo order, by the classifier's photo role. The SKU sticker photo is
# internal and deliberately never listed.
PHOTO_ROLE_ORDER = [
    "front_photo",
    "back_photo",
    "detail_photos",
    "tag_photos",
    "measurement_photos",
    "defect_photos",
]


def listing_photo_filenames(manifest: dict) -> list[str]:
    """Picks which product photos go on the listing, in display order."""
    photos = manifest.get("photos") or {}
    ordered: list[str] = []
    for role in PHOTO_ROLE_ORDER:
        value = photos.get(role)
        for name in value if isinstance(value, list) else [value]:
            if name and name not in ordered:
                ordered.append(name)

    # Photos the classifier didn't assign a role go last (extra angles, etc.)
    excluded = set(ordered) | {photos.get("sku_photo")}
    ordered += [n for n in manifest.get("raw_images", []) if n not in excluded]
    return ordered[:MAX_LISTING_PHOTOS]


def prepare_image(path: Path) -> bytes:
    """Re-encodes a photo as an upright JPEG no larger than MAX_DIMENSION."""
    with Image.open(path) as img:
        # Phones store rotation in EXIF; bake it in so eBay shows it upright
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        return buffer.getvalue()


def _is_fresh(cached: dict | None) -> bool:
    if not cached or not cached.get("imageUrl"):
        return False
    expires = cached.get("expirationDate")
    if not expires:
        return True
    return datetime.fromisoformat(expires.replace("Z", "+00:00")) > datetime.now(UTC)


async def upload_image(client: httpx.AsyncClient, path: Path) -> dict:
    """Uploads one photo to EPS. Returns {"imageUrl", "expirationDate"}."""
    headers = get_headers()
    # httpx must set the multipart Content-Type itself (it includes the boundary)
    headers.pop("Content-Type", None)

    response = await client.post(
        UPLOAD_URL,
        headers=headers,
        files={"image": (f"{path.stem}.jpg", prepare_image(path), "image/jpeg")},
        timeout=60.0,
    )
    if response.status_code != 201:
        raise Exception(
            f"eBay photo upload failed for {path.name} "
            f"({response.status_code}): {response.text}"
        )

    data = response.json() if response.content else {}
    if not data.get("imageUrl"):
        # Fall back to getImage via the Location header
        location = response.headers["Location"]
        data = (await client.get(location, headers=headers, timeout=15.0)).json()
    return {"imageUrl": data["imageUrl"], "expirationDate": data.get("expirationDate")}


async def ensure_listing_images(
    images_dir: Path, filenames: list[str], cache: dict
) -> tuple[list[str], dict]:
    """
    Returns EPS URLs for the given photos, uploading only those not already
    cached (or whose cached upload has expired). Also returns the updated cache
    (filename -> {"imageUrl", "expirationDate"}) for the caller to persist.
    """
    cache = dict(cache)
    urls = []
    async with httpx.AsyncClient() as client:
        for name in filenames:
            path = images_dir / name
            if not path.exists():
                logger.warning(f"Listing photo missing on disk, skipping: {path}")
                continue
            if not _is_fresh(cache.get(name)):
                logger.info(f"Uploading {name} to eBay Picture Services")
                cache[name] = await upload_image(client, path)
            urls.append(cache[name]["imageUrl"])
    return urls, cache
