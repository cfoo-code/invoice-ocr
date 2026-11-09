"""Tier-1 OCR vs ledger ground truth. Usage: python scripts/eval_ocr.py [N]"""

import sqlite3
import sys

from pydantic import ValidationError

from src.automate.ocr import ocr_text, parse_totals
from src.constants import CENT
from src.db.db import get_paths

n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
rows = (
    sqlite3.connect(get_paths()[0])
    .execute(
        "SELECT image_path, total_net, total_vat, total_gross FROM invoices ORDER BY id LIMIT ?",
        (n,),
    )
    .fetchall()
)

stats = {"exact": 0, "wrong": 0, "gate_failed": 0, "no_totals": 0}
print(f"{'image':<26}{'truth net/vat/gross':<32}{'ocr net/vat/gross':<32}result")
for img, *truth in rows:
    try:
        text, conf = ocr_text(img)
        o = parse_totals(text, conf)
        got = [o.total_net, o.total_vat, o.total_gross]
        result = "exact" if all(abs(a - b) <= CENT for a, b in zip(got, truth)) else "wrong"
    except ValidationError as e:
        got, result = "-", "gate_failed"
        detail = e.errors()[0]["msg"]
    except ValueError:
        got, result = "-", "no_totals"
    stats[result] += 1
    line = f"{img.split(chr(92))[-1].split('/')[-1]:<26}{truth!s:<32}{got!s:<32}{result}"
    print(line + (f" ({detail})" if result == "gate_failed" else ""))

print("\n", {k: f"{v}/{len(rows)}" for k, v in stats.items()})
