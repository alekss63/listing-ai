import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.paths import PICTURES
from backend.app.services.discovery.image_scanner import scan_images
from backend.app.services.discovery.manifest_builder import build_manifest
from backend.app.services.discovery.product_grouper import (
    ProductBatch,
    group_by_folder,
)
from backend.app.services.discovery.smart_grouper import group_loose_images
from backend.app.services.discovery.storage import save_manifest

SUPPORTED = {".jpg", ".jpeg", ".png"}


def main() -> int:
    print("Starting Full ListingAI Discovery Pipeline...")
    print("=" * 50)

    # 1. Scan all images
    images = scan_images()
    if not images:
        print("No images found in Pictures directory.")
        return 0
    print(f"Scanned {len(images)} total images.")

    # 2. Separate organized folders from loose photos
    organized = [img for img in images if img.path.parent != PICTURES]
    loose = [img for img in images if img.path.parent == PICTURES]

    print(f"Found {len(organized)} images in organized folders.")
    print(f"Found {len(loose)} loose images in Pictures/ root.")

    batches = group_by_folder(organized)

    # 3. Smart-group loose photos by physical product using AI
    if loose:
        loose_paths = [img.path for img in loose]
        groups = group_loose_images(loose_paths)

        for i, group in enumerate(groups, start=1):
            batches.append(ProductBatch(sku=f"Batch{i}", images=group))

        print(f"AI grouped loose photos into {len(groups)} product(s).")

    print(f"Total products to process: {len(batches)}")
    print("=" * 50)

    success_count = 0
    fail_count = 0

    # 4. Process and Save
    for i, batch in enumerate(batches):
        print(
            f"\n[{i+1}/{len(batches)}] Processing SKU: {batch.sku} ({len(batch.images)} images)..."
        )

        if len(batch.images) > 8:
            print(
                f"  ⚠️  Warning: {len(batch.images)} images. Large payloads might trigger macOS SSL dropouts."
            )

        try:
            manifest = build_manifest(batch)
            save_manifest(manifest)
            print(f"  ✅ SUCCESS: Saved to storage/products/{manifest.sku}/")
            print(f"  📦 Originals moved to Processed/{manifest.sku}/")
            success_count += 1

        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            fail_count += 1

        if i < len(batches) - 1:
            print("  ⏳ Pausing for 1 second to respect API rate limits...")
            time.sleep(1)

    print("\n" + "=" * 50)
    print(
        f"Pipeline finished! Processed {success_count} products. Failed: {fail_count}."
    )
    print("Check 'storage/products/' for manifests and 'Processed/' for your archive!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
