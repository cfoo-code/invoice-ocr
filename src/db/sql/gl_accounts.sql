-- Fake demo data. GL account: a general ledger account, a category in the chart of accounts
-- that every transaction is booked to. Used to build the profit-and-loss statement and balance sheet.
INSERT INTO gl_accounts (code, name) VALUES
    ('3000', 'Sales revenue'),
    ('4000', 'Purchases of goods'),
    ('7600', 'Other operating expenses');
