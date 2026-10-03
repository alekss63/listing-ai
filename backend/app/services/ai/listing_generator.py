# backend/app/services/ai/listing_generator.py
import json
import logging
import re
from typing import TYPE_CHECKING

import httpx

from backend.app.core.logging import app_logger
from backend.app.schemas import ListingDraft
from backend.app.services.ai.vision_client import DEFAULT_MODEL, get_client

if TYPE_CHECKING:
    # Runtime import would be circular: discovery -> manifest_builder -> here
    from backend.app.services.discovery.models import ProductManifest

logger = logging.getLogger(__name__)

# Point this to your local Ollama instance
OLLAMA_URL = "http://localhost:11434/api/generate"
# Use a model good at JSON and reasoning. qwen2.5-coder:7b or llama3.2:3b are great free choices.
MODEL_NAME = "qwen2.5-coder:14b"


async def generate_listing_draft(sku: str, raw_product_data: dict) -> ListingDraft:
    """
    Uses local Ollama to generate an optimized eBay listing draft.
    """
    # Update the prompt inside backend/app/services/ai/listing_generator.py

    prompt = f"""
    You are an expert eBay listing optimizer. 
    Generate a listing draft for the following product data.
    
    Product Data: {json.dumps(raw_product_data, indent=2)}
    
    STRICT RULES:
    1. Title: Max 80 characters, highly searchable, capitalize key words.
    2. Description: Clean, professional. Highlight ONLY features explicitly mentioned in the Product Data.
    3. Price: Suggest a competitive price. If no price data exists, suggest a conservative estimate and explain why in ai_notes.
    4. Item Specifics: Extract ONLY if explicitly stated in the data. If unknown, use null. DO NOT GUESS (e.g., if sleeve length is not in the data, set it to null).
    5. Respond ONLY with valid JSON matching this exact structure:
    {{
      "sku": "{sku}",
      "title": "string",
      "description": "string",
      "suggested_price": 0.0,
      "condition": "string",
      "item_specifics": {{
        "brand": "string or null",
        "size": "string or null",
        "color": "string or null",
        "material": "string or null",
        "custom": {{}}
      }},
      "ai_notes": "string"
    }}
    """
    try:
        # A 14B model on local hardware can take a few minutes per draft
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL_NAME,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",  # Forces Ollama to output valid JSON
                },
            )
            response.raise_for_status()
            result = response.json()

            # Parse the AI's JSON response into our Pydantic model
            draft_data = json.loads(result["response"])
            return ListingDraft(**draft_data)

    except Exception as e:
        logger.error(f"Ollama draft generation failed for SKU {sku}: {e}")
        raise Exception(f"Failed to generate draft: {str(e)}") from e


# Used by the discovery pipeline (manifest_builder) to write the manifest's
# initial title/description/item_specifics.
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


def generate_listing(manifest: "ProductManifest") -> dict:
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
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = response.content[0].text
    clean_text = re.sub(r"```json|```", "", response_text).strip()

    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as e:
        app_logger.error(
            f"Failed to parse Listing JSON: {e}\nRaw text: {response_text}"
        )
        return {}
