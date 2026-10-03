import asyncio
import json

import httpx
import pytest

from backend.app.schemas import ItemSpecifics, ListingDraft
from backend.app.services.ebay import draft_pusher


def make_draft(**overrides) -> ListingDraft:
    fields = {
        "sku": "CAP3340 RR29854",
        "title": "Cremieux Men's L Paisley Shirt",
        "description": "<p>Shirt</p>",
        "suggested_price": 25.0,
        "condition": "New without tags, Store Display",
        "item_specifics": ItemSpecifics(
            brand="Cremieux", size="L", custom={"Pattern": "Paisley"}
        ),
        "ai_notes": "",
    }
    fields.update(overrides)
    return ListingDraft(**fields)


@pytest.mark.parametrize(
    "condition, expected",
    [
        ("New with tags", "NEW"),
        ("New without tags, Store Display", "NEW_OTHER"),
        ("New with imperfections", "NEW_WITH_DEFECTS"),
        ("Pre-owned", "USED_EXCELLENT"),
        ("Used", "USED_EXCELLENT"),
        ("New", "NEW"),
        ("NEW_OTHER", "NEW_OTHER"),
    ],
)
def test_condition_maps_to_ebay_enum(condition, expected):
    assert draft_pusher.to_ebay_condition(condition) == expected


def test_unknown_condition_is_rejected_rather_than_guessed():
    with pytest.raises(ValueError):
        draft_pusher.to_ebay_condition("Mint")


def test_aspects_use_ebay_names_and_skip_empty_values():
    assert draft_pusher.build_aspects(make_draft()) == {
        "Brand": ["Cremieux"],
        "Size": ["L"],
        "Pattern": ["Paisley"],
    }


def fake_ebay(monkeypatch, existing_offer_id: str | None):
    """Routes the pusher's httpx calls to an in-memory eBay and records them."""
    monkeypatch.setattr(draft_pusher, "get_headers", lambda: {})
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else None
        # raw_path keeps the percent-encoding that url.path decodes away
        path = request.url.raw_path.decode().split("?")[0]
        calls.append((request.method, path, body))
        if path.endswith("/location"):
            return httpx.Response(
                200,
                json={
                    # Real response shape: "locations", and disabled ones skipped
                    "locations": [
                        {
                            "merchantLocationKey": "OLD",
                            "merchantLocationStatus": "DISABLED",
                        },
                        {
                            "merchantLocationKey": "HOME",
                            "merchantLocationStatus": "ENABLED",
                        },
                    ]
                },
            )
        if path.endswith("/get_category_suggestions"):
            return httpx.Response(
                200,
                json={"categorySuggestions": [{"category": {"categoryId": "57990"}}]},
            )
        if request.method == "GET" and path.endswith("/offer"):
            if existing_offer_id:
                offers = [{"offerId": existing_offer_id, "status": "UNPUBLISHED"}]
                return httpx.Response(200, json={"offers": offers})
            return httpx.Response(404, json={"errors": [{"errorId": 25713}]})
        if request.method == "POST":
            return httpx.Response(201, json={"offerId": "NEW1"})
        return httpx.Response(204)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        draft_pusher.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler)),
    )
    return calls


def test_first_push_creates_offer(monkeypatch):
    calls = fake_ebay(monkeypatch, existing_offer_id=None)
    result = asyncio.run(
        draft_pusher.push_draft_to_ebay("CAP3340 RR29854", make_draft())
    )

    method, path, inventory = calls[0]
    assert (method, path) == (
        "PUT",
        "/sell/inventory/v1/inventory_item/CAP3340%20RR29854",
    )
    assert inventory["condition"] == "NEW_OTHER"

    method, path, offer = calls[-1]
    assert (method, path) == ("POST", "/sell/inventory/v1/offer")
    assert offer["pricingSummary"]["price"]["value"] == "25.0"
    assert offer["merchantLocationKey"] == "HOME"
    assert offer["categoryId"] == "57990"
    assert offer["sku"] == "CAP3340 RR29854"
    assert result["ebay_offer_id"] == "NEW1"


def test_repush_updates_existing_offer(monkeypatch):
    calls = fake_ebay(monkeypatch, existing_offer_id="999")
    result = asyncio.run(draft_pusher.push_draft_to_ebay("05277", make_draft()))

    method, path, offer = calls[-1]
    assert (method, path) == ("PUT", "/sell/inventory/v1/offer/999")
    # updateOffer rejects create-only fields
    assert "sku" not in offer and "marketplaceId" not in offer
    assert result["ebay_offer_id"] == "999"
    assert result["ebay_listing_status"] == "UNPUBLISHED"
