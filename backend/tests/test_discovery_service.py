from datetime import datetime
import json
from pathlib import Path

from backend.app.services.discovery.image_scanner import ImageFile
from backend.app.services.discovery.service import discover_products
from backend.app.services.discovery.sku_detector import SKUResult


def test_discovery_builds_product_batches_without_writing():
    images = [
        ImageFile(Path("Pictures/sku.jpg"), datetime(2026, 1, 1, 10, 0, 0)),
        ImageFile(Path("Pictures/front.jpg"), datetime(2026, 1, 1, 10, 0, 1)),
    ]
    sku_results = [
        SKUResult("04182", 1.0, "confirmed", "test"),
        SKUResult("00000", 0.0, "manual_review", "test"),
    ]

    result = discover_products(images, sku_results, persist=False)

    assert result.scanned_images == 2
    assert len(result.products) == 1
    assert result.products[0].manifest.sku == "04182"
    assert result.products[0].manifest.raw_images == [image.path for image in images]
    assert result.manifests == []


def test_manifest_serialization_uses_relative_paths(tmp_path, monkeypatch):
    images = [ImageFile(Path("Pictures/sku.jpg"), datetime(2026, 1, 1, 10, 0, 0))]
    sku_results = [SKUResult("04182", 1.0, "confirmed", "test")]

    from backend.app.services.discovery import service

    monkeypatch.setattr(service, "PRODUCTS", tmp_path)
    monkeypatch.setattr(service, "ROOT", Path.cwd())
    result = discover_products(images, sku_results)

    manifest_data = json.loads(result.manifests[0].read_text(encoding="utf-8"))
    assert manifest_data["schema_version"] == 1
    assert manifest_data["sku"] == "04182"
    assert manifest_data["raw_images"] == ["Pictures/sku.jpg"]
