import pytest
from PIL import Image
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from src.automate import llm_ocr, rapidocr
from src.automate.llm_ocr import vision_agent
from src.automate.pipeline import extract_totals_with_fallback
from src.automate.rapidocr import OcrTotals


def fake_llm(*replies):
    """FunctionModel answering each call with the next (net, vat, gross) reply."""
    it = iter(replies)

    def respond(messages, info):
        net, vat, gross = next(it)
        args = {"total_net": net, "total_vat": vat, "total_gross": gross}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, args)])

    return FunctionModel(respond)


@pytest.fixture
def blank(tmp_path):
    img = tmp_path / "blank.png"
    Image.new("RGB", (200, 100), "white").save(img)
    return img


def test_tier1_failure_escalates_to_vision(blank):
    with vision_agent().override(model=fake_llm((100, 10, 110))):
        t = extract_totals_with_fallback(blank)
    assert not isinstance(t, OcrTotals) and t.total_gross == 110


def test_vision_checksum_failure_raises_without_retry(blank):
    with (
        vision_agent().override(model=fake_llm((100, 10, 999), (100, 10, 110))),
        pytest.raises(ValueError, match="checksum"),
    ):
        extract_totals_with_fallback(blank)


def test_tier1_success_skips_vision(monkeypatch):
    monkeypatch.setattr(
        rapidocr,
        "extract_totals",
        lambda _: OcrTotals(total_net=1, total_vat=1, total_gross=2, confidence=0.9),
    )
    monkeypatch.setattr(llm_ocr, "extract_totals_vision", lambda _: pytest.fail("Tier 2 called"))
    assert isinstance(extract_totals_with_fallback("x"), OcrTotals)
