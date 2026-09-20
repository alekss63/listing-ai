from pathlib import Path

import pytest

from backend.app.services.listing.draft_builder import (
    analyze_and_save_review_draft,
    build_review_draft,
    save_review_draft,
)
from backend.app.services.listing.vision import VisionListingAnalysis


def sample_analysis() -> VisionListingAnalysis:
    return VisionListingAnalysis(
        item_type="Polo shirt",
        brand="Nike Golf",
        color="Black",
        size="L",
        material=None,
        condition="New without tags",
        condition_evidence=[],
        defects=[],
        title_facts=[],
        suggested_category="Men's Polos",
        review_notes=[],
        source_images=["Golf1.png"],
    )


def test_review_draft_is_always_draft_only_and_needs_weight():
    draft = build_review_draft(product_id="nike-golf-polo", analysis=sample_analysis())

    assert draft.submission_mode == "draft_only"
    assert draft.status == "review_required"
    assert draft.shipping_and_returns is None
    assert "packaged shipping weight" in draft.review_notes[0]
    assert draft.title == "Nike Golf Black Polo shirt L"


def test_review_draft_applies_shipping_when_weight_is_known():
    draft = build_review_draft(
        product_id="nike-golf-polo", analysis=sample_analysis(), weight_oz=11.1
    )

    assert draft.shipping_and_returns.shipping_cost == 12.99
    assert draft.shipping_and_returns.return_shipping_paid_by == "buyer"


def test_review_draft_can_use_a_selected_shipping_tier_without_weight():
    draft = build_review_draft(
        product_id="nike-golf-polo", analysis=sample_analysis(), shipping_cost=9.99
    )

    assert draft.shipping_and_returns.shipping_cost == 9.99
    assert draft.shipping_and_returns.billed_weight_oz is None


def test_review_draft_rejects_weight_and_shipping_rate_together():
    with pytest.raises(ValueError, match="either"):
        build_review_draft(
            product_id="nike-golf-polo",
            analysis=sample_analysis(),
            weight_oz=4,
            shipping_cost=9.99,
        )


def test_review_draft_serializes_to_local_json(tmp_path):
    draft = build_review_draft(product_id="nike-golf-polo", analysis=sample_analysis())

    path = save_review_draft(draft, directory=tmp_path)

    assert path == tmp_path / "nike-golf-polo.json"
    assert '"submission_mode": "draft_only"' in path.read_text(encoding="utf-8")


def test_product_id_cannot_escape_drafts_folder():
    with pytest.raises(ValueError, match="letters"):
        build_review_draft(product_id="../outside", analysis=sample_analysis())


def test_analysis_results_are_cached_between_retries(tmp_path, monkeypatch):
    class FakeAnalyzer:
        def __init__(self):
            self.calls = 0

        def analyze(self, paths):
            self.calls += 1
            return sample_analysis()

    from backend.app.services.listing import draft_builder

    monkeypatch.setattr(draft_builder, "TEMP", tmp_path / "temp")
    monkeypatch.setattr(draft_builder, "DRAFTS", tmp_path / "drafts")
    analyzer = FakeAnalyzer()
    images = [Path("first.jpg"), Path("second.jpg")]

    analyze_and_save_review_draft(
        product_id="test-item", image_paths=images, analyzer=analyzer
    )
    analyze_and_save_review_draft(
        product_id="test-item", image_paths=images, analyzer=analyzer
    )

    assert analyzer.calls == 2
