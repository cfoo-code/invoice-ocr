"""Pydantic models validating one invoices.jsonl record before it is inserted."""

import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, field_validator


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
