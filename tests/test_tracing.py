from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from src.automate.llm_ocr import vision_agent
from src.automate.pipeline import extract_totals_with_fallback
from src.server import init_langfuse
from tests.test_ocr_fallback import blank, fake_llm  # noqa: F401  (blank is a fixture)


def test_escalation_is_one_trace_with_tier_spans(blank):  # noqa: F811
    exporter = InMemorySpanExporter()
    langfuse = init_langfuse(
        public_key="pk-test",
        secret_key="sk-test",
        base_url="http://127.0.0.1:9",
        span_exporter=exporter,
    )
    with vision_agent().override(model=fake_llm((100, 10, 110))):
        extract_totals_with_fallback(blank)
    langfuse.flush()

    spans = {s.name: s for s in exporter.get_finished_spans()}
    assert {"ocr_pipeline", "tier1_rapidocr", "invoke_agent agent"} <= spans.keys()
    assert spans["ocr_pipeline"].attributes["ocr.tier"] == 2
    assert len({s.context.trace_id for s in spans.values()}) == 1
