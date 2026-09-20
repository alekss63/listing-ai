from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from backend.app.core.paths import PICTURES
from backend.app.services.discovery.image_scanner import ImageFile


@dataclass
class ProductBatch:
    sku: str
    images: list[Path]


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


def group_by_product(images: list[ImageFile]) -> list[ProductBatch]:
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