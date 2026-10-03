import json
import re
from pathlib import Path

from backend.app.core.logging import app_logger
from backend.app.services.ai.vision_client import ask_vision

CONDITION_PROMPT = """You are an expert e-commerce condition grader for resale clothing.
IMPORTANT CONTEXT: these garments come from retail store displays / overstock. They must be assumed NEW unless there is clear evidence otherwise.

Determine the condition using these rules, in this exact order:
1. "New with imperfections": ONLY if you see a specific minor defect (stain, hole, missing button, snag, repair). Describe each defect in condition_notes.
2. "Pre-owned": ONLY if you see unambiguous signs of actual wear: pilling, fading, stretched collar or seams, worn labels. Describe the wear in condition_notes.
3. "New without tags, Store Display": the DEFAULT. Wrinkles from storage, fold lines, dust, hanging tags, or flat lighting do NOT count as wear or defects.

When in doubt between "Pre-owned" and "New without tags, Store Display", ALWAYS choose "New without tags, Store Display".

Return ONLY a valid JSON object with these exact keys: "condition", "condition_notes".
Do not include markdown formatting (no ```json). Just the raw JSON.
"""


def assess_condition(photo_paths: list[Path]) -> dict:
    if not photo_paths:
        return {
            "condition": "New without tags, Store Display",
            "condition_notes": "Store display item. No visible wear or defects.",
        }

    batch = photo_paths[:6]
    app_logger.info(f"Assessing condition from {len(batch)} photo(s)...")

    response_text = ask_vision(
        prompt=CONDITION_PROMPT,
        image_paths=batch,
        max_tokens=400,
        max_size=600,
        quality=50,
    )

    clean_text = re.sub(r"```json|```", "", response_text).strip()

    try:
        data = json.loads(clean_text)
        return {
            "condition": data.get("condition") or "New without tags, Store Display",
            "condition_notes": data.get("condition_notes") or "",
        }
    except json.JSONDecodeError as e:
        app_logger.error(f"Failed to parse condition JSON: {e}\nRaw: {response_text}")
        return {
            "condition": "New without tags, Store Display",
            "condition_notes": "",
        }
