# backend/app/api/drafts.py
"""
The draft review workflow (the dashboard's stand-in for Seller Hub Drafts,
which never shows offers created through the Inventory API):

    generate -> review/edit -> push (unpublished offer + photos) -> publish (live)

Local drafts live in /drafts as {sku}_draft.json until pushed, then are renamed
{sku}_draft_PUSHED.json. Editing a pushed draft writes a new {sku}_draft.json,
so "has unpushed changes" is simply "both files exist". eBay-side state (offer
ID, listing ID, uploaded photo URLs) is kept in the product manifest under "ebay".
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.app.core.paths import DRAFTS, PRODUCTS
from backend.app.schemas import ListingDraft
from backend.app.services.ai.listing_generator import generate_listing_draft
from backend.app.services.ebay.client import EBAY_DOMAIN
from backend.app.services.ebay.draft_pusher import (
    publish_offer,
    push_draft_to_ebay,
    suggest_category_id,
)
from backend.app.services.ebay.media import (
    ensure_listing_images,
    listing_photo_filenames,
)
from backend.app.services.ebay.seller_hub import build_drafts_csv, draft_row

router = APIRouter(prefix="/api/drafts", tags=["drafts"])

DRAFTS_DIR = DRAFTS
EBAY_TITLE_LIMIT = 80
LISTING_URL_BASE = (
    "https://sandbox.ebay.com/itm"
    if "sandbox" in EBAY_DOMAIN
    else "https://www.ebay.com/itm"
)


def _product_dir(sku: str) -> Path:
    # Reject path tricks like "../x" - the SKU is used as a directory name
    if sku in ("", ".", "..") or Path(sku).name != sku:
        raise HTTPException(status_code=400, detail=f"Invalid SKU: {sku!r}")
    return PRODUCTS / sku


def _load_manifest(sku: str) -> dict:
    manifest_path = _product_dir(sku) / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Product manifest not found for SKU: {sku}"
        )
    with open(manifest_path, encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(sku: str, manifest: dict) -> None:
    with open(_product_dir(sku) / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)


def _draft_path(sku: str) -> Path:
    return DRAFTS_DIR / f"{_product_dir(sku).name}_draft.json"


def _pushed_path(sku: str) -> Path:
    return DRAFTS_DIR / f"{_product_dir(sku).name}_draft_PUSHED.json"


def _current_draft_path(sku: str) -> Path | None:
    """The newest version of the draft: unpushed edits win over the pushed copy."""
    for path in (_draft_path(sku), _pushed_path(sku)):
        if path.exists():
            return path
    return None


def _write_draft(sku: str, draft: ListingDraft) -> None:
    with open(_draft_path(sku), "w", encoding="utf-8") as f:
        json.dump(draft.model_dump(), f, indent=4, ensure_ascii=False)


def _draft_state(sku: str, manifest: dict) -> dict:
    ebay = manifest.get("ebay") or {}
    has_local = _draft_path(sku).exists()
    # Listings made outside the dashboard (e.g. from Seller Hub drafts) have no
    # listing_id here, only the manifest status
    if ebay.get("listing_id") or manifest.get("status") == "listed":
        status = "listed"
    elif ebay.get("offer_id"):
        status = "on_ebay"
    elif has_local:
        status = "draft"
    else:
        status = "no_draft"
    return {
        "status": status,
        # Edits saved locally that eBay doesn't have yet
        "has_unpushed_changes": has_local and bool(ebay.get("offer_id")),
        "offer_id": ebay.get("offer_id"),
        "listing_id": ebay.get("listing_id"),
        "listing_url": ebay.get("listing_url"),
        "pushed_at": ebay.get("pushed_at"),
        "published_at": ebay.get("published_at"),
        "seller_hub_exported_at": ebay.get("seller_hub_exported_at"),
        "listed_via": ebay.get("listed_via"),
    }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@router.get("")
def list_drafts():
    """Every product with its draft/eBay status, for the dashboard's Drafts view."""
    items = []
    for product_dir in sorted(PRODUCTS.iterdir()) if PRODUCTS.exists() else []:
        manifest_file = product_dir / "manifest.json"
        if not product_dir.is_dir() or not manifest_file.exists():
            continue
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        sku = product_dir.name
        draft_path = _current_draft_path(sku)
        draft = json.loads(draft_path.read_text(encoding="utf-8")) if draft_path else {}
        photos = listing_photo_filenames(manifest)
        items.append(
            {
                "sku": sku,
                "title": draft.get("title") or manifest.get("title"),
                "price": draft.get("suggested_price"),
                "condition": draft.get("condition") or manifest.get("condition"),
                "thumbnail": photos[0] if photos else None,
                **_draft_state(sku, manifest),
            }
        )
    return items


@router.get("/seller-hub.csv")
async def seller_hub_drafts_file(skus: list[str] | None = Query(None)):  # noqa: B008
    """
    A "Create drafts" file for Seller Hub > Reports > Uploads. Uploading it
    there puts each product in https://www.ebay.com/sh/lst/drafts.
    Defaults to every product that has a draft; pass ?skus=A&skus=B to pick.
    """
    if not skus:
        skus = [
            d.name
            for d in sorted(PRODUCTS.iterdir())
            if (d / "manifest.json").exists() and _current_draft_path(d.name)
        ]
    if not skus:
        raise HTTPException(status_code=404, detail="No drafts to export yet.")

    rows = []
    for sku in skus:
        manifest = _load_manifest(sku)
        draft_path = _current_draft_path(sku)
        if not draft_path:
            raise HTTPException(status_code=404, detail=f"No draft for SKU {sku}")
        draft = ListingDraft(**json.loads(draft_path.read_text(encoding="utf-8")))
        ebay = manifest.setdefault("ebay", {})

        try:
            # Seller Hub needs web-hosted photos; reuse the EPS uploads from pushes
            image_urls, ebay["images"] = await ensure_listing_images(
                _product_dir(sku) / "images",
                listing_photo_filenames(manifest),
                ebay.get("images", {}),
            )
            # Category ID is mandatory for Seller Hub drafts
            if not ebay.get("category_id"):
                ebay["category_id"] = await suggest_category_id(draft.title)
            rows.append(
                draft_row(
                    sku,
                    draft,
                    ebay.get("category_id"),
                    image_urls,
                    manifest.get("item_specifics"),
                )
            )
            ebay["seller_hub_exported_at"] = _now()
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"{sku}: {e}") from e
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"{sku}: {e}") from e
        finally:
            # Keep photo uploads even if this product failed, to avoid re-uploading
            _save_manifest(sku, manifest)

    filename = (
        f"listingai-seller-hub-drafts-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
    )
    return Response(
        build_drafts_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{sku}")
def get_draft(sku: str):
    """The current draft, its listing photos, and its eBay status."""
    manifest = _load_manifest(sku)
    draft_path = _current_draft_path(sku)
    return {
        "sku": sku,
        "draft": (
            json.loads(draft_path.read_text(encoding="utf-8")) if draft_path else None
        ),
        "photos": listing_photo_filenames(manifest),
        **_draft_state(sku, manifest),
    }


@router.put("/{sku}")
def save_draft(sku: str, draft: ListingDraft):
    """Saves reviewed edits. If the draft was already pushed, push again to sync."""
    _load_manifest(sku)  # 404s for unknown SKUs
    if len(draft.title) > EBAY_TITLE_LIMIT:
        raise HTTPException(
            status_code=422,
            detail=f"Title is {len(draft.title)} characters; eBay allows {EBAY_TITLE_LIMIT}.",
        )
    _write_draft(sku, draft.model_copy(update={"sku": sku}))
    return {"status": "success", "message": f"Draft saved for {sku}"}


@router.post("/generate/{sku}")
async def generate_and_save_draft(sku: str):
    """
    Triggers local AI to generate a listing draft for a specific SKU,
    and saves it to the /drafts folder for manual approval.
    """
    manifest = _load_manifest(sku)
    # Photo lists and eBay bookkeeping are noise to the model
    product_data = {
        k: v for k, v in manifest.items() if k not in ("photos", "raw_images", "ebay")
    }

    try:
        draft = await generate_listing_draft(sku, product_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    _write_draft(sku, draft)
    manifest["created_draft"] = True
    _save_manifest(sku, manifest)

    return {
        "status": "success",
        "message": f"Draft generated and saved for {sku}",
        "draft_path": str(_draft_path(sku)),
        "draft": draft.model_dump(),
    }


@router.post("/push-to-ebay/{sku}")
async def push_approved_draft_to_ebay(sku: str):
    """
    Uploads the listing photos to eBay and pushes the draft as an UNPUBLISHED
    offer. Nothing is visible to buyers until /publish is called.
    """
    manifest = _load_manifest(sku)
    draft_file_path = _current_draft_path(sku)
    if not draft_file_path:
        raise HTTPException(status_code=404, detail=f"No draft found for SKU: {sku}")

    if (manifest.get("ebay") or {}).get("listed_via"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Listed via {manifest['ebay']['listed_via']} - revise it there. "
                "Pushing would create a second, separate eBay offer."
            ),
        )

    draft = ListingDraft(**json.loads(draft_file_path.read_text(encoding="utf-8")))
    ebay = manifest.setdefault("ebay", {})

    try:
        image_urls, ebay["images"] = await ensure_listing_images(
            _product_dir(sku) / "images",
            listing_photo_filenames(manifest),
            ebay.get("images", {}),
        )
        # Persist uploads now so a failed push doesn't re-upload them next time
        _save_manifest(sku, manifest)

        result = await push_draft_to_ebay(
            sku,
            draft,
            image_urls=image_urls,
            base_aspects=manifest.get("item_specifics"),
        )
    except ValueError as e:
        # Bad draft data (e.g. an unrecognized condition) - fix the draft and retry
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    ebay.update(
        {
            "offer_id": result["ebay_offer_id"],
            "offer_status": result["ebay_listing_status"],
            "category_id": result["ebay_category_id"],
            "pushed_at": _now(),
        }
    )
    manifest["uploaded_to_ebay"] = True
    _save_manifest(sku, manifest)

    # Mark the local file as "pushed" by renaming it (replacing any older push)
    draft_file_path.replace(_pushed_path(sku))

    return {**result, "ebay_image_count": len(image_urls)}


@router.post("/publish/{sku}")
async def publish_draft(sku: str):
    """Publishes the pushed offer as a LIVE eBay listing."""
    manifest = _load_manifest(sku)
    ebay = manifest.get("ebay") or {}
    state = _draft_state(sku, manifest)

    if not ebay.get("offer_id"):
        raise HTTPException(
            status_code=409, detail="Push this draft to eBay before publishing."
        )
    if state["has_unpushed_changes"]:
        raise HTTPException(
            status_code=409,
            detail="This draft has edits eBay doesn't have yet. Push again first.",
        )
    if ebay.get("listing_id"):
        raise HTTPException(
            status_code=409,
            detail=f"Already listed: {ebay.get('listing_url')}. Push to revise it.",
        )
    if state["status"] == "listed":
        # Listed some other way (Seller Hub) - publishing would duplicate it
        raise HTTPException(
            status_code=409,
            detail="Already listed on eBay outside the dashboard. Publishing would create a duplicate.",
        )

    try:
        result = await publish_offer(ebay["offer_id"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    ebay.update(
        {
            "listing_id": result["listing_id"],
            "listing_url": f"{LISTING_URL_BASE}/{result['listing_id']}",
            "offer_status": "PUBLISHED",
            "published_at": _now(),
        }
    )
    manifest["ebay"] = ebay
    manifest["status"] = "listed"
    _save_manifest(sku, manifest)

    return {
        "status": "success",
        "message": f"{sku} is live on eBay",
        "listing_id": result["listing_id"],
        "listing_url": ebay["listing_url"],
        "warnings": result["warnings"],
    }
