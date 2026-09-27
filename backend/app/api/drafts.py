# backend/app/api/drafts.py
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.schemas import ListingDraft
from backend.app.services.ai.listing_generator import generate_listing_draft
from backend.app.services.ebay.draft_pusher import push_draft_to_ebay

router = APIRouter(prefix="/api/drafts", tags=["drafts"])

# Point to the drafts folder at the root of your project
DRAFTS_DIR = Path(__file__).parent.parent.parent.parent / "drafts"
DRAFTS_DIR.mkdir(exist_ok=True)


@router.post("/generate/{sku}")
async def generate_and_save_draft(sku: str):
    """
    Triggers local AI to generate a listing draft for a specific SKU,
    and saves it to the /drafts folder for manual approval.
    """
    from backend.app.core.paths import PRODUCTS

    manifest_path = PRODUCTS / sku / "manifest.json"
    if not manifest_path.exists():
        raise HTTPException(
            status_code=404, detail=f"Product manifest not found for SKU: {sku}"
        )

    with open(manifest_path, encoding="utf-8") as f:
        product_data = json.load(f)

    try:
        draft = await generate_listing_draft(sku, product_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    draft_file_path = DRAFTS_DIR / f"{sku}_draft.json"
    with open(draft_file_path, "w", encoding="utf-8") as f:
        json.dump(draft.model_dump(), f, indent=4, ensure_ascii=False)

    return {
        "status": "success",
        "message": f"Draft generated and saved for {sku}",
        "draft_path": str(draft_file_path),
        "draft": draft.model_dump(),
    }


@router.post("/push-to-ebay/{sku}")
async def push_approved_draft_to_ebay(sku: str):
    """
    Reads an approved draft from the local /drafts folder and pushes it
    to eBay as a DRAFT listing for manual review in Seller Hub.
    """
    draft_file_path = DRAFTS_DIR / f"{sku}_draft.json"

    if not draft_file_path.exists():
        raise HTTPException(status_code=404, detail=f"No draft found for SKU: {sku}")

    with open(draft_file_path, encoding="utf-8") as f:
        draft_data = json.load(f)

    draft = ListingDraft(**draft_data)

    try:
        result = await push_draft_to_ebay(sku, draft)

        # Mark the local file as "pushed" by renaming it
        pushed_file_path = DRAFTS_DIR / f"{sku}_draft_PUSHED.json"
        draft_file_path.rename(pushed_file_path)

        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
