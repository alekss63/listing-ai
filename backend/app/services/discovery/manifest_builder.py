from pathlib import Path

from backend.app.services.discovery.models import (
    ProductManifest,
    Measurements,
    PhotoSet,
)
from backend.app.services.discovery.product_grouper import ProductBatch
from backend.app.services.ai.photo_classifier import classify_photos
from backend.app.services.ocr.tag_extractor import extract_tag_data
from backend.app.services.measurements.measurement_extractor import extract_measurements
from backend.app.services.ai.condition_assessor import assess_condition
from backend.app.services.ai.listing_generator import generate_listing
from backend.app.core.logging import app_logger


def _resolve_path(image_paths: list[Path], filename: str | None) -> Path | None:
    if not filename:
        return None
    path_lookup = {p.name: p for p in image_paths}
    return path_lookup.get(filename)


def _resolve_paths(image_paths: list[Path], filenames: list[str] | None) -> list[Path]:
    if not filenames:
        return []
    path_lookup = {p.name: p for p in image_paths}
    return [path_lookup[name] for name in filenames if name in path_lookup]


def build_manifest(product: ProductBatch) -> ProductManifest:
    app_logger.info(f"Classifying photos for {product.sku}...")

    # 1. Classify photos using AI
    classification = classify_photos(product.images)

    # 2. Map the AI classification to Path objects
    photos = PhotoSet(
        sku_photo=_resolve_path(product.images, classification.get("sku_photo")),
        tag_photos=_resolve_paths(product.images, classification.get("tag_photos")),
        measurement_photos=_resolve_paths(product.images, classification.get("measurement_photos")),
        defect_photos=_resolve_paths(product.images, classification.get("defect_photos")),
        front_photo=_resolve_path(product.images, classification.get("front_photo")),
        back_photo=_resolve_path(product.images, classification.get("back_photo")),
        detail_photos=_resolve_paths(product.images, classification.get("detail_photos")),
    )

    # 3. Extract tag data using OCR
    # Send the SKU photo (bag sticker) FIRST, followed by interior garment tags
    ocr_photos = []
    if photos.sku_photo:
        ocr_photos.append(photos.sku_photo)
    ocr_photos.extend(photos.tag_photos)

    tag_data = {}
    if ocr_photos:
        tag_data = extract_tag_data(ocr_photos)

    # 4. Extract measurements
        measurement_data = {}
    if photos.measurement_photos:
        measurement_data = extract_measurements(
            photos.measurement_photos,
            garment_type=tag_data.get("garment_type"),
            size=tag_data.get("size"),
        )

    measurements = Measurements(
        pit_to_pit=measurement_data.get("pit_to_pit"),
        length=measurement_data.get("length"),
        sleeve=measurement_data.get("sleeve"),
        waist=measurement_data.get("waist"),
        inseam=measurement_data.get("inseam"),
    )

    # 5. Assess condition from front/back/detail/defect photos
    condition_photos = []
    if photos.front_photo:
        condition_photos.append(photos.front_photo)
    if photos.back_photo:
        condition_photos.append(photos.back_photo)
    condition_photos.extend(photos.detail_photos)
    condition_photos.extend(photos.defect_photos)
    condition_data = assess_condition(condition_photos)

    # 6. Determine final SKU
    extracted_sku = tag_data.get("sku")
    if extracted_sku:
        final_sku = extracted_sku
    else:
        # Fallback: Use Brand-Color-Type if no SKU sticker is found
        brand = (tag_data.get("brand") or "Unknown").replace(" ", "")
        color = (tag_data.get("color") or "Unknown").replace(" ", "")
        g_type = (tag_data.get("garment_type") or "Item").replace(" ", "")
        final_sku = f"{brand}-{color}-{g_type}"

    # 7. Build the initial manifest
    manifest = ProductManifest(
        sku=final_sku,
        extracted_sku=extracted_sku,
        photos=photos,
        measurements=measurements,
        raw_images=product.images,
        garment_type=tag_data.get("garment_type"),
        brand=tag_data.get("brand"),
        size=tag_data.get("size"),
        color=tag_data.get("color"),
        material=tag_data.get("material"),
        department=tag_data.get("department"),
        condition=condition_data.get("condition"),
        condition_notes=condition_data.get("condition_notes"),
    )

    # 8. Generate Listing
    listing_data = generate_listing(manifest)
    manifest.title = listing_data.get("title")
    manifest.description = listing_data.get("description")
    manifest.item_specifics = listing_data.get("item_specifics", {})

    return manifest