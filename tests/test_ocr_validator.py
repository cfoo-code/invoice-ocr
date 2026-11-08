import pytest
from PIL import Image, ImageDraw, ImageFont
from pydantic import ValidationError

from src.automate.ocr import OcrTotals, extract_totals, parse_totals


def test_parse_totals_takes_last_total_row():
    text = "Total $ 1,00 $ 1,00 $ 2,00\nSUMMARY\nTotal $ 1 234,56 $ 123,46\n$ 1 358,02"
    t = parse_totals(text, confidence=0.95)
    assert (t.total_net, t.total_vat, t.total_gross) == (1234.56, 123.46, 1358.02)


def test_checksum_and_confidence_gate():
    OcrTotals(total_net=100, total_vat=10, total_gross=110.01, confidence=0.9)
    with pytest.raises(ValidationError, match="checksum"):
        OcrTotals(total_net=100, total_vat=10, total_gross=111, confidence=0.9)
    with pytest.raises(ValidationError, match="confidence"):
        OcrTotals(total_net=100, total_vat=10, total_gross=110, confidence=0.5)
    with pytest.raises(ValueError, match="no totals"):
        parse_totals("illegible", confidence=0.9)


def test_blank_image_raises(tmp_path):
    img = tmp_path / "blank.png"
    Image.new("RGB", (200, 100), "white").save(img)
    with pytest.raises(ValueError, match="no text"):
        extract_totals(img)


def test_extract_totals_from_rendered_image(tmp_path):
    img = tmp_path / "inv.png"
    im = Image.new("RGB", (900, 120), "white")
    ImageDraw.Draw(im).text(
        (10, 40),
        "Total  $ 100,00  $ 10,00  $ 110,00",
        fill="black",
        font=ImageFont.load_default(size=28),
    )
    im.save(img)
    t = extract_totals(img)
    assert (t.total_net, t.total_vat, t.total_gross) == (100.0, 10.0, 110.0)
