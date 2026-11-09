"""FastAPI service. Run: uvicorn src.api:app"""

import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request

from src.automate.ocr import OcrTotals, extract_totals

app = FastAPI(title="Finago AI Copilot")
MAX_IMAGE_BYTES = 10 * 1024 * 1024


@app.post("/automate/ocr")
async def automate_ocr(request: Request) -> OcrTotals:
    """Raw image bytes in the body -> Tier-1 totals. Checksum/confidence/no-text failure -> 422."""
    body = await request.body()
    if not body:
        raise HTTPException(400, "empty body; POST the image bytes")
    if len(body) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"image larger than {MAX_IMAGE_BYTES} bytes")
    with tempfile.TemporaryDirectory() as tmp:
        image = Path(tmp) / "upload"
        image.write_bytes(body)
        try:
            return await asyncio.to_thread(extract_totals, image)
        except ValueError as e:  # pydantic ValidationError subclasses ValueError
            raise HTTPException(422, str(e)) from e
