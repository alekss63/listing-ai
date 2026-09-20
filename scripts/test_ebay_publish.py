import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.paths import PRODUCTS
from backend.app.services.ebay.draft_publisher import publish_to_ebay

def main():
    # Pick the first available manifest to test
    for product_dir in PRODUCTS.iterdir():
        manifest_file = product_dir / "manifest.json"
        if manifest_file.exists():
            print(f"Testing publish for: {product_dir.name}")
            publish_to_ebay(manifest_file)
            return
            
    print("No manifests found in storage/products/")

if __name__ == "__main__":
    main()