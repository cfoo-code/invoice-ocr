"""Tier 2: Vision LLM reads the totals; checksum gate only."""

import io
from functools import cache
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, model_validator
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.exceptions import UnexpectedModelBehavior

from src.automate import checksum
from src.constants import VISION_MODEL


class VisionTotals(BaseModel):
    """Checksum only: an LLM has no calibrated confidence to gate on."""

    total_net: float
    total_vat: float
    total_gross: float

    @model_validator(mode="after")
    def check_checksum(self):
        checksum(self.total_net, self.total_vat, self.total_gross)
        return self


@cache
def vision_agent() -> Agent[None, VisionTotals]:
    return Agent(
        VISION_MODEL,
        output_type=VisionTotals,
        instructions="Read the invoice summary 'Total' row: net amount, VAT, gross amount.",
        defer_model_check=True,
    )


def extract_totals_vision(image: Path | str) -> VisionTotals:
    """Checksum failure is fed back to the LLM to retry; still failing -> ValueError."""
    data = Path(image).read_bytes()
    media_type = Image.MIME[Image.open(io.BytesIO(data)).format]
    try:
        return vision_agent().run_sync([BinaryContent(data, media_type=media_type)]).output
    except UnexpectedModelBehavior as e:
        raise ValueError(f"Tier 2 failed: {e}") from e
