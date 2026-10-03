import csv
import io

from backend.app.schemas import ItemSpecifics, ListingDraft
from backend.app.services.ebay import seller_hub


def make_draft(**overrides) -> ListingDraft:
    fields = {
        "sku": "05277",
        "title": "Cremieux Men's L Paisley Shirt",
        "description": "<p>Line one,\nwith a comma</p>",
        "suggested_price": 35,
        "condition": "New without tags",
        "item_specifics": ItemSpecifics(brand="Cremieux", size="L"),
        "ai_notes": "",
    }
    fields.update(overrides)
    return ListingDraft(**fields)


def parse(csv_bytes: bytes) -> list[dict]:
    assert not csv_bytes.startswith(b"\xef\xbb\xbf"), "BOM hides the Action header"
    text = csv_bytes.decode("utf-8")
    # Seller Hub rejects the file unless it opens with the template's #INFO line
    assert text.startswith(
        "#INFO,Version=0.0.2,Template= eBay-draft-listings-template_US,"
    )
    lines = text.splitlines(keepends=True)
    info_count = len(seller_hub.TEMPLATE_INFO_LINES)
    assert all(line.startswith(("#INFO", '"#INFO')) for line in lines[:info_count])
    return list(csv.DictReader(io.StringIO("".join(lines[info_count:]))))


def test_drafts_file_matches_seller_hub_create_drafts_template():
    photos = [f"https://i.ebayimg.com/{i}.jpg" for i in range(15)]
    rows = [
        seller_hub.draft_row(
            "05277", make_draft(), "57990", photos, {"Department": "Men"}
        ),
        seller_hub.draft_row(
            "06522",
            make_draft(sku="06522", condition="New with tags"),
            "15687",
            photos[:2],
            {"Neckline": "Crew"},
        ),
    ]
    first, second = parse(seller_hub.build_drafts_csv(rows))

    assert first[seller_hub.ACTION_HEADER] == "Draft"
    assert first["Custom label (SKU)"] == "05277"
    assert first["Category ID"] == "57990"
    assert first["Price"] == "35.00"
    assert first["Condition ID"] == "1500"  # New without tags
    assert second["Condition ID"] == "1000"  # New with tags
    assert first["Format"] == "FixedPrice"
    # Pipe-separated, capped at the drafts template's 12-photo limit
    assert len(first["Item photo URL"].split("|")) == seller_hub.MAX_DRAFT_PHOTOS
    # Commas survive CSV quoting; newlines are flattened
    assert first["Description"] == "<p>Line one, with a comma</p>"
    # Item specifics become C: columns, union across rows, blank where unused
    assert first["C:Brand"] == "Cremieux"
    assert first["C:Department"] == "Men"
    assert first["C:Neckline"] == ""
    assert second["C:Neckline"] == "Crew"
