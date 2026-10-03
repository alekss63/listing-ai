# backend/app/services/ebay/seller_hub.py
"""
Creates real Seller Hub drafts (https://www.ebay.com/sh/lst/drafts).

Offers made with the Inventory API never appear in Seller Hub's Drafts folder.
Drafts uploaded as a "Create drafts" file in Seller Hub > Reports > Uploads do.
Each row with Action "Draft" becomes a draft you can finish and list there.

The file has to be uploaded through Seller Hub itself: the Sell Feed API
(FX_LISTING) accepts the same file but rejects the Draft action with
"BAF.Error.5 Unable to find Task Action Id for task Draft" (verified Oct 2026).
"""

import csv
import io

from backend.app.schemas import ListingDraft
from backend.app.services.ebay.draft_pusher import (
    build_aspects,
    to_ebay_condition,
)

# Seller Hub identifies the template from these #INFO lines (the first one in
# particular) - without them the upload fails with "We couldn't identify your
# template". Mirrors the opening of Seller Hub > Reports > Uploads > Get template
# > "Create drafts"; if eBay changes that template, update these to match.
TEMPLATE_INFO_LINES = [
    "#INFO,Version=0.0.2,Template= eBay-draft-listings-template_US",
    "#INFO Action and Category ID are required fields. 1) Set Action to Draft "
    "2) Please find the category ID for your listings here: "
    "https://pages.ebay.com/sellerinformation/news/categorychanges.html",
    "#INFO After you've successfully uploaded your draft from the Seller Hub "
    "Reports tab, complete the drafts to create live listings: "
    "https://www.ebay.com/sh/lst/drafts",
    "#INFO",
]

# The template's column header row
ACTION_HEADER = "Action(SiteID=US|Country=US|Currency=USD|Version=1193|CC=UTF-8)"
BASE_COLUMNS = [
    ACTION_HEADER,
    "Custom label (SKU)",
    "Category ID",
    "Title",
    "UPC",
    "Price",
    "Quantity",
    "Item photo URL",
    "Condition ID",
    "Description",
    "Format",
]
# The drafts template accepts at most 12 photos per row
MAX_DRAFT_PHOTOS = 12

# Inventory API condition enums -> Seller Hub numeric condition IDs (clothing)
CONDITION_IDS = {
    "NEW": "1000",
    "NEW_OTHER": "1500",
    "NEW_WITH_DEFECTS": "1750",
    "USED_EXCELLENT": "3000",
}


def draft_row(
    sku: str,
    draft: ListingDraft,
    category_id: str | None,
    image_urls: list[str],
    base_aspects: dict | None = None,
) -> dict:
    row = {
        ACTION_HEADER: "Draft",
        "Custom label (SKU)": sku,
        "Category ID": category_id or "",
        "Title": draft.title,
        "UPC": "",
        "Price": f"{draft.suggested_price:.2f}",
        "Quantity": "1",
        "Item photo URL": "|".join(image_urls[:MAX_DRAFT_PHOTOS]),
        "Condition ID": CONDITION_IDS[to_ebay_condition(draft.condition)],
        # Embedded newlines are legal in CSV but some eBay parsers choke on them
        "Description": " ".join(draft.description.splitlines()),
        "Format": "FixedPrice",
    }
    for name, values in build_aspects(draft, base_aspects).items():
        row[f"C:{name}"] = "|".join(values)
    return row


def build_drafts_csv(rows: list[dict]) -> bytes:
    """One CSV for all rows; item-specific columns are the union across rows."""
    aspect_columns = sorted({k for row in rows for k in row if k.startswith("C:")})
    fieldnames = BASE_COLUMNS + aspect_columns
    buffer = io.StringIO()
    # Each #INFO line is one cell, padded to the full width like eBay's template
    info_writer = csv.writer(buffer)
    for line in TEMPLATE_INFO_LINES:
        first, *rest = line.split(",") if line.startswith("#INFO,") else [line]
        cells = [first, *rest]
        info_writer.writerow(cells + [""] * (len(fieldnames) - len(cells)))
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, restval="")
    writer.writeheader()
    writer.writerows(rows)
    # No BOM: a leading BOM can hide the Action header's SiteID from eBay's parser
    return buffer.getvalue().encode("utf-8")
