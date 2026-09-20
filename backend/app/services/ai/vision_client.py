import base64
import io
import os
import time
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv
from PIL import Image

from backend.app.core.logging import app_logger

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-4-5"
_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not found. Add it to the .env file.")
        _client = Anthropic(api_key=api_key, timeout=120.0)
    return _client


def image_to_content_block(path: Path, max_size: int = 400, quality: int = 40) -> dict:
    """Convert a local image into an Anthropic vision content block."""
    with Image.open(path) as img:
        if img.mode != "RGB":
            img = img.convert("RGB")

        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality, optimize=True)
        raw_bytes = buffer.getvalue()

    print(f"  - Prepared {path.name}: {len(raw_bytes) / 1024:.1f} KB")

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": base64.standard_b64encode(raw_bytes).decode("utf-8"),
        },
    }


def ask_vision(
    prompt: str,
    image_paths: list[Path],
    model: str | None = None,
    max_tokens: int = 1024,
    max_size: int = 400,
    quality: int = 40,
) -> str:
    """Send images plus a prompt to Claude and return the text reply."""
    model = model or os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)

    content = [
        image_to_content_block(p, max_size=max_size, quality=quality)
        for p in image_paths
    ]
    content.append({"type": "text", "text": prompt})

    app_logger.info(f"Sending {len(image_paths)} image(s) to {model}")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = get_client().messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": content}],
            )
            return response.content[0].text
        except Exception as e:
            if attempt < max_retries - 1:
                print(
                    f"  ⚠️ Network hiccup ({type(e).__name__}). Retrying in 3 seconds..."
                )
                time.sleep(3)
            else:
                app_logger.error("Max retries reached. Connection failed.")
                raise e
