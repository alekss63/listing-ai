import json
import re

from backend.app.services.ai.vision_client import get_client, DEFAULT_MODEL
from backend.app.services.discovery.models import ProductManifest
from backend.app.core.logging import app_logger


LISTING_PROMPT = """You are an expert eBay listing copywriter and SEO specialist.
I will provide you with structured data extracted from a product's photos.

Product Data:
Garment Type: {garment_type}
Brand: {brand}
Size: {size}
Color: {color}
Material: {material}
Department: {department}
Condition: {condition}
Condition Notes: {condition_notes}
Measurements:
- Pit-to-Pit: {p2p} inches
- Length: {length} inches
- Sleeve: {sleeve} inches
- Waist: {waist} inches
- Inseam: {inseam} inches

Rules:
1. Title: Max 80 characters, SEO-optimized. Including the size is recommended, but you may omit it if it hurts readability or SEO.
2. Description: Write an engaging, honest, professional HTML-formatted description. It MUST clearly state the Condition and include the Condition Notes (describe any imperfections if present). Include the measurements clearly.
3. Item Specifics: A JSON object of eBay item specifics. It MUST include a "Condition" key with the exact condition value provided above.

Return ONLY a valid JSON object with these exact keys: "title", "description", "item_specifics".
Do not include markdown formatting (no ```json). Just the raw JSON.
"""


def generate_listing(manifest: ProductManifest) -> dict:
    app_logger.info(f"Generating eBay listing for {manifest.sku}...")

    prompt = LISTING_PROMPT.format(
        garment_type=manifest.garment_type or "Apparel",
        brand=manifest.brand or "Unknown",
        size=manifest.size or "Unknown",
        color=manifest.color or "Unknown",
        material=manifest.material or "Unknown",
        department=manifest.department or "Unknown",
        condition=manifest.condition or "New without tags, Store Display",
        condition_notes=manifest.condition_notes or "",
        p2p=manifest.measurements.pit_to_pit or "N/A",
        length=manifest.measurements.length or "N/A",
        sleeve=manifest.measurements.sleeve or "N/A",
        waist=manifest.measurements.waist or "N/A",
        inseam=manifest.measurements.inseam or "N/A",
    )

    client = get_client()
    response = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text
    clean_text = re.sub(r"```json|```", "", response_text).strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        app_logger.error(f"Failed to parse Listing JSON: {e}\nRaw text: {response_text}")
        return {}