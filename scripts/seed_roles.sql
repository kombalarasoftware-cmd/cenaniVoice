-- Seed default role permissions
INSERT INTO role_permissions (role, permissions, description) VALUES
('ADMIN', '{"dashboard":true,"agents":true,"campaigns":true,"numbers":true,"recordings":true,"call_logs":true,"appointments":true,"leads":true,"surveys":true,"reports":true,"settings":true}', 'Full access to all pages and features'),
('OPERATOR', '{"dashboard":true,"agents":true,"campaigns":true,"numbers":true,"recordings":true,"call_logs":true,"appointments":true,"leads":true,"surveys":true,"reports":true,"settings":true}', 'Standard operator access')
ON CONFLICT (role) DO NOTHING;
SELECT id, role, description FROM role_permissions;
