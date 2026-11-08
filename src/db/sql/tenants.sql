-- Fake demo data. Tenant: a customer company using the accounting system. Every invoice
-- belongs to one tenant, and one tenant must never see another tenant's data.
INSERT INTO tenants (id, name) VALUES
    (1, 'Nordic Demo Oy'),
    (2, 'Helsinki Consulting Oy');
