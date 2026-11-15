"""Tier 1 RapidOCR first; any failure escalates to the Tier 2 Vision LLM. All gates live here."""

from pathlib import Path

from src.automate import Totals, llm_ocr, rapidocr
from src.automate.rapidocr import OcrTotals
from src.constants import CENT, MIN_CONFIDENCE


def checksum(t: Totals) -> None:
    """Accounting identity Net + VAT == Gross (±1 cent)."""
    if abs(t.total_net + t.total_vat - t.total_gross) > CENT:
        raise ValueError(f"checksum failed: {t.total_net} + {t.total_vat} != {t.total_gross}")


def tier1_gate(t: OcrTotals) -> None:
    """Checksum plus OCR confidence. An LLM has no calibrated confidence, so Tier 2 skips this."""
    checksum(t)
    if t.confidence < MIN_CONFIDENCE:
        raise ValueError(f"OCR confidence {t.confidence:.2f} < {MIN_CONFIDENCE}")


def extract_totals_with_fallback(image: Path | str) -> OcrTotals | Totals:
    try:
        t = rapidocr.extract_totals(image)
        tier1_gate(t)
        return t
    except ValueError:
        t = llm_ocr.extract_totals_vision(image)
        checksum(t)
        return t
