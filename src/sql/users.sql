-- Fake demo data: one user per RBAC case (full, invoices-only, read-only).
INSERT INTO users (id, tenant_id, email, has_payroll_rights, can_create_invoices, approval_limit) VALUES
    (1, 1, 'accountant@nordic.example', 1, 1, 10000.0),
    (2, 1, 'clerk@nordic.example',      0, 1, 1000.0),
    (3, 2, 'viewer@helsinki.example',   0, 0, 0.0);
