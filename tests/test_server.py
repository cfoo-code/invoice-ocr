from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from src.automate.ocr import vision_agent
from src.server import app
from tests.test_ocr_fallback import fake_llm

client = TestClient(app)


def _png(tmp_path, text):
    img = tmp_path / "inv.png"
    im = Image.new("RGB", (900, 120), "white")
    ImageDraw.Draw(im).text((10, 40), text, fill="black", font=ImageFont.load_default(size=28))
    im.save(img)
    return img.read_bytes()


def test_ocr_endpoint(tmp_path):
    r = client.post("/automate/ocr", content=_png(tmp_path, "Total  $ 100,00  $ 10,00  $ 110,00"))
    assert r.status_code == 200
    assert (r.json()["total_net"], r.json()["total_gross"]) == (100.0, 110.0)

    bad = _png(tmp_path, "Total  $ 100,00  $ 10,00  $ 999,00")
    with vision_agent().override(model=fake_llm(*[(100, 10, 999)] * 5)):
        r = client.post("/automate/ocr", content=bad)
    assert r.status_code == 422 and "Tier 2" in r.json()["detail"]

    assert client.post("/automate/ocr", content=b"").status_code == 400
