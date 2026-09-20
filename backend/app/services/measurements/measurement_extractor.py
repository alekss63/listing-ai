import json
import re
from pathlib import Path

from backend.app.core.logging import app_logger
from backend.app.services.ai.vision_client import ask_vision

MEASUREMENT_EXTRACTION_PROMPT = """You are an expert e-commerce apparel specialist.
I am providing you with HIGH RESOLUTION photo(s) of a measuring tape placed on a garment.
Context: the garment is a {garment_type}, size {size}.

Your task: read the measuring tape and extract dimensions in inches:
- pit_to_pit: across the chest, armpit seam to armpit seam.
- length: top of shoulder/collar to bottom hem.
- sleeve: shoulder seam to cuff.
- waist: across the waistband.
- inseam: crotch seam to bottom hem.

How to read the tape correctly:
- For pit_to_pit, read the number on the tape exactly where it meets the FAR armpit seam (the tape usually starts at 0 on the near seam).
- Do NOT report the number at the center of the garment or at the edge of the photo.
- If the far end of the tape is cut off, estimate using the visible portion and garment proportions.

Sanity checks (apply before answering):
- Adult tops: pit_to_pit is usually 17-28 inches; length 24-32 inches.
- If your raw reading for pit_to_pit or length is below 15 inches, you are almost certainly reading a FOLDED garment or the wrong point on the tape. Re-examine and correct (a folded reading must be doubled).
- Only return null if there is no measuring tape at all.

Return ONLY a valid JSON object with these exact keys (numbers in inches).
Do not include markdown formatting (no ```json). Just the raw JSON.
"""


def extract_measurements(
    measurement_photos: list[Path],
    garment_type: str | None = None,
    size: str | None = None,
) -> dict:
    if not measurement_photos:
        return {}

    prompt = MEASUREMENT_EXTRACTION_PROMPT.format(
        garment_type=garment_type or "garment",
        size=size or "unknown",
    )

    app_logger.info(
        f"Extracting measurements from {len(measurement_photos)} photo(s)..."
    )

    # HIGH RESOLUTION: tape numbers need detail (only 1-2 photos, so payload is safe)
    response_text = ask_vision(
        prompt=prompt,
        image_paths=measurement_photos,
        max_tokens=300,
        max_size=1000,
        quality=70,
    )

    clean_text = re.sub(r"```json|```", "", response_text).strip()

    try:
        extracted = json.loads(clean_text)
    except json.JSONDecodeError as e:
        app_logger.error(
            f"Failed to parse Measurement JSON response: {e}\nRaw text: {response_text}"
        )
        return {}

    # Warn on suspicious values so the user double-checks in the dashboard
    try:
        p2p = extracted.get("pit_to_pit")
        if p2p is not None and float(p2p) < 15:
            app_logger.warning(
                f"Suspicious pit_to_pit={p2p}in — please double-check in the dashboard."
            )
    except (TypeError, ValueError):
        pass

    return extracted
