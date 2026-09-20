import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.paths import PICTURES
from backend.app.services.discovery.product_grouper import ProductBatch
from backend.app.services.discovery.manifest_builder import build_manifest

TEST_SKU = "TestClassification"

def main() -> int:
    test_dir = PICTURES / TEST_SKU
    
    if not test_dir.exists() or not any(test_dir.iterdir()):
        print(f"ERROR: Please place photos into {test_dir}")
        return 1

    image_paths = [f for f in test_dir.iterdir() if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png"}]
    
    print(f"Running full pipeline for {TEST_SKU}...")
    
    batch = ProductBatch(sku=TEST_SKU, images=image_paths)
    manifest = build_manifest(batch)
    
    print("\n--- Extracted Tag Data ---")
    print(f"Brand:      {manifest.brand}")
    print(f"Size:       {manifest.size}")
    print(f"Color:      {manifest.color}")
    print(f"Material:   {manifest.material}")
    print(f"Department: {manifest.department}")
    
    print("\n--- Extracted Measurements (Sprint 4) ---")
    print(f"Pit-to-Pit: {manifest.measurements.pit_to_pit} inches")
    print(f"Length:     {manifest.measurements.length} inches")
    print(f"Sleeve:     {manifest.measurements.sleeve} inches")
    print(f"Waist:      {manifest.measurements.waist} inches")
    print(f"Inseam:     {manifest.measurements.inseam} inches")
    print("------------------------------------------")
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())