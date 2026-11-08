"""SQLite ledger: schema + deterministic loader from data/invoices.jsonl (katanaml donut gt)."""

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

# Order matters: schema first, then seed tables respecting foreign keys.
SQL_FILES = ["schema.sql", "tenants.sql", "users.sql", "gl_accounts.sql"]


def get_paths() -> tuple[Path, Path, Path]:
    """(db file, sql scripts dir, invoices jsonl). DB_PATH env var overrides the db file."""
    db_path = Path(os.environ.get("DB_PATH", "data/procountor_ledger.db"))
    sql_dir = Path(__file__).parent / "sql"
    invoices_jsonl = Path("data/invoices.jsonl")
    return db_path, sql_dir, invoices_jsonl


def parse_amount(s) -> float:
    """'$ 1 234,56' / '1,234.56' / '10%' -> float. Last , or . followed by 1-2 digits is decimal."""
    digits = re.sub(r"[^\d,.\-]", "", str(s))
    decimal_part = re.search(r"[.,](\d{1,2})$", digits)
    whole, frac = (
        (digits[: decimal_part.start()], decimal_part[1]) if decimal_part else (digits, "0")
    )
    return float(re.sub(r"[^\d\-]", "", whole) + "." + frac)


def parse_date(s) -> str:
    """Donut dates are US 'MM/DD/YYYY'; store ISO so SQL range filters work."""
    return datetime.strptime(str(s).strip(), "%m/%d/%Y").date().isoformat()


def create_db(db_path: Path, sql_dir: Path) -> sqlite3.Connection:
    """Fresh db file with schema and fake seed tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    for f in SQL_FILES:
        con.executescript((sql_dir / f).read_text())
    return con


def insert_invoice(con: sqlite3.Connection, rec: dict, tenant_id: int) -> int:
    h, s = rec["header"], rec["summary"]
    date = parse_date(h["invoice_date"])
    cur = con.execute(
        "INSERT INTO invoices (tenant_id, invoice_no, direction, seller, client, seller_tax_id,"
        " client_tax_id, iban, invoice_date, posting_date, total_net, total_vat, total_gross,"
        " gl_account, image_path) VALUES (?, ?, 'purchase', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
        " '4000', ?)",
        (tenant_id, str(h["invoice_no"]), h["seller"], h["client"], h["seller_tax_id"],
         h["client_tax_id"], h["iban"], date, date, parse_amount(s["total_net_worth"]),
         parse_amount(s["total_vat"]), parse_amount(s["total_gross_worth"]), rec["image"]),
    )
    return cur.lastrowid


def insert_line_items(con: sqlite3.Connection, invoice_id: int, items) -> None:
    items = items if isinstance(items, list) else [items]
    con.executemany(
        "INSERT INTO line_items (invoice_id, description, qty, unit_net_price, net, vat_pct,"
        " gross) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(invoice_id, it["item_desc"], parse_amount(it["item_qty"]),
          parse_amount(it["item_net_price"]), parse_amount(it["item_net_worth"]),
          parse_amount(it["item_vat"]), parse_amount(it["item_gross_worth"])) for it in items],
    )


def build_db(db_path: Path | None = None, jsonl: Path | None = None) -> sqlite3.Connection:
    default_db, sql_dir, default_jsonl = get_paths()
    con = create_db(db_path or default_db, sql_dir)
    n_tenants = con.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
    for i, line in enumerate((jsonl or default_jsonl).read_text().splitlines()):
        rec = json.loads(line)
        # ponytail: tenant = row parity; swap for a real seller->tenant mapping if needed.
        invoice_id = insert_invoice(con, rec, tenant_id=i % n_tenants + 1)
        insert_line_items(con, invoice_id, rec["items"])
    con.commit()
    return con


if __name__ == "__main__":
    con = build_db()
    n = con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    print(f"invoices: {n} -> {get_paths()[0]}")
