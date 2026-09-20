import json
import shutil
from pathlib import Path

from backend.app.services.discovery.models import ProductManifest
from backend.app.core.logging import app_logger

try:
    from backend.app.core.paths import STORAGE_PRODUCTS, PROCESSED
except ImportError:
    from backend.app.core.paths import BASE_DIR
    STORAGE_PRODUCTS = BASE_DIR / "storage" / "products"
    PROCESSED = BASE_DIR / "Processed"


def save_manifest(manifest: ProductManifest) -> Path:
    """
    Saves the manifest to storage/products/{sku}/manifest.json,
    copies images to storage/products/{sku}/images/,
    and MOVES the originals from Pictures/ to Processed/{sku}/.
    """
    product_dir = STORAGE_PRODUCTS / manifest.sku
    product_dir.mkdir(parents=True, exist_ok=True)

    images_dir = product_dir / "images"
    images_dir.mkdir(exist_ok=True)

    processed_dir = PROCESSED / manifest.sku
    processed_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy to storage + MOVE originals to Processed archive
    for img_path in manifest.raw_images:
        if img_path.exists():
            shutil.copy2(img_path, images_dir / img_path.name)
            shutil.move(str(img_path), str(processed_dir / img_path.name))

    # 2. Prepare manifest dictionary for JSON serialization
    manifest_dict = {
        "sku": manifest.sku,
        "status": manifest.status,

        # Sprint 3 & 7: OCR Data
        "garment_type": manifest.garment_type,
        "brand": manifest.brand,
        "size": manifest.size,
        "color": manifest.color,
        "material": manifest.material,
        "department": manifest.department,
        "condition": manifest.condition,
        "condition_notes": manifest.condition_notes,

        # Sprint 4: Measurements
        "measurements": {
            "pit_to_pit": manifest.measurements.pit_to_pit,
            "length": manifest.measurements.length,
            "sleeve": manifest.measurements.sleeve,
            "waist": manifest.measurements.waist,
            "inseam": manifest.measurements.inseam,
        },

        # Sprint 5: Listing Data
        "title": manifest.title,
        "description": manifest.description,
        "category": manifest.category,
        "item_specifics": manifest.item_specifics,

        # Photo mapping (stored as filenames)
        "photos": {
            "sku_photo": manifest.photos.sku_photo.name if manifest.photos.sku_photo else None,
            "tag_photos": [p.name for p in manifest.photos.tag_photos],
            "measurement_photos": [p.name for p in manifest.photos.measurement_photos],
            "defect_photos": [p.name for p in manifest.photos.defect_photos],
            "front_photo": manifest.photos.front_photo.name if manifest.photos.front_photo else None,
            "back_photo": manifest.photos.back_photo.name if manifest.photos.back_photo else None,
            "detail_photos": [p.name for p in manifest.photos.detail_photos],
        },

        "raw_images": [p.name for p in manifest.raw_images],
        "created_draft": manifest.created_draft,
        "uploaded_to_ebay": manifest.uploaded_to_ebay,
    }

    # 3. Save manifest.json
    manifest_file = product_dir / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_dict, f, indent=4, ensure_ascii=False)

    app_logger.info(f"Saved manifest for {manifest.sku} to {manifest_file}")
    return manifest_file