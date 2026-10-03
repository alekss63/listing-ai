import json

from fastapi.testclient import TestClient

from backend.app.api import routes
from backend.app.main import app


def test_update_merges_into_manifest_instead_of_replacing_it(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "PRODUCTS", tmp_path)
    manifest_path = tmp_path / "05277" / "manifest.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(json.dumps({"sku": "05277", "brand": "Cremieux"}))

    # The Swagger UI's default example body must not wipe the product data
    response = TestClient(app).post(
        "/api/products/05277", json={"title": "New title", "additionalProp1": {}}
    )

    assert response.status_code == 200
    saved = json.loads(manifest_path.read_text())
    assert saved["brand"] == "Cremieux"
    assert saved["title"] == "New title"
