from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from src.api import app

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

    r = client.post("/automate/ocr", content=_png(tmp_path, "Total  $ 100,00  $ 10,00  $ 999,00"))
    assert r.status_code == 422 and "checksum" in r.json()["detail"]

    assert client.post("/automate/ocr", content=b"").status_code == 400
