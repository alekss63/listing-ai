from pathlib import Path
from datetime import datetime

from PIL import Image

from backend.app.core.paths import PICTURES
from backend.app.core.logging import app_logger


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".avif",
    ".heic",
    ".webp",
    ".tiff",
    ".tif",
}


class ImageFile:
    def __init__(
        self,
        path: Path,
        created: datetime,
        width: int | None = None,
        height: int | None = None,
    ):
        self.path = path
        self.created = created
        self.width = width
        self.height = height

    def __repr__(self) -> str:
        return (
            f"ImageFile("
            f"name={self.path.name}, "
            f"created={self.created}, "
            f"size={self.width}x{self.height}"
            f")"
        )


def get_image_timestamp(path: Path) -> datetime:
    """
    Priority:
    1. EXIF DateTimeOriginal
    2. File creation time fallback
    """
    try:
        with Image.open(path) as img:
            exif = img.getexif()

            # DateTimeOriginal tag
            date = exif.get(36867)

            if date:
                return datetime.strptime(
                    date,
                    "%Y:%m:%d %H:%M:%S",
                )

    except Exception:
        pass

    stat_result = path.stat()

    # st_birthtime exists on macOS/Windows.
    # On Linux, fall back to st_mtime.
    timestamp = getattr(
        stat_result,
        "st_birthtime",
        stat_result.st_mtime,
    )

    return datetime.fromtimestamp(timestamp)


def scan_images() -> list[ImageFile]:
    """
    Recursively scan the Pictures folder for supported image files.
    """
    if not PICTURES.exists():
        app_logger.error(
            f"Pictures folder missing: {PICTURES}"
        )
        return []

    images: list[ImageFile] = []

    for file in PICTURES.rglob("*"):
        if not file.is_file():
            continue

        if file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            with Image.open(file) as img:
                width, height = img.size

            images.append(
                ImageFile(
                    path=file,
                    created=get_image_timestamp(file),
                    width=width,
                    height=height,
                )
            )

        except Exception as exc:
            app_logger.warning(
                f"Cannot read image {file}: {exc}"
            )

    images.sort(key=lambda image: image.created)

    return images