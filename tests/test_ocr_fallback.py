import pytest
from PIL import Image
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from src.automate.ocr import (
    OcrTotals,
    VisionTotals,
    extract_totals_with_fallback,
    vision_agent,
)


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
    assert isinstance(t, VisionTotals) and t.total_gross == 110


def test_vision_retries_after_checksum_failure(blank):
    with vision_agent().override(model=fake_llm((100, 10, 999), (100, 10, 110))):
        assert extract_totals_with_fallback(blank).total_gross == 110


def test_vision_still_failing_raises_value_error(blank):
    with (
        vision_agent().override(model=fake_llm(*[(100, 10, 999)] * 5)),
        pytest.raises(ValueError, match="Tier 2"),
    ):
        extract_totals_with_fallback(blank)


def test_tier1_success_skips_vision(monkeypatch):
    from src.automate import ocr

    monkeypatch.setattr(
        ocr,
        "extract_totals",
        lambda _: OcrTotals(total_net=1, total_vat=1, total_gross=2, confidence=0.9),
    )
    monkeypatch.setattr(ocr, "extract_totals_vision", lambda _: pytest.fail("Tier 2 called"))
    assert isinstance(ocr.extract_totals_with_fallback("x"), OcrTotals)
