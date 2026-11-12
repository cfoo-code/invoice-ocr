"""Shared constants and regex rules."""

import os
import re
from pathlib import Path

# --- Datasets (scripts/download_data.py) ---
DATA_DIR = Path("data")
INVOICE_DATASET = "katanaml-org/invoices-donut-data-v1"
TES_URL = "https://tietoala.fi/wp-content/uploads/2026/09/TES_englanti_2025_korj_2_9_2026.pdf"

# TES section heading: "§ 12  Additional work, overtime and Sunday work" -> ("12", title).
# Title must not start with "." or a digit and has no "." (skips TOC dot leaders / page numbers).
SECTION_RE = re.compile(r"^\s*§\s*(\d+)\s+([^.\d][^.]*?)\s*$")

# --- Ledger db (src/db/db.py) ---
# Order matters: schema first, then seed tables respecting foreign keys.
SQL_FILES = ["schema.sql", "tenants.sql", "users.sql", "gl_accounts.sql"]

# --- Tier-1 OCR (src/automate/ocr.py) ---
OCR_CACHE_DIR = DATA_DIR / "ocr_cache"
MIN_CONFIDENCE = 0.8
CENT = 0.011

# --- Tier-2 Vision LLM fallback (src/automate/ocr.py) ---
VISION_MODEL = os.getenv("VISION_MODEL", "openai:gpt-4o-mini")

# One money amount, captured without the "$": optional "$ ", then digits (spaces allowed as
# thousands separators), then "," or "." and exactly 2 decimals. e.g. "$ 1 234,56" -> "1 234,56".
AMOUNT = r"\$?\s?(\d[\d ]*[.,]\d{2})"
# Donut invoice summary row: "Total" followed by 3 amounts (net, vat, gross),
# e.g. "Total $ 1 234,56 $ 123,45 $ 1 358,01".
TOTALS_RE = re.compile(rf"Total\s+{AMOUNT}\s+{AMOUNT}\s+{AMOUNT}")
