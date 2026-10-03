import json

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.app.api import drafts
from backend.app.main import app

DRAFT = {
    "sku": "05277",
    "title": "Cremieux Men's L Paisley Shirt",
    "description": "<p>Shirt</p>",
    "suggested_price": 35.0,
    "condition": "New without tags",
    "item_specifics": {
        "brand": "Cremieux",
        "size": "L",
        "color": None,
        "material": None,
        "custom": {},
    },
    "ai_notes": "",
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A product folder + drafts folder, with eBay replaced by recorders."""
    products, drafts_dir = tmp_path / "products", tmp_path / "drafts"
    (products / "05277" / "images").mkdir(parents=True)
    drafts_dir.mkdir()
    (products / "05277" / "manifest.json").write_text(
        json.dumps(
            {
                "sku": "05277",
                "photos": {"front_photo": "front.jpg", "sku_photo": "sticker.jpg"},
                "raw_images": ["sticker.jpg", "front.jpg"],
                "item_specifics": {"Department": "Men"},
            }
        )
    )
    (drafts_dir / "05277_draft.json").write_text(json.dumps(DRAFT))
    monkeypatch.setattr(drafts, "PRODUCTS", products)
    monkeypatch.setattr(drafts, "DRAFTS_DIR", drafts_dir)

    calls = {"push": [], "publish": []}

    async def fake_images(images_dir, filenames, cache):
        return [f"https://i.ebayimg.com/{n}" for n in filenames], {"front.jpg": {}}

    async def fake_push(sku, draft, image_urls=None, base_aspects=None):
        calls["push"].append(
            {"draft": draft, "image_urls": image_urls, "base_aspects": base_aspects}
        )
        return {
            "ebay_offer_id": "OFFER1",
            "ebay_listing_status": "UNPUBLISHED",
            "ebay_category_id": "57990",
        }

    async def fake_publish(offer_id):
        calls["publish"].append(offer_id)
        return {"listing_id": "LIST1", "warnings": []}

    monkeypatch.setattr(drafts, "ensure_listing_images", fake_images)
    monkeypatch.setattr(drafts, "push_draft_to_ebay", fake_push)
    monkeypatch.setattr(drafts, "publish_offer", fake_publish)

    manifest = lambda: json.loads(  # noqa: E731
        (products / "05277" / "manifest.json").read_text()
    )
    return TestClient(app), calls, manifest


def test_full_review_push_publish_flow(env):
    client, calls, manifest = env

    assert client.get("/api/drafts").json()[0]["status"] == "draft"

    # Publishing before pushing is refused
    assert client.post("/api/drafts/publish/05277").status_code == 409

    response = client.post("/api/drafts/push-to-ebay/05277")
    assert response.status_code == 200
    push = calls["push"][0]
    assert push["image_urls"] == ["https://i.ebayimg.com/front.jpg"]
    assert push["base_aspects"] == {"Department": "Men"}
    assert manifest()["ebay"]["offer_id"] == "OFFER1"
    assert client.get("/api/drafts/05277").json()["status"] == "on_ebay"

    # Editing after a push must be pushed again before publishing
    edited = {**DRAFT, "title": "Edited title"}
    assert client.put("/api/drafts/05277", json=edited).status_code == 200
    state = client.get("/api/drafts/05277").json()
    assert state["has_unpushed_changes"] is True
    assert state["draft"]["title"] == "Edited title"
    assert client.post("/api/drafts/publish/05277").status_code == 409

    client.post("/api/drafts/push-to-ebay/05277")
    assert calls["push"][1]["draft"].title == "Edited title"

    response = client.post("/api/drafts/publish/05277")
    assert response.status_code == 200
    assert calls["publish"] == ["OFFER1"]
    assert response.json()["listing_url"].endswith("/itm/LIST1")
    assert manifest()["status"] == "listed"
    assert client.get("/api/drafts/05277").json()["status"] == "listed"

    # A second publish of the same listing is refused
    assert client.post("/api/drafts/publish/05277").status_code == 409


def test_title_over_ebay_limit_is_rejected(env):
    client, _, _ = env
    response = client.put("/api/drafts/05277", json={**DRAFT, "title": "x" * 81})
    assert response.status_code == 422


@pytest.mark.parametrize("sku", ["..", "../etc", "a/b", ""])
def test_path_traversal_sku_is_rejected(sku):
    # Tested directly: HTTP clients normalize "/.." out of URLs before sending
    with pytest.raises(HTTPException) as exc:
        drafts._product_dir(sku)
    assert exc.value.status_code == 400


def test_seller_hub_listed_product_cannot_be_pushed_or_published(env):
    client, calls, manifest = env
    data = manifest()
    data["status"] = "listed"
    data["ebay"] = {"listed_via": "seller_hub"}
    (drafts.PRODUCTS / "05277" / "manifest.json").write_text(json.dumps(data))

    state = client.get("/api/drafts/05277").json()
    assert state["status"] == "listed"
    assert state["listed_via"] == "seller_hub"
    # Either would create a duplicate of the Seller Hub listing
    assert client.post("/api/drafts/push-to-ebay/05277").status_code == 409
    assert client.post("/api/drafts/publish/05277").status_code == 409
    assert calls == {"push": [], "publish": []}
