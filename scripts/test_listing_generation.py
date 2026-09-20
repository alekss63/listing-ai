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
    
    # FIX: Limit to 5 images to bypass macOS SSL payload fragmentation limits during testing
    if len(image_paths) > 5:
        print(f"Note: {len(image_paths)} images found. Limiting to first 5 to prevent macOS SSL dropouts.")
        image_paths = image_paths[:5]
    
    print(f"Running full pipeline for {TEST_SKU}... (This may take a minute)")
    
    batch = ProductBatch(sku=TEST_SKU, images=image_paths)
    manifest = build_manifest(batch)
    
    print("\n" + "="*50)
    print(f"GENERATED EBAY LISTING FOR: {manifest.sku}")
    print("="*50)
    
    print(f"\nTITLE:\n{manifest.title}")
    
    print(f"\nDESCRIPTION:\n{manifest.description}")
    
    print(f"\nITEM SPECIFICS:")
    for k, v in (manifest.item_specifics or {}).items():
        print(f"  - {k}: {v}")
        
    print("\n" + "="*50)
    
    return 0

if __name__ == "__main__":
    raise SystemExit(main())