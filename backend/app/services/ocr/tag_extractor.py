import json
import re
from pathlib import Path

from backend.app.services.ai.vision_client import ask_vision
from backend.app.core.logging import app_logger


TAG_EXTRACTION_PROMPT = """You are an expert e-commerce data entry specialist.
I am providing you with photo(s) of a clothing tag, label, or the garment itself.

Extract the following information:
- sku: The inventory SKU, sticker number, barcode, or handwritten ID number on the tag or plastic bag. (If not present, use null).
- garment_type: What is the item? (e.g., T-Shirt, Hoodie, Jeans).
- brand: The brand name.
- size: The size (e.g., M, Large, 10).
- color: The primary color.
- material: The fabric composition.
- department: The target gender (e.g., Men, Women).

Return ONLY a valid JSON object with these exact keys. Use `null` if not visible.
Do not include markdown formatting. Just the raw JSON.
"""


def extract_tag_data(tag_photos: list[Path]) -> dict:
    if not tag_photos:
        return {}

    app_logger.info(f"Extracting tag data from {len(tag_photos)} photo(s)...")

    response_text = ask_vision(
        prompt=TAG_EXTRACTION_PROMPT,
        image_paths=tag_photos,
        max_tokens=500,
        max_size=800,
        quality=60,
    )

    clean_text = re.sub(r"```json|```", "", response_text).strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        app_logger.error(f"Failed to parse OCR JSON response: {e}\nRaw text: {response_text}")
        return {}