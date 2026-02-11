-- Stamp alembic to latest and check role_permissions data
UPDATE alembic_version SET version_num = '005_add_role_permissions';
SELECT * FROM alembic_version;
SELECT id, role, permissions, description FROM role_permissions;
