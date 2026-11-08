"""SQLite ledger: schema + deterministic loader from data/invoices.jsonl (katanaml donut gt)."""

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "data/procountor_ledger.db"))
INVOICES_JSONL = Path("data/invoices.jsonl")

SQL_DIR = Path(__file__).parent / "sql"
# Order matters: schema first, then seed tables respecting foreign keys.
SQL_FILES = ["schema.sql", "tenants.sql", "users.sql", "gl_accounts.sql"]


def parse_amount(s) -> float | None:
    """'$ 1 234,56' / '1,234.56' / '10%' -> float. Last , or . followed by 1-2 digits is decimal."""
    if s is None:
        return None
    s = re.sub(r"[^\d,.\-]", "", str(s))
    if not re.search(r"\d", s):
        return None
    m = re.search(r"[.,](\d{1,2})$", s)
    whole, frac = (s[: m.start()], m[1]) if m else (s, "0")
    return float(re.sub(r"[^\d\-]", "", whole) + "." + frac)


def parse_date(s) -> str:
    """Donut dates are US 'MM/DD/YYYY'; store ISO so SQL range filters work."""
    return datetime.strptime(str(s).strip(), "%m/%d/%Y").date().isoformat()


def build_db(db_path: Path = DB_PATH, jsonl: Path = INVOICES_JSONL) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    for f in SQL_FILES:
        con.executescript((SQL_DIR / f).read_text())
    n_tenants = con.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
    for i, line in enumerate(jsonl.read_text().splitlines()):
        rec = json.loads(line)
        h, s = rec.get("header", {}), rec.get("summary", {})
        # ponytail: tenant = row parity; swap for a real seller->tenant mapping if needed.
        tenant_id = i % n_tenants + 1
        date = parse_date(h.get("invoice_date"))
        cur = con.execute(
            "INSERT INTO invoices (tenant_id, invoice_no, direction, seller, client, seller_tax_id,"
            " client_tax_id, iban, invoice_date, posting_date, total_net, total_vat, total_gross,"
            " gl_account, image_path) VALUES (?, ?, 'purchase', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
            " '4000', ?)",
            (tenant_id, str(h.get("invoice_no", "")), h.get("seller"), h.get("client"),
             h.get("seller_tax_id"), h.get("client_tax_id"), h.get("iban"), date, date,
             parse_amount(s.get("total_net_worth")), parse_amount(s.get("total_vat")),
             parse_amount(s.get("total_gross_worth")), rec.get("image")),
        )
        items = rec.get("items", [])
        con.executemany(
            "INSERT INTO line_items (invoice_id, description, qty, unit_net_price, net, vat_pct,"
            " gross) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(cur.lastrowid, it.get("item_desc"), parse_amount(it.get("item_qty")),
              parse_amount(it.get("item_net_price")), parse_amount(it.get("item_net_worth")),
              parse_amount(it.get("item_vat")), parse_amount(it.get("item_gross_worth")))
             for it in (items if isinstance(items, list) else [items])],
        )
    con.commit()
    return con


if __name__ == "__main__":
    con = build_db()
    print(f"invoices: {con.execute('SELECT COUNT(*) FROM invoices').fetchone()[0]} -> {DB_PATH}")
