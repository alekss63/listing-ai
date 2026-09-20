"""Seller-specific policy used when creating marketplace listing drafts."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True)
class ShippingAndReturns:
    shipping_service: str
    shipping_cost: float
    return_window_days: int
    return_shipping_paid_by: str
    billed_weight_oz: int | None


class ListingPolicy:
    """Business rules supplied by the seller for clothing and accessories.

    All weights are rounded upward to the next whole ounce. A 12 oz item is
    deliberately assigned to the higher (12 oz and above) tier.
    """

    DEFAULT_CONDITION = "New without tags"
    TAGGED_CONDITION = "New with tags"
    DEFECT_CONDITION = "New with imperfections"
    USED_CONDITION = "Used"
    MARKETPLACE_SUBMISSION = "draft_only"

    @staticmethod
    def recommended_condition(*, has_tags: bool, has_defects: bool, is_used: bool = False) -> str:
        """Choose a conservative condition recommendation from photo findings.

        A visible defect overrides a tag because the item needs review before
        publication. ``is_used`` is reserved for the rare case where clear
        wear is visible in the photos.
        """
        if is_used:
            return ListingPolicy.USED_CONDITION
        if has_defects:
            return ListingPolicy.DEFECT_CONDITION
        if has_tags:
            return ListingPolicy.TAGGED_CONDITION
        return ListingPolicy.DEFAULT_CONDITION

    @staticmethod
    def shipping_and_returns(*, weight_oz: float, is_tie: bool = False) -> ShippingAndReturns:
        """Apply flat-rate USPS Ground and return policy to an item's weight."""
        if weight_oz <= 0:
            raise ValueError("weight_oz must be greater than zero")

        billed_weight_oz = ceil(weight_oz)
        if is_tie or billed_weight_oz <= 4:
            return ShippingAndReturns(
                shipping_service="USPS Ground Advantage",
                shipping_cost=5.99,
                return_window_days=60,
                return_shipping_paid_by="seller",
                billed_weight_oz=billed_weight_oz,
            )

        if billed_weight_oz < 12:
            return ShippingAndReturns(
                shipping_service="USPS Ground Advantage",
                shipping_cost=9.99,
                return_window_days=60,
                return_shipping_paid_by="seller",
                billed_weight_oz=billed_weight_oz,
            )

        return ShippingAndReturns(
            shipping_service="USPS Ground Advantage",
            shipping_cost=12.99,
            return_window_days=30,
            return_shipping_paid_by="buyer",
            billed_weight_oz=billed_weight_oz,
        )

    @staticmethod
    def shipping_and_returns_for_rate(shipping_cost: float) -> ShippingAndReturns:
        """Apply a seller-selected flat-rate tier when package weight is unknown."""
        if shipping_cost == 5.99:
            return ShippingAndReturns("USPS Ground Advantage", 5.99, 60, "seller", None)
        if shipping_cost == 9.99:
            return ShippingAndReturns("USPS Ground Advantage", 9.99, 60, "seller", None)
        if shipping_cost == 12.99:
            return ShippingAndReturns("USPS Ground Advantage", 12.99, 30, "buyer", None)
        raise ValueError("shipping_cost must be one of: 5.99, 9.99, 12.99")
