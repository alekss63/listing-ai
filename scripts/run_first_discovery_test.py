import shutil
import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.app.core.paths import PICTURES
from backend.app.services.discovery.image_scanner import scan_images
from backend.app.services.discovery.manifest_builder import build_manifest
from backend.app.services.discovery.product_grouper import group_by_folder

TEST_SKU = "Product1"


def create_test_product_folder() -> Path:
    test_product_dir = PICTURES / TEST_SKU

    if test_product_dir.exists():
        raise RuntimeError(
            f"Test aborted: {test_product_dir} already exists. "
            "Rename or remove it before running the first Discovery Engine test."
        )

    test_product_dir.mkdir(parents=True)

    image_one = Image.new(
        "RGB",
        size=(800, 600),
        color=(180, 40, 40),
    )
    image_one.save(
        test_product_dir / "image1.jpg",
        format="JPEG",
    )

    image_two = Image.new(
        "RGB",
        size=(800, 600),
        color=(40, 80, 180),
    )
    image_two.save(
        test_product_dir / "image2.jpg",
        format="JPEG",
    )

    return test_product_dir


def main() -> int:
    print("Running first Discovery Engine test")
    print("=" * 40)

    test_product_dir: Path | None = None

    try:
        test_product_dir = create_test_product_folder()

        scanned_images = scan_images()
        product_batches = group_by_folder(scanned_images)

        target_batch = next(
            (batch for batch in product_batches if batch.sku == TEST_SKU),
            None,
        )

        print("\nFound products:")

        if target_batch is None:
            print("- none")
            print("\nFirst Discovery Engine test failed.")
            return 1

        manifest = build_manifest(target_batch)

        print(f"- {manifest.sku}")
        print(f"  - image count detected: {len(manifest.raw_images)}")

        if len(manifest.raw_images) != 2:
            print("\nFirst Discovery Engine test failed.")
            return 1

        print("\nFirst Discovery Engine test passed.")
        return 0

    except Exception as exc:
        print(f"\nFirst Discovery Engine test failed: {exc}")
        return 1

    finally:
        if test_product_dir is not None and test_product_dir.exists():
            shutil.rmtree(test_product_dir)


if __name__ == "__main__":
    raise SystemExit(main())
