"""Tier-1 document understanding: local RapidOCR + accounting checksum gate (Net + VAT == Gross)."""

import hashlib
import json
from functools import cache
from pathlib import Path

from pydantic import BaseModel, model_validator
from rapidocr_onnxruntime import RapidOCR

from src.constants import CENT, MIN_CONFIDENCE, OCR_CACHE_DIR, TOTALS_RE
from src.db.db import parse_amount


def checksum(net: float, vat: float, gross: float) -> None:
    """Accounting identity Net + VAT == Gross (±1 cent). Shared by Tier 1 and Tier 2."""
    if abs(net + vat - gross) > CENT:
        raise ValueError(f"checksum failed: {net} + {vat} != {gross}")


class OcrTotals(BaseModel):
    """Raises ValidationError when the checksum or confidence gate fails -> escalate to Tier 2."""

    total_net: float
    total_vat: float
    total_gross: float
    confidence: float

    @model_validator(mode="after")
    def check_checksum(self):
        checksum(self.total_net, self.total_vat, self.total_gross)
        return self

    @model_validator(mode="after")
    def check_confidence(self):
        if self.confidence < MIN_CONFIDENCE:
            raise ValueError(f"OCR confidence {self.confidence:.2f} < {MIN_CONFIDENCE}")
        return self


@cache
def _engine() -> RapidOCR:
    return RapidOCR()


def ocr_boxes(image: Path | str) -> list:
    """RapidOCR boxes [corner_points, text, confidence], cached as JSON keyed by image sha256."""
    cache = OCR_CACHE_DIR / f"{hashlib.sha256(Path(image).read_bytes()).hexdigest()}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))["boxes"]
    boxes = _engine()(str(image))[0] or []
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"image": str(image), "boxes": boxes}, default=float), "utf-8")
    return boxes


def ocr_text(image: Path | str) -> tuple[str, float]:
    """(text lines joined by newline, mean box confidence). No text detected -> ValueError."""
    boxes = ocr_boxes(image)
    if not boxes:
        raise ValueError(f"OCR found no text in {image}")
    text = "\n".join(text for _, text, _ in boxes)
    mean_confidence = sum(conf for _, _, conf in boxes) / len(boxes)
    return text, mean_confidence


def parse_totals(text: str, confidence: float) -> OcrTotals:
    """Last 'Total' row wins (summary sits at the bottom). No match -> ValueError."""
    matches = TOTALS_RE.findall(" ".join(text.split()))
    if not matches:
        raise ValueError("no totals row found in OCR text")
    net, vat, gross = map(parse_amount, matches[-1])
    return OcrTotals(total_net=net, total_vat=vat, total_gross=gross, confidence=confidence)


def extract_totals(image: Path | str) -> OcrTotals:
    text, mean_confidence = ocr_text(image)
    return parse_totals(text, mean_confidence)
