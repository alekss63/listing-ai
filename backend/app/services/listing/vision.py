"""Claude Vision analysis for reviewable marketplace-listing drafts."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from anthropic import Anthropic, DefaultHttpxClient
from PIL import Image, ImageOps

from backend.app.core.config import settings
from backend.app.services.listing.policy import ListingPolicy

MAX_IMAGE_DIMENSION = 1024
MAX_IMAGES_PER_REQUEST = 20


@dataclass
class ConditionFinding:
    has_tags: bool = False
    has_defects: bool = False
    is_used: bool = False
    evidence: list[str] = field(default_factory=list)
    used_evidence: list[str] = field(default_factory=list)


@dataclass
class VisionListingAnalysis:
    item_type: str | None
    brand: str | None
    color: str | None
    size: str | None
    material: str | None
    condition: str
    condition_evidence: list[str]
    defects: list[str]
    title_facts: list[str]
    suggested_category: str | None
    review_notes: list[str]
    source_images: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SYSTEM_PROMPT = """You analyze resale-item photos for a human-reviewed eBay draft.
Do not invent a brand, size, material, measurements, or defects. Only report what
is visible or legible in the supplied images. Visible evidence must name the image
filename. Treat ordinary fabric texture, lighting, or wrinkles as non-defects unless
there is clear evidence otherwise. Return valid JSON only, with exactly these keys:
item_type, brand, color, size, material, has_tags, has_defects, is_used,
condition_evidence, used_evidence, defects, title_facts, suggested_category,
review_notes.
All booleans must be JSON booleans. Every non-boolean field except
suggested_category may be null or an array as appropriate. Add a review note for
any uncertainty, unreadable tag, apparent damage, or missing information.
Set has_tags to true only for an original retail hang tag or price tag visibly
attached to the item. A sewn-in brand, size, care, or material label is not a
hang tag. Set is_used to true only if used_evidence names clear visible wear such as
fading, pilling, fraying, stains, holes, or worn soles. Wrinkles, creases,
missing tags, and ordinary handling are not evidence of use."""


def encode_image(path: Path) -> dict[str, Any]:
    """Normalize a local image to a size-bounded JPEG source for Claude."""
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION))
            buffer = BytesIO()
            image.save(buffer, format="JPEG", quality=75, optimize=True)
    except (OSError, ValueError) as exc:
        raise ValueError(f"Cannot prepare image {path.name}: {exc}") from exc

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.b64encode(buffer.getvalue()).decode("ascii"),
        },
    }


def parse_model_json(text: str) -> dict[str, Any]:
    """Parse a JSON response, tolerating an accidental Markdown code fence."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    try:
        result = json.loads(cleaned.strip())
    except json.JSONDecodeError as exc:
        raise ValueError("Claude returned invalid listing-analysis JSON") from exc
    if not isinstance(result, dict):
        raise ValueError("Claude listing analysis must be a JSON object")
    return result


def _text_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def analysis_from_response(
    data: dict[str, Any], source_images: list[Path]
) -> VisionListingAnalysis:
    """Convert Claude's JSON into a stable internal review object."""
    finding = ConditionFinding(
        has_tags=bool(data.get("has_tags", False)),
        has_defects=bool(data.get("has_defects", False)),
        is_used=bool(data.get("is_used", False)),
        evidence=_text_list(data.get("condition_evidence")),
        used_evidence=_text_list(data.get("used_evidence")),
    )
    has_clear_wear = finding.is_used and bool(finding.used_evidence)
    condition = ListingPolicy.recommended_condition(
        has_tags=finding.has_tags,
        has_defects=finding.has_defects,
        is_used=has_clear_wear,
    )
    review_notes = _text_list(data.get("review_notes"))
    if finding.is_used and not has_clear_wear:
        review_notes.insert(
            0,
            "Unsupported used-condition recommendation ignored; verify condition during review.",
        )
    if finding.has_defects or has_clear_wear:
        review_notes.insert(
            0, "Condition requires human confirmation before publication."
        )

    def string_or_none(key: str) -> str | None:
        value = data.get(key)
        return str(value).strip() if isinstance(value, str) and value.strip() else None

    return VisionListingAnalysis(
        item_type=string_or_none("item_type"),
        brand=string_or_none("brand"),
        color=string_or_none("color"),
        size=string_or_none("size"),
        material=string_or_none("material"),
        condition=condition,
        condition_evidence=finding.evidence,
        defects=_text_list(data.get("defects")),
        title_facts=_text_list(data.get("title_facts")),
        suggested_category=string_or_none("suggested_category"),
        review_notes=review_notes,
        source_images=[path.name for path in source_images],
    )


def merge_analyses(analyses: list[VisionListingAnalysis]) -> VisionListingAnalysis:
    """Conservatively merge per-photo analyses into one product review object."""
    if not analyses:
        raise ValueError("At least one analysis is required")

    def first_value(field: str) -> str | None:
        return next(
            (value for analysis in analyses if (value := getattr(analysis, field))),
            None,
        )

    def unique(field: str) -> list[str]:
        return list(
            dict.fromkeys(
                value for analysis in analyses for value in getattr(analysis, field)
            )
        )

    conditions = {analysis.condition for analysis in analyses}

    def has_retail_tag_evidence(analysis: VisionListingAnalysis) -> bool:
        evidence = " ".join(analysis.condition_evidence).lower()
        return (
            "hang tag" in evidence
            or "retail tag" in evidence
            or "price tag" in evidence
        )

    if "Used" in conditions:
        condition = "Used"
    elif "New with imperfections" in conditions:
        condition = "New with imperfections"
    elif any(
        analysis.condition == "New with tags" and has_retail_tag_evidence(analysis)
        for analysis in analyses
    ):
        condition = "New with tags"
    else:
        condition = "New without tags"

    notes = unique("review_notes")
    notes.insert(
        0,
        "Combined from individual photo analyses; confirm all details before creating an eBay draft.",
    )
    return VisionListingAnalysis(
        item_type=first_value("item_type"),
        brand=first_value("brand"),
        color=first_value("color"),
        size=first_value("size"),
        material=first_value("material"),
        condition=condition,
        condition_evidence=unique("condition_evidence"),
        defects=unique("defects"),
        title_facts=unique("title_facts"),
        suggested_category=first_value("suggested_category"),
        review_notes=notes,
        source_images=unique("source_images"),
    )


class ClaudeVisionAnalyzer:
    """Analyze one product's local photos using Claude Vision."""

    def __init__(self, client: Anthropic | None = None) -> None:
        if client is None:
            if not settings.ANTHROPIC_API_KEY:
                raise RuntimeError("ANTHROPIC_API_KEY is not configured")
            client = Anthropic(
                api_key=settings.ANTHROPIC_API_KEY,
                http_client=DefaultHttpxClient(
                    http2=True,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
                ),
            )
        self.client = client

    def analyze(self, image_paths: list[Path]) -> VisionListingAnalysis:
        if not image_paths:
            raise ValueError("At least one image is required for vision analysis")
        if len(image_paths) > MAX_IMAGES_PER_REQUEST:
            raise ValueError(
                f"A maximum of {MAX_IMAGES_PER_REQUEST} images may be analyzed at once"
            )

        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": "Analyze these product photos. Image filenames in order: "
                + ", ".join(path.name for path in image_paths),
            }
        ]
        content.extend(encode_image(path) for path in image_paths)
        response = self.client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=1200,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return analysis_from_response(parse_model_json(text), image_paths)

    def analyze_individually(self, image_paths: list[Path]) -> VisionListingAnalysis:
        """Analyze photos separately, then merge their evidence.

        This mode is useful on networks that reject multi-image uploads. It
        sends the same images but creates one API request per photo.
        """
        return merge_analyses([self.analyze([path]) for path in image_paths])
