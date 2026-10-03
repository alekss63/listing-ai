# backend/app/schemas.py
from pydantic import BaseModel, Field


class ProductSearchRequest(BaseModel):
    query: str = Field(..., description="Search query for products")
    category: str | None = Field(None, description="Optional category filter")
    max_price: float | None = Field(None, description="Optional maximum price")
    min_price: float | None = Field(None, description="Optional minimum price")
    sort: str | None = Field(
        None, description="Sort order (e.g.g., 'PricePlusShippingLowest')"
    )
    page: int = Field(1, ge=1, description="Page number for pagination")
    limit: int = Field(10, ge=1, le=100, description="Items per page (max 100)")


class Product(BaseModel):
    id: str = Field(..., description="Unique identifier")
    title: str = Field(..., description="Title of the product")
    price: float = Field(..., description="Price of the product")
    currency: str = Field(..., description="Currency code (e.g., 'USD')")
    url: str = Field(..., description="URL to the product page")
    image_url: str | None = Field(None, description="URL to product image")


class ProductSearchResponse(BaseModel):
    products: list[Product] = Field(..., description="List of matching products")
    total_results: int = Field(..., description="Total number of results found")
    page: int = Field(..., description="Current page number")
    limit: int = Field(..., description="Number of items per page")

    # Add to backend/app/schemas.py


class ItemSpecifics(BaseModel):
    """Dynamic key-value pairs for eBay item specifics."""

    brand: str | None = None
    size: str | None = None
    color: str | None = None
    material: str | None = None
    # Add other specifics as needed, or use a generic dict
    custom: dict[str, str] = Field(default_factory=dict)


class ListingDraft(BaseModel):
    """AI-generated draft ready for human review."""

    sku: str = Field(..., description="The product SKU")
    title: str = Field(..., description="SEO-optimized eBay title (max 80 chars)")
    description: str = Field(..., description="Clean, HTML-friendly description")
    suggested_price: float = Field(
        ..., description="Suggested price based on market data"
    )
    condition: str = Field(
        ..., description="eBay condition (e.g., 'New with tags', 'Pre-owned - Good')"
    )
    item_specifics: ItemSpecifics = Field(
        ..., description="Key attributes for eBay search visibility"
    )
    ai_notes: str = Field(
        ..., description="Brief explanation of why the AI chose this title/price"
    )
