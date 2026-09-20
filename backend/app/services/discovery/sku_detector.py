import re
from dataclasses import asdict, dataclass
from pathlib import Path

import easyocr

from backend.app.core.logging import app_logger

SKU_PATTERN = re.compile(r"\b0\d{4}\b")


_reader: easyocr.Reader | None = None


def get_reader() -> easyocr.Reader:
    """Create the OCR reader only when an image actually needs scanning.

    EasyOCR loads its model during construction. Deferring that work keeps the
    discovery package fast to import and lets the grouping code be tested
    without requiring OCR model files.
    """
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False)
    return _reader


@dataclass
class SKUResult:
    sku: str
    confidence: float
    status: str
    source: str
    raw_text: str = ""

    def __str__(self) -> str:
        return (
            f"SKUResult(sku={self.sku}, confidence={self.confidence:.2f}, "
            f"status={self.status}, source={self.source}, raw_text={self.raw_text!r})"
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SKUResult":
        return cls(
            sku=data.get("sku", "00000"),
            confidence=float(data.get("confidence", 0.0)),
            status=data.get("status", "manual_review"),
            source=data.get("source", "unknown"),
            raw_text=data.get("raw_text", ""),
        )

    def is_valid(self) -> bool:
        return bool(SKU_PATTERN.fullmatch(self.sku))

    def requires_manual_review(self) -> bool:
        return self.status in {"manual_review", "error", "ocr_failed"}


def validate_sku(text: str) -> SKUResult:

    matches = SKU_PATTERN.findall(text)

    if matches:
        return SKUResult(
            sku=matches[0],
            confidence=1.0,
            status="confirmed",
            source="ocr",
            raw_text=text,
        )

    return SKUResult(
        sku="00000",
        confidence=0.0,
        status="manual_review",
        source="ocr_failed",
        raw_text=text,
    )


def detect_sku(image_path: Path) -> SKUResult:

    app_logger.info(f"Scanning SKU image: {image_path.name}")

    try:
        results = get_reader().readtext(str(image_path))

        extracted = " ".join([item[1] for item in results])

        app_logger.info(f"OCR text: {extracted}")

        return validate_sku(extracted)

    except Exception as e:
        app_logger.error(f"OCR failed: {e}")

        return SKUResult(
            sku="00000", confidence=0, status="error", source="exception", raw_text=""
        )
