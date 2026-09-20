import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.ai.vision_client import ask_vision


def main() -> int:
    temp_image = PROJECT_ROOT / "temp" / "vision_test.jpg"
    temp_image.parent.mkdir(parents=True, exist_ok=True)

    Image.new("RGB", (400, 300), color=(200, 30, 30)).save(temp_image, format="JPEG")

    try:
        answer = ask_vision(
            prompt=(
                "What is the dominant color of this image? " "Reply with one word."
            ),
            image_paths=[temp_image],
        )

        print("Claude Vision responded:")
        print(answer)
        print("\nVision connection test passed.")
        return 0

    except Exception as exc:
        print(f"\nVision connection test failed: {exc}")
        return 1

    finally:
        if temp_image.exists():
            temp_image.unlink()


if __name__ == "__main__":
    raise SystemExit(main())
