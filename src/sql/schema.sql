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
