import io
import json
import re
import base64
import time
from pathlib import Path

from PIL import Image
from anthropic import APIConnectionError, APITimeoutError

from backend.app.services.ai.vision_client import get_client, DEFAULT_MODEL
from backend.app.core.logging import app_logger


GROUPING_PROMPT = """You are an expert e-commerce photography assistant.
I am providing you with a batch of raw product photos. They may contain MULTIPLE different physical products.

Here are the exact filenames provided:
{filenames}

Your task: Group the filenames by physical product.
CRITICAL RULES FOR GROUPING:
1. Be HIGHLY SKEPTICAL. Only group photos together if you are 100% certain they are the EXACT SAME physical item.
2. Look closely at the collar/neckline, the pattern/print, the pockets, and the fabric texture. 
3. If two shirts are both "blue button-downs" but have different patterns, different collars, or different pocket styles, they are DIFFERENT products. Put them in separate groups.
4. If in doubt, put them in separate groups.

Return ONLY a valid JSON object with this exact structure:
{{"groups": [["file1.jpg", "file2.jpg"], ["file3.jpg"]]}}
Do not include markdown formatting (no ```json). Just the raw JSON.
"""


def _make_thumbnail(path: Path, max_size: int = 192) -> dict:
    """Create a tiny thumbnail so many photos easily fit in one API call."""
    with Image.open(path) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        # Very low quality, but perfectly fine for just grouping items
        img.save(buffer, format="JPEG", quality=30, optimize=True)
        raw_bytes = buffer.getvalue()

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.standard_b64encode(raw_bytes).decode("utf-8"),
        },
    }


def group_loose_images(image_paths: list[Path]) -> list[list[Path]]:
    """
    Uses Claude Vision to group loose photos by physical product.
    """
    if not image_paths:
        return []

    batch = image_paths[:40]
    if len(image_paths) > 40:
        app_logger.warning(
            f"{len(image_paths)} loose photos found. "
            "Only grouping the first 40 in this pass."
        )

    filenames = [p.name for p in batch]
    prompt = GROUPING_PROMPT.format(filenames=", ".join(filenames))

    app_logger.info(f"Smart-grouping {len(batch)} loose photo(s)...")

    content = [_make_thumbnail(p) for p in batch]
    content.append({"type": "text", "text": prompt})

    # Auto-retry logic to survive flaky macOS network drops
    max_retries = 3
    response_text = ""
    for attempt in range(max_retries):
        try:
            response = get_client().messages.create(
                model=DEFAULT_MODEL,
                max_tokens=1000,
                messages=[{"role": "user", "content": content}],
            )
            response_text = response.content[0].text
            break
        except (APIConnectionError, APITimeoutError) as e:
            if attempt < max_retries - 1:
                app_logger.warning(f"Grouping connection dropped on attempt {attempt + 1}. Retrying in 3 seconds...")
                time.sleep(3)
            else:
                app_logger.error("Max retries reached for grouping. Connection failed.")
                raise e

    clean_text = re.sub(r"```json|```", "", response_text).strip()

    try:
        data = json.loads(clean_text)
    except json.JSONDecodeError as e:
        app_logger.error(f"Failed to parse grouping JSON: {e}\nRaw: {response_text}")
        return [[p] for p in batch]  # Fallback: every photo its own product

    path_lookup = {p.name: p for p in batch}
    groups: list[list[Path]] = []

    for group in data.get("groups", []):
        resolved = [path_lookup[name] for name in group if name in path_lookup]
        if resolved:
            groups.append(resolved)

    # Safety net: any photo Claude forgot gets its own group
    grouped_names = {p.name for g in groups for p in g}
    for p in batch:
        if p.name not in grouped_names:
            groups.append([p])

    return groups