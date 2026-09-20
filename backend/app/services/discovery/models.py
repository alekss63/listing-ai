from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Measurements:
    pit_to_pit: float | None = None
    length: float | None = None
    sleeve: float | None = None
    waist: float | None = None
    inseam: float | None = None


@dataclass
class PhotoSet:
    sku_photo: Path | None = None
    tag_photos: list[Path] = field(default_factory=list)
    measurement_photos: list[Path] = field(default_factory=list)
    defect_photos: list[Path] = field(default_factory=list)
    front_photo: Path | None = None
    back_photo: Path | None = None
    detail_photos: list[Path] = field(default_factory=list)


@dataclass
class ProductManifest:
    sku: str
    photos: PhotoSet
    measurements: Measurements
    raw_images: list[Path]

    extracted_sku: str | None = None
    garment_type: str | None = None
    brand: str | None = None
    size: str | None = None
    color: str | None = None
    material: str | None = None
    department: str | None = None

    condition: str | None = None
    condition_notes: str | None = None

    title: str | None = None
    description: str | None = None
    category: str | None = None
    item_specifics: dict[str, str] = field(default_factory=dict)

    status: str = "discovered"
    created_draft: bool = False
    uploaded_to_ebay: bool = False