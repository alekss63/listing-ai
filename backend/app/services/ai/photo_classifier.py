import json
import re
import time
from pathlib import Path

from backend.app.services.ai.vision_client import ask_vision
from backend.app.core.logging import app_logger


CLASSIFICATION_PROMPT = """You are an expert e-commerce product photographer and listing specialist. 
I am going to provide you with a batch of raw photos for a single product. 

Your task is to analyze the images and classify each photo into exactly one of the following categories:
- sku_photo: A photo of a physical SKU sticker, inventory barcode, or handwritten ID number. This is very frequently located on the OUTSIDE of a plastic bag or packaging, and is often the very FIRST photo in the batch.
- tag_photos: Photos of the interior brand tag, size tag, or material care label.
- measurement_photos: Photos showing a measuring tape on the item (pit-to-pit, length, inseam, etc.).
- defect_photos: Close-up photos highlighting flaws, stains, rips, or wear.
- front_photo: The best, clearest photo of the front of the item.
- back_photo: The best, clearest photo of the back of the item.
- detail_photos: Any other general photos (angles, close-ups of fabric, buttons, logos).

Here are the exact filenames of the images provided in this batch:
{filenames}

Return ONLY a valid JSON object mapping the categories to the filename(s). 
- Use a string for single-photo categories (sku_photo, front_photo, back_photo). Use `null` if not found.
- Use an array of strings for multi-photo categories (tag_photos, measurement_photos, defect_photos, detail_photos). Use `[]` if none found.

Do not include any explanations, markdown formatting, or code blocks (no ```json). Just the raw JSON.
"""


def _merge_classifications(results: list[dict]) -> dict:
    """Stitches multiple chunk results back into a single PhotoSet dictionary."""
    merged = {
        "sku_photo": None,
        "tag_photos": [],
        "measurement_photos": [],
        "defect_photos": [],
        "front_photo": None,
        "back_photo": None,
        "detail_photos": [],
    }
    
    for res in results:
        # Keep the first non-null single photo we find
        if merged["sku_photo"] is None:
            merged["sku_photo"] = res.get("sku_photo")
        if merged["front_photo"] is None:
            merged["front_photo"] = res.get("front_photo")
        if merged["back_photo"] is None:
            merged["back_photo"] = res.get("back_photo")
            
        # Combine all list-based photos
        for key in ["tag_photos", "measurement_photos", "defect_photos", "detail_photos"]:
            if key in res and isinstance(res[key], list):
                merged[key].extend(res[key])
                
    return merged


def classify_photos(image_paths: list[Path]) -> dict:
    """
    Sends images to Claude Vision in chunks of 5 to bypass macOS SSL payload limits.
    """
    if not image_paths:
        return {}

    # Chunk into batches of 2
    chunk_size = 2
    chunks = [image_paths[i:i + chunk_size] for i in range(0, len(image_paths), chunk_size)]
    
    all_results = []
    
    for i, chunk in enumerate(chunks):
        filenames = [p.name for p in chunk]
        prompt = CLASSIFICATION_PROMPT.format(filenames=", ".join(filenames))
        
        app_logger.info(f"Classifying chunk {i+1}/{len(chunks)} ({len(chunk)} photos)...")
        
        response_text = ask_vision(
            prompt=prompt,
            image_paths=chunk,
            max_tokens=1000
        )

        clean_text = re.sub(r"```json|```", "", response_text).strip()

        try:
            all_results.append(json.loads(clean_text))
        except json.JSONDecodeError as e:
            app_logger.error(f"Failed to parse chunk {i+1} JSON: {e}\nRaw text: {response_text}")
            all_results.append({})
            
        # Pause between chunks to respect API rate limits
        if i < len(chunks) - 1:
            time.sleep(1)
            
    return _merge_classifications(all_results)