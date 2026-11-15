"""Tier 2: Vision LLM reads the totals row."""

import io
from functools import cache
from pathlib import Path

from PIL import Image
from pydantic_ai import Agent, BinaryContent

from src.automate import Totals
from src.constants import VISION_MODEL


@cache
def vision_agent() -> Agent[None, Totals]:
    return Agent(
        VISION_MODEL,
        output_type=Totals,
        instructions="Read the invoice summary 'Total' row: net amount, VAT, gross amount.",
        defer_model_check=True,
    )


def extract_totals_vision(image: Path | str) -> Totals:
    """Single attempt; the checksum is applied by pipeline.py."""
    data = Path(image).read_bytes()
    media_type = Image.MIME[Image.open(io.BytesIO(data)).format]
    return vision_agent().run_sync([BinaryContent(data, media_type=media_type)]).output
