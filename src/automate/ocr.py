"""Tier-1 document understanding: local RapidOCR + accounting checksum gate (Net + VAT == Gross)."""

import re
from functools import cache
from pathlib import Path

from pydantic import BaseModel, model_validator
from rapidocr_onnxruntime import RapidOCR

from src.db.db import parse_amount

MIN_CONFIDENCE = 0.8
CENT = 0.011

# One money amount, captured without the "$": optional "$ ", then digits (spaces allowed as
# thousands separators), then "," or "." and exactly 2 decimals. e.g. "$ 1 234,56" -> "1 234,56".
AMOUNT = r"\$?\s?(\d[\d ]*[.,]\d{2})"
# Donut invoice summary row: "Total" followed by 3 amounts (net, vat, gross),
# e.g. "Total $ 1 234,56 $ 123,45 $ 1 358,01".
TOTALS_RE = re.compile(rf"Total\s+{AMOUNT}\s+{AMOUNT}\s+{AMOUNT}")


class OcrTotals(BaseModel):
    """Raises ValidationError when the checksum or confidence gate fails -> escalate to Tier 2."""

    total_net: float
    total_vat: float
    total_gross: float
    confidence: float

    @model_validator(mode="after")
    def checksum(self):
        if abs(self.total_net + self.total_vat - self.total_gross) > CENT:
            raise ValueError(
                f"checksum failed: {self.total_net} + {self.total_vat} != {self.total_gross}"
            )
        if self.confidence < MIN_CONFIDENCE:
            raise ValueError(f"OCR confidence {self.confidence:.2f} < {MIN_CONFIDENCE}")
        return self


@cache
def _engine() -> RapidOCR:
    return RapidOCR()


def ocr_text(image: Path | str) -> tuple[str, float]:
    """(text lines joined by newline, mean box confidence). No text detected -> ValueError."""
    # One box per detected text region: [corner_points, text, confidence]; None if no text.
    boxes, _ = _engine()(str(image))
    if not boxes:
        raise ValueError(f"OCR found no text in {image}")
    text = "\n".join(text for _, text, _ in boxes)
    return text, sum(conf for _, _, conf in boxes) / len(boxes)


def parse_totals(text: str, confidence: float) -> OcrTotals:
    """Last 'Total' row wins (summary sits at the bottom). No match -> ValueError."""
    matches = TOTALS_RE.findall(" ".join(text.split()))
    if not matches:
        raise ValueError("no totals row found in OCR text")
    net, vat, gross = map(parse_amount, matches[-1])
    return OcrTotals(total_net=net, total_vat=vat, total_gross=gross, confidence=confidence)


def extract_totals(image: Path | str) -> OcrTotals:
    return parse_totals(*ocr_text(image))
