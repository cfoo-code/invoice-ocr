import json

import pytest

from src.db.db import build_db, parse_amount, parse_date


def test_parse_amount_handles_eu_and_us_formats():
    assert parse_amount("$ 1 234,56") == 1234.56
    assert parse_amount("1,234.56") == 1234.56
    assert parse_amount("10%") == 10.0
    assert parse_date("10/18/2014") == "2014-10-18"
    with pytest.raises(ValueError):
        parse_date("garbage")


VALID = {
    "image": "data/invoices/train_000.png",
    "header": {
        "invoice_no": 123,
        "invoice_date": "01/02/2020",
        "seller": "ACME",
        "client": "Bob",
        "seller_tax_id": "111-22-3333",
        "client_tax_id": "444-55-6666",
        "iban": "GB00TEST0000000000",
    },
    "items": {
        "item_desc": "Chair",
        "item_qty": "2,00",
        "item_net_price": "50,00",
        "item_net_worth": "100,00",
        "item_vat": "10%",
        "item_gross_worth": "110,00",
    },
    "summary": {
        "total_net_worth": "$ 100,00",
        "total_vat": "$ 10,00",
        "total_gross_worth": "$ 110,00",
    },
}


def test_build_db_loads_invoices_and_line_items(tmp_path):
    jsonl = tmp_path / "inv.jsonl"
    jsonl.write_text("\n".join(json.dumps(VALID) for _ in range(3)))
    con = build_db(tmp_path / "t.db", jsonl)
    assert con.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 3
    assert con.execute("SELECT COUNT(DISTINCT tenant_id) FROM invoices").fetchone()[0] == 2
    net, vat, gross, date = con.execute(
        "SELECT total_net, total_vat, total_gross, invoice_date FROM invoices LIMIT 1"
    ).fetchone()
    assert (net + vat, gross, date) == (110.0, 110.0, "2020-01-02")
    assert con.execute("SELECT SUM(gross) FROM line_items").fetchone()[0] == 330.0
    assert con.execute("SELECT has_payroll_rights FROM users WHERE id = 1").fetchone()[0] == 1
