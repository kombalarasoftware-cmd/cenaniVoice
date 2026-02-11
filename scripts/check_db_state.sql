-- Check DB state and apply role_permissions if needed
SELECT 'alembic_version' as check_type, version_num FROM alembic_version;
SELECT 'is_approved_exists' as check_type, COUNT(*) as cnt FROM information_schema.columns WHERE table_name='users' AND column_name='is_approved';
SELECT 'role_permissions_exists' as check_type, COUNT(*) as cnt FROM information_schema.tables WHERE table_name='role_permissions';
