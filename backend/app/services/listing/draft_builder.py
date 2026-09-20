"""Build and save local, human-reviewable eBay draft payloads.

This module intentionally has no eBay API client. A saved file represents a
candidate draft only; it can never publish a marketplace listing.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from backend.app.core.paths import DRAFTS, ROOT, TEMP
from backend.app.services.listing.policy import ListingPolicy, ShippingAndReturns
from backend.app.services.listing.vision import (
    ClaudeVisionAnalyzer,
    VisionListingAnalysis,
    merge_analyses,
)

PRODUCT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


@dataclass
class ReviewDraft:
    product_id: str
    marketplace: str
    submission_mode: str
    status: str
    title: str | None
    condition: str
    suggested_category: str | None
    analysis: VisionListingAnalysis
    shipping_and_returns: ShippingAndReturns | None
    review_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_title(analysis: VisionListingAnalysis, limit: int = 80) -> str | None:
    """Create a short, conservative title from facts confirmed in the photos."""
    parts = [analysis.brand, analysis.color, analysis.item_type, analysis.size]
    title = " ".join(part.strip() for part in parts if part and part.strip())
    return title[:limit].rstrip() or None


def build_review_draft(
    *,
    product_id: str,
    analysis: VisionListingAnalysis,
    weight_oz: float | None = None,
    shipping_cost: float | None = None,
    is_tie: bool = False,
) -> ReviewDraft:
    """Build a local draft that is deliberately blocked pending human review."""
    if not PRODUCT_ID_PATTERN.fullmatch(product_id):
        raise ValueError(
            "product_id must use letters, numbers, hyphens, or underscores"
        )

    if weight_oz is not None and shipping_cost is not None:
        raise ValueError("provide either weight_oz or shipping_cost, not both")

    shipping = None
    notes = list(analysis.review_notes)
    if shipping_cost is not None:
        shipping = ListingPolicy.shipping_and_returns_for_rate(shipping_cost)
    elif weight_oz is None:
        notes.append(
            "Enter the packaged shipping weight before creating an eBay draft."
        )
    else:
        shipping = ListingPolicy.shipping_and_returns(
            weight_oz=weight_oz, is_tie=is_tie
        )

    return ReviewDraft(
        product_id=product_id,
        marketplace="ebay",
        submission_mode=ListingPolicy.MARKETPLACE_SUBMISSION,
        status="review_required",
        title=build_title(analysis),
        condition=analysis.condition,
        suggested_category=analysis.suggested_category,
        analysis=analysis,
        shipping_and_returns=shipping,
        review_notes=notes,
    )


def save_review_draft(draft: ReviewDraft, directory: Path = DRAFTS) -> Path:
    """Save a local JSON review draft; no external API call is made."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{draft.product_id}.json"
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "project_root": str(ROOT),
        **draft.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _analysis_cache_path(product_id: str, image_path: Path) -> Path:
    return TEMP / "vision" / product_id / f"{image_path.name}.json"


def _load_cached_analysis(path: Path) -> VisionListingAnalysis:
    return VisionListingAnalysis(**json.loads(path.read_text(encoding="utf-8")))


def _save_cached_analysis(path: Path, analysis: VisionListingAnalysis) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(analysis.to_dict(), indent=2) + "\n", encoding="utf-8")


def analyze_and_save_review_draft(
    *,
    product_id: str,
    image_paths: list[Path],
    weight_oz: float | None = None,
    shipping_cost: float | None = None,
    is_tie: bool = False,
    analyzer: ClaudeVisionAnalyzer | None = None,
) -> tuple[ReviewDraft, Path]:
    """Run Claude Vision, then save the resulting local review draft."""
    if not PRODUCT_ID_PATTERN.fullmatch(product_id):
        raise ValueError(
            "product_id must use letters, numbers, hyphens, or underscores"
        )

    vision = analyzer or ClaudeVisionAnalyzer()
    analyses: list[VisionListingAnalysis] = []
    for image_path in image_paths:
        cache_path = _analysis_cache_path(product_id, image_path)
        if cache_path.exists():
            analyses.append(_load_cached_analysis(cache_path))
            continue
        analysis = vision.analyze([image_path])
        _save_cached_analysis(cache_path, analysis)
        analyses.append(analysis)

    analysis = merge_analyses(analyses)
    draft = build_review_draft(
        product_id=product_id,
        analysis=analysis,
        weight_oz=weight_oz,
        shipping_cost=shipping_cost,
        is_tie=is_tie,
    )
    return draft, save_review_draft(draft)
