"""Tier 1 RapidOCR first; any failure escalates to the Tier 2 Vision LLM."""

from pathlib import Path

from src.automate import llm_ocr, rapidocr
from src.automate.llm_ocr import VisionTotals
from src.automate.rapidocr import OcrTotals


def extract_totals_with_fallback(image: Path | str) -> OcrTotals | VisionTotals:
    try:
        return rapidocr.extract_totals(image)
    except ValueError:
        return llm_ocr.extract_totals_vision(image)
