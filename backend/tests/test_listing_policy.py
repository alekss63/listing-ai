import pytest

from backend.app.services.listing.policy import ListingPolicy


def test_condition_defaults_to_new_without_tags():
    assert (
        ListingPolicy.recommended_condition(has_tags=False, has_defects=False)
        == "New without tags"
    )


def test_condition_flags_defects_and_rare_used_items():
    assert (
        ListingPolicy.recommended_condition(has_tags=True, has_defects=True)
        == "New with imperfections"
    )
    assert (
        ListingPolicy.recommended_condition(
            has_tags=False, has_defects=False, is_used=True
        )
        == "Used"
    )


def test_ties_and_light_items_use_lowest_shipping_tier():
    tie = ListingPolicy.shipping_and_returns(weight_oz=5, is_tie=True)
    light_item = ListingPolicy.shipping_and_returns(weight_oz=4.0)

    assert tie.shipping_cost == 5.99
    assert light_item.shipping_cost == 5.99
    assert tie.return_shipping_paid_by == "seller"


def test_weight_is_rounded_up_and_twelve_ounces_uses_higher_tier():
    result = ListingPolicy.shipping_and_returns(weight_oz=11.1)
    exactly_twelve = ListingPolicy.shipping_and_returns(weight_oz=12)

    assert result.billed_weight_oz == 12
    assert result.shipping_cost == 12.99
    assert result.return_window_days == 30
    assert exactly_twelve.shipping_cost == 12.99
    assert exactly_twelve.return_shipping_paid_by == "buyer"


def test_weight_must_be_positive():
    with pytest.raises(ValueError, match="greater than zero"):
        ListingPolicy.shipping_and_returns(weight_oz=0)


def test_selected_shipping_tier_does_not_invent_a_weight():
    result = ListingPolicy.shipping_and_returns_for_rate(9.99)

    assert result.shipping_cost == 9.99
    assert result.return_window_days == 60
    assert result.return_shipping_paid_by == "seller"
    assert result.billed_weight_oz is None
