import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.paths import PICTURES
from backend.app.services.discovery.manifest_builder import build_manifest
from backend.app.services.discovery.product_grouper import ProductBatch

TEST_SKU = "TestClassification"


def main() -> int:
    test_dir = PICTURES / TEST_SKU

    if not test_dir.exists() or not any(test_dir.iterdir()):
        print(f"ERROR: Please place photos into {test_dir}")
        return 1

    image_paths = [
        f
        for f in test_dir.iterdir()
        if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]

    print(f"Building manifest for {TEST_SKU} with {len(image_paths)} photos...")

    batch = ProductBatch(sku=TEST_SKU, images=image_paths)
    manifest = build_manifest(batch)

    print("\n--- Manifest PhotoSet ---")
    print(
        f"Front Photo: {manifest.photos.front_photo.name if manifest.photos.front_photo else 'None'}"
    )
    print(
        f"Back Photo: {manifest.photos.back_photo.name if manifest.photos.back_photo else 'None'}"
    )
    print(
        f"SKU Photo: {manifest.photos.sku_photo.name if manifest.photos.sku_photo else 'None'}"
    )
    print(f"Tag Photos: {[p.name for p in manifest.photos.tag_photos]}")
    print(f"Measurement Photos: {[p.name for p in manifest.photos.measurement_photos]}")
    print(f"Defect Photos: {[p.name for p in manifest.photos.defect_photos]}")
    print(f"Detail Photos: {[p.name for p in manifest.photos.detail_photos]}")
    print("-------------------------")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
