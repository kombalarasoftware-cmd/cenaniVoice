-- Seed default role permissions with updated_at
INSERT INTO role_permissions (role, permissions, description, updated_at) VALUES
('ADMIN', '{"dashboard":true,"agents":true,"campaigns":true,"numbers":true,"recordings":true,"call_logs":true,"appointments":true,"leads":true,"surveys":true,"reports":true,"settings":true}', 'Full access to all pages and features', NOW()),
('OPERATOR', '{"dashboard":true,"agents":true,"campaigns":true,"numbers":true,"recordings":true,"call_logs":true,"appointments":true,"leads":true,"surveys":true,"reports":true,"settings":true}', 'Standard operator access', NOW())
ON CONFLICT (role) DO NOTHING;
SELECT id, role, description FROM role_permissions;
