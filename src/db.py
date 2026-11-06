"""SQLite ledger: schema + deterministic loader from data/invoices.jsonl (katanaml donut gt)."""

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.environ.get("DB_PATH", "data/procountor_ledger.db"))
INVOICES_JSONL = Path("data/invoices.jsonl")

SCHEMA = """
CREATE TABLE tenants (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    email TEXT NOT NULL UNIQUE,
    has_payroll_rights INTEGER NOT NULL DEFAULT 0,
    can_create_invoices INTEGER NOT NULL DEFAULT 0,
    approval_limit REAL NOT NULL DEFAULT 0
);
CREATE TABLE gl_accounts (code TEXT PRIMARY KEY, name TEXT NOT NULL);
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    invoice_no TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('sales', 'purchase')),
    seller TEXT, client TEXT, seller_tax_id TEXT, client_tax_id TEXT, iban TEXT,
    invoice_date TEXT, posting_date TEXT,
    total_net REAL, total_vat REAL, total_gross REAL,
    gl_account TEXT REFERENCES gl_accounts(code),
    status TEXT NOT NULL DEFAULT 'POSTED',
    image_path TEXT
);
CREATE TABLE line_items (
    id INTEGER PRIMARY KEY,
    invoice_id INTEGER NOT NULL REFERENCES invoices(id),
    description TEXT, qty REAL, unit_net_price REAL,
    net REAL, vat_pct REAL, gross REAL
);
CREATE INDEX ix_invoices_tenant_date ON invoices(tenant_id, invoice_date);
"""

TENANTS = [(1, "Nordic Demo Oy"), (2, "Helsinki Consulting Oy")]
USERS = [
    (1, 1, "accountant@nordic.example", 1, 1, 10000.0),
    (2, 1, "clerk@nordic.example", 0, 1, 1000.0),
    (3, 2, "viewer@helsinki.example", 0, 0, 0.0),
]
GL_ACCOUNTS = [
    ("3000", "Sales revenue"),
    ("4000", "Purchases of goods"),
    ("7600", "Other operating expenses"),
]


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


def parse_date(s) -> str | None:
    """Donut dates are US 'MM/DD/YYYY'; store ISO so SQL range filters work."""
    try:
        return datetime.strptime(str(s).strip(), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return None


def build_db(db_path: Path = DB_PATH, jsonl: Path = INVOICES_JSONL) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO tenants VALUES (?, ?)", TENANTS)
    con.executemany("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", USERS)
    con.executemany("INSERT INTO gl_accounts VALUES (?, ?)", GL_ACCOUNTS)
    for i, line in enumerate(jsonl.read_text().splitlines()):
        rec = json.loads(line)
        h, s = rec.get("header", {}), rec.get("summary", {})
        # ponytail: tenant = row parity; swap for a real seller->tenant mapping if needed.
        tenant_id = i % len(TENANTS) + 1
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
