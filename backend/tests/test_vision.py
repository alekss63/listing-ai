from pathlib import Path

import pytest

from backend.app.services.listing.vision import (
    VisionListingAnalysis,
    analysis_from_response,
    merge_analyses,
    parse_model_json,
)


def test_model_json_can_be_wrapped_in_a_code_fence():
    assert parse_model_json('```json\n{"brand": "Oakley"}\n```') == {"brand": "Oakley"}


def test_invalid_model_json_is_rejected():
    with pytest.raises(ValueError, match="invalid"):
        parse_model_json("probably an Oakley shirt")


def test_analysis_applies_defect_condition_and_review_requirement():
    analysis = analysis_from_response(
        {
            "item_type": "T-shirt",
            "brand": "Oakley",
            "color": "Black",
            "size": "L",
            "material": None,
            "has_tags": False,
            "has_defects": True,
            "is_used": False,
            "condition_evidence": ["IMG_1.jpg: small spot visible on front"],
            "used_evidence": [],
            "defects": ["Small spot on front"],
            "title_facts": ["Oakley", "T-shirt", "Black", "Large"],
            "suggested_category": "Men's T-Shirts",
            "review_notes": ["Confirm spot is a stain."],
        },
        [Path("Pictures/IMG_1.jpg")],
    )

    assert analysis.condition == "New with imperfections"
    assert (
        analysis.review_notes[0]
        == "Condition requires human confirmation before publication."
    )
    assert analysis.source_images == ["IMG_1.jpg"]


def test_used_condition_requires_explicit_wear_evidence():
    analysis = analysis_from_response(
        {
            "has_tags": False,
            "has_defects": False,
            "is_used": True,
            "condition_evidence": ["IMG_1.jpg: wrinkles visible"],
            "used_evidence": [],
        },
        [Path("Pictures/IMG_1.jpg")],
    )

    assert analysis.condition == "New without tags"
    assert analysis.review_notes[0].startswith("Unsupported used-condition")


def test_individual_analyses_merge_to_the_more_conservative_condition():
    first = VisionListingAnalysis(
        "Polo",
        "Nike",
        "Black",
        None,
        None,
        "New without tags",
        [],
        [],
        ["Nike"],
        "Polos",
        [],
        ["front.jpg"],
    )
    second = VisionListingAnalysis(
        "Polo",
        None,
        None,
        "L",
        None,
        "New with imperfections",
        ["back.jpg: spot"],
        ["Spot"],
        ["L"],
        None,
        ["Confirm spot"],
        ["back.jpg"],
    )

    merged = merge_analyses([first, second])

    assert merged.condition == "New with imperfections"
    assert merged.size == "L"
    assert merged.source_images == ["front.jpg", "back.jpg"]


def test_sewn_in_label_does_not_qualify_as_new_with_tags():
    label = VisionListingAnalysis(
        "Polo",
        "Nike",
        None,
        None,
        None,
        "New with tags",
        [],
        [],
        [],
        None,
        [],
        ["label.jpg"],
    )
    hang_tag = VisionListingAnalysis(
        "Polo",
        "Nike",
        None,
        None,
        None,
        "New with tags",
        ["tag.jpg: original retail hang tag attached"],
        [],
        [],
        None,
        [],
        ["tag.jpg"],
    )

    assert merge_analyses([label]).condition == "New without tags"
    assert merge_analyses([hang_tag]).condition == "New with tags"
