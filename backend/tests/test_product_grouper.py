from datetime import datetime
from pathlib import Path

from backend.app.services.discovery.image_scanner import ImageFile
from backend.app.services.discovery.product_grouper import group_by_product
from backend.app.services.discovery.sku_detector import SKUResult


def test_group_by_product():
    images = [
        ImageFile(
            path=Path("img1.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 0),
        ),
        ImageFile(
            path=Path("img2.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 1),
        ),
        ImageFile(
            path=Path("img3.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 2),
        ),
        ImageFile(
            path=Path("img4.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 3),
        ),
        ImageFile(
            path=Path("img5.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 4),
        ),
    ]

    sku_results = [
        SKUResult("04182", 1.0, "confirmed", "test"),
        SKUResult("00000", 0.0, "manual_review", "test"),
        SKUResult("00000", 0.0, "manual_review", "test"),
        SKUResult("04183", 1.0, "confirmed", "test"),
        SKUResult("00000", 0.0, "manual_review", "test"),
    ]

    products = group_by_product(images, sku_results)

    assert len(products) == 2

    assert products[0].sku == "04182"
    assert len(products[0].images) == 3

    assert products[1].sku == "04183"
    assert len(products[1].images) == 2


def test_images_before_first_sku_are_not_assigned():
    images = [
        ImageFile(
            path=Path("unknown.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 0),
        ),
        ImageFile(
            path=Path("sku.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 1),
        ),
        ImageFile(
            path=Path("photo.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 2),
        ),
    ]

    sku_results = [
        SKUResult("00000", 0.0, "manual_review", "test"),
        SKUResult("04182", 1.0, "confirmed", "test"),
        SKUResult("00000", 0.0, "manual_review", "test"),
    ]

    products = group_by_product(images, sku_results)

    assert len(products) == 1
    assert products[0].sku == "04182"
    assert len(products[0].images) == 2
    assert products[0].images[0].name == "sku.jpg"
    assert products[0].images[1].name == "photo.jpg"


def test_duplicate_sku_creates_separate_batches():
    images = [
        ImageFile(
            path=Path("img1.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 0),
        ),
        ImageFile(
            path=Path("img2.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 1),
        ),
        ImageFile(
            path=Path("img3.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 2),
        ),
    ]

    sku_results = [
        SKUResult("04182", 1.0, "confirmed", "test"),
        SKUResult("00000", 0.0, "manual_review", "test"),
        SKUResult("04182", 1.0, "confirmed", "test"),
    ]

    products = group_by_product(images, sku_results)

    assert len(products) == 2

    assert products[0].sku == "04182"
    assert len(products[0].images) == 2

    assert products[1].sku == "04182"
    assert len(products[1].images) == 1


def test_mismatched_images_and_sku_results_raise_error():
    images = [
        ImageFile(
            path=Path("img1.jpg"),
            created=datetime(2026, 1, 1, 10, 0, 0),
        ),
    ]

    sku_results = []

    try:
        group_by_product(images, sku_results)
    except ValueError as exc:
        assert "same number" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
