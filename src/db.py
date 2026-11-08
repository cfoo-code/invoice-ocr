"""SQLite ledger: schema + deterministic loader from data/invoices.jsonl (katanaml donut gt)."""

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator

# Order matters: schema first, then seed tables respecting foreign keys.
SQL_FILES = ["schema.sql", "tenants.sql", "users.sql", "gl_accounts.sql"]


def get_paths() -> tuple[Path, Path, Path]:
    """(db file, sql scripts dir, invoices jsonl). DB_PATH env var overrides the db file."""
    db_path = Path(os.environ.get("DB_PATH", "data/procountor_ledger.db"))
    return db_path, Path(__file__).parent / "sql", Path("data/invoices.jsonl")


def parse_amount(s) -> float:
    """'$ 1 234,56' / '1,234.56' / '10%' -> float. Last , or . followed by 1-2 digits is decimal."""
    raw, s = s, re.sub(r"[^\d,.\-]", "", str(s))
    if not re.search(r"\d", s):
        raise ValueError(f"not an amount: {raw!r}")
    m = re.search(r"[.,](\d{1,2})$", s)
    whole, frac = (s[: m.start()], m[1]) if m else (s, "0")
    return float(re.sub(r"[^\d\-]", "", whole) + "." + frac)


def parse_date(s) -> str:
    """Donut dates are US 'MM/DD/YYYY'; store ISO so SQL range filters work."""
    return datetime.strptime(str(s).strip(), "%m/%d/%Y").date().isoformat()


Amount = Annotated[float, BeforeValidator(parse_amount)]
IsoDate = Annotated[str, BeforeValidator(parse_date)]


class Record(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)


class Header(Record):
    invoice_no: str
    invoice_date: IsoDate
    seller: str
    client: str
    seller_tax_id: str | None = None
    client_tax_id: str | None = None
    iban: str | None = None


class Summary(Record):
    total_net_worth: Amount
    total_vat: Amount
    total_gross_worth: Amount


class Item(Record):
    item_desc: str
    item_qty: Amount
    item_net_price: Amount
    item_net_worth: Amount
    item_vat: Amount
    item_gross_worth: Amount


class InvoiceRecord(Record):
    image: str
    header: Header
    summary: Summary
    items: list[Item]

    @field_validator("items", mode="before")
    @classmethod
    def wrap_single_item(cls, v):
        return v if isinstance(v, list) else [v]


def create_db(db_path: Path, sql_dir: Path) -> sqlite3.Connection:
    """Fresh db file with schema and fake seed tables."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)
    con = sqlite3.connect(db_path)
    for f in SQL_FILES:
        con.executescript((sql_dir / f).read_text())
    return con


def insert_invoice(con: sqlite3.Connection, rec: InvoiceRecord, tenant_id: int) -> int:
    h, s = rec.header, rec.summary
    cur = con.execute(
        "INSERT INTO invoices (tenant_id, invoice_no, direction, seller, client, seller_tax_id,"
        " client_tax_id, iban, invoice_date, posting_date, total_net, total_vat, total_gross,"
        " gl_account, image_path) VALUES (?, ?, 'purchase', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,"
        " '4000', ?)",
        (tenant_id, h.invoice_no, h.seller, h.client, h.seller_tax_id, h.client_tax_id, h.iban,
         h.invoice_date, h.invoice_date, s.total_net_worth, s.total_vat, s.total_gross_worth,
         rec.image),
    )
    return cur.lastrowid


def insert_line_items(con: sqlite3.Connection, invoice_id: int, items: list[Item]) -> None:
    con.executemany(
        "INSERT INTO line_items (invoice_id, description, qty, unit_net_price, net, vat_pct,"
        " gross) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(invoice_id, it.item_desc, it.item_qty, it.item_net_price, it.item_net_worth,
          it.item_vat, it.item_gross_worth) for it in items],
    )


def build_db(db_path: Path | None = None, jsonl: Path | None = None) -> sqlite3.Connection:
    default_db, sql_dir, default_jsonl = get_paths()
    con = create_db(db_path or default_db, sql_dir)
    n_tenants = con.execute("SELECT COUNT(*) FROM tenants").fetchone()[0]
    for i, line in enumerate((jsonl or default_jsonl).read_text().splitlines()):
        rec = InvoiceRecord.model_validate_json(line)
        # ponytail: tenant = row parity; swap for a real seller->tenant mapping if needed.
        invoice_id = insert_invoice(con, rec, tenant_id=i % n_tenants + 1)
        insert_line_items(con, invoice_id, rec.items)
    con.commit()
    return con


if __name__ == "__main__":
    con = build_db()
    n = con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    print(f"invoices: {n} -> {get_paths()[0]}")
