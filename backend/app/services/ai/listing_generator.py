# backend/app/services/ai/listing_generator.py
import json
import logging

import httpx

from backend.app.schemas import ListingDraft

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
        async with httpx.AsyncClient(timeout=60.0) as client:
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
        raise Exception(f"Failed to generate draft: {str(e)}")
