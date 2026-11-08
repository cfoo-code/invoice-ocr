"""Fetch the public datasets: katanaml B2B invoices + Finnish IT sector TES 2025-2027."""

import io
import json
import re
import urllib.request
from pathlib import Path

DATA_DIR = Path("data")
INVOICE_DATASET = "katanaml-org/invoices-donut-data-v1"
TES_URL = "https://tietoala.fi/wp-content/uploads/2026/09/TES_englanti_2025_korj_2_9_2026.pdf"

# "§ 12  Additional work, overtime and Sunday work" without TOC dot leaders / page numbers.
SECTION_RE = re.compile(r"^\s*§\s*(\d+)\s+([^.\d][^.]*?)\s*$")


def download_invoices(data_dir: Path = DATA_DIR) -> int:
    from datasets import load_dataset

    img_dir = data_dir / "invoices"
    img_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(data_dir / "invoices.jsonl", "w") as out:
        for split, rows in load_dataset(INVOICE_DATASET).items():
            for i, row in enumerate(rows):
                image_path = img_dir / f"{split}_{i:03d}.png"
                row["image"].save(image_path)
                gt = json.loads(row["ground_truth"])["gt_parse"]
                out.write(json.dumps({"image": str(image_path), **gt}) + "\n")
                n += 1
    return n


def tes_text_to_markdown(text: str) -> str:
    lines = [
        f"# Collective Agreement of the IT Service Sector in Finland 2025-2027\n\nSource: {TES_URL}\n"
    ]
    for line in text.splitlines():
        m = SECTION_RE.match(line)
        lines.append(f"\n## § {m[1]} {m[2]}\n" if m else line.rstrip())
    return "\n".join(lines) + "\n"


def download_tes(data_dir: Path = DATA_DIR) -> Path:
    from pypdf import PdfReader

    with urllib.request.urlopen(TES_URL, timeout=60) as resp:
        pdf = PdfReader(io.BytesIO(resp.read()))
    out = data_dir / "finnish_it_tes_2025_2027.md"
    data_dir.mkdir(parents=True, exist_ok=True)
    out.write_text(tes_text_to_markdown("\n".join(p.extract_text() for p in pdf.pages)))
    return out


if __name__ == "__main__":
    print(f"invoices: {download_invoices()}")
    print(f"tes: {download_tes()}")
