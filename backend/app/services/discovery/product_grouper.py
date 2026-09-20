"""Group scanned photos into per-product batches.

Two strategies exist because photos arrive two ways:

``group_by_folder``
    For photos already sorted into one folder per item under ``Pictures/``.

``group_by_product``
    For a flat run of photos shot back to back, where a readable SKU sticker
    marks the start of each new item.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from backend.app.core.paths import PICTURES
from backend.app.services.discovery.image_scanner import ImageFile
from backend.app.services.discovery.models import ProductManifest
from backend.app.services.discovery.sku_detector import SKUResult


@dataclass
class ProductBatch:
    sku: str
    images: list[Path] = field(default_factory=list)
    # Populated later by the discovery service once photos are analysed.
    manifest: ProductManifest | None = None


def _resolve_sku(image: ImageFile) -> str:
    """
    Resolve the product SKU from the image path.

    Expected structure:
        Pictures/Product1/image1.jpg

    If an image is directly inside Pictures/, use the filename stem
    as a fallback SKU.
    """
    try:
        relative_path = image.path.relative_to(PICTURES)

        if len(relative_path.parts) > 1:
            return relative_path.parts[0]

        return image.path.stem

    except ValueError:
        return image.path.parent.name or image.path.stem


def group_by_folder(images: list[ImageFile]) -> list[ProductBatch]:
    """
    Group scanned images into product batches.

    Each folder inside Pictures/ becomes one product batch.
    """
    grouped: dict[str, list[ImageFile]] = defaultdict(list)

    for image in images:
        sku = _resolve_sku(image)
        grouped[sku].append(image)

    product_batches: list[ProductBatch] = []

    for sku, image_files in grouped.items():
        image_files.sort(key=lambda image_file: image_file.created)

        product_batches.append(
            ProductBatch(
                sku=sku,
                images=[image_file.path for image_file in image_files],
            )
        )

    product_batches.sort(key=lambda batch: batch.sku)

    return product_batches


def group_by_product(
    images: list[ImageFile],
    sku_results: list[SKUResult],
) -> list[ProductBatch]:
    """
    Group a flat sequence of photos into product batches by SKU sticker.

    ``images`` and ``sku_results`` are parallel lists: ``sku_results[i]`` is the
    SKU detection for ``images[i]``. Photographing an item starts by shooting
    its SKU sticker, so every successfully read sticker opens a new batch and
    the photos that follow belong to it.

    A repeated SKU still opens a separate batch, because the same sticker
    appearing twice means the item was photographed twice. Photos taken before
    the first readable sticker belong to no item and are dropped.
    """
    if len(images) != len(sku_results):
        raise ValueError(
            "images and sku_results must contain the same number of entries: "
            f"got {len(images)} images and {len(sku_results)} SKU results"
        )

    # Sequence is what assigns a photo to an item, so order by capture time
    # rather than trusting the order the caller happened to supply.
    paired = sorted(
        zip(images, sku_results, strict=True),
        key=lambda pair: pair[0].created,
    )

    product_batches: list[ProductBatch] = []
    current: ProductBatch | None = None

    for image, sku_result in paired:
        if not sku_result.requires_manual_review():
            current = ProductBatch(sku=sku_result.sku)
            product_batches.append(current)

        if current is None:
            continue

        current.images.append(image.path)

    return product_batches
