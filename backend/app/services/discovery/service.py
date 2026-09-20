"""End-to-end product discovery from a folder of raw item photographs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.logging import app_logger
from backend.app.core.paths import PRODUCTS, ROOT
from backend.app.services.discovery.image_scanner import ImageFile, scan_images
from backend.app.services.discovery.manifest_builder import build_manifest
from backend.app.services.discovery.models import ProductManifest
from backend.app.services.discovery.product_grouper import ProductBatch, group_by_product
from backend.app.services.discovery.sku_detector import SKUResult, detect_sku


@dataclass
class DiscoveryResult:
    scanned_images: int
    products: list[ProductBatch]
    manifests: list[Path]


def _manifest_path(sku: str, sequence: int) -> Path:
    """Allocate a predictable, non-destructive manifest location."""
    suffix = "" if sequence == 1 else f"-{sequence}"
    return PRODUCTS / f"{sku}{suffix}" / "manifest.json"


def save_manifest(manifest: ProductManifest, sequence: int) -> Path:
    """Persist one portable product manifest without copying or moving photos."""
    path = _manifest_path(manifest.sku, sequence)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **manifest.to_dict(project_root=ROOT),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def discover_products(
    images: list[ImageFile] | None = None,
    sku_results: list[SKUResult] | None = None,
    *,
    persist: bool = True,
) -> DiscoveryResult:
    """Scan photos, detect SKU boundaries, group items, and save manifests.

    Passing ``images`` and ``sku_results`` is primarily useful for tests and
    preview tooling. In normal use both are derived from the Pictures folder.
    """
    scanned = scan_images() if images is None else images
    detected = sku_results
    if detected is None:
        detected = [detect_sku(image.path) for image in scanned]

    products = group_by_product(scanned, detected)
    manifests: list[Path] = []
    sku_counts: dict[str, int] = {}

    for product in products:
        product.manifest = build_manifest(product)
        sku_counts[product.sku] = sku_counts.get(product.sku, 0) + 1
        if persist:
            manifests.append(save_manifest(product.manifest, sku_counts[product.sku]))

    app_logger.info(
        "Discovery completed: {} images, {} products, {} manifests",
        len(scanned),
        len(products),
        len(manifests),
    )
    return DiscoveryResult(len(scanned), products, manifests)
