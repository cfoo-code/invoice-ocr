"""FastAPI service. Run: uvicorn src.server:app"""

import asyncio
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from langfuse import Langfuse
from langfuse.span_filter import is_default_export_span
from pydantic_ai import Agent

from src.automate import Totals
from src.automate.pipeline import extract_totals_with_fallback
from src.automate.rapidocr import OcrTotals


def init_langfuse(**kwargs) -> Langfuse:
    """Export pipeline spans (tracers named src.*) and Pydantic AI LLM spans to Langfuse."""
    client = Langfuse(
        should_export_span=lambda s: (
            is_default_export_span(s) or s.instrumentation_scope.name.startswith("src.")
        ),
        **kwargs,
    )
    Agent.instrument_all()
    return client


# No key -> spans stay in the no-op OTel provider: nothing exported, nothing logged.
if os.getenv("LANGFUSE_PUBLIC_KEY"):
    init_langfuse()

app = FastAPI(title="Finago AI Copilot")
MAX_IMAGE_BYTES = 10 * 1024 * 1024


@app.post("/automate/ocr")
async def automate_ocr(request: Request) -> OcrTotals | Totals:
    """Raw image bytes -> totals. Tier 1 fails -> Tier 2 Vision LLM; both fail -> 422."""
    body = await request.body()
    if not body:
        raise HTTPException(400, "empty body; POST the image bytes")
    if len(body) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"image larger than {MAX_IMAGE_BYTES} bytes")
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "upload"
        image.write_bytes(body)
        try:
            return await asyncio.to_thread(extract_totals_with_fallback, image)
        except ValueError as e:
            raise HTTPException(422, str(e)) from e
