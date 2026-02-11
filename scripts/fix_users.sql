-- Transfer all FK references from user 1 to user 2
UPDATE agents SET owner_id = 2 WHERE owner_id = 1;
UPDATE campaigns SET owner_id = 2 WHERE owner_id = 1;
UPDATE prompt_templates SET owner_id = 2 WHERE owner_id = 1;

-- Check enum values
SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'userrole');

-- Make users 2 and 3 ADMIN (use correct enum case)
UPDATE users SET role = 'ADMIN' WHERE id IN (2, 3);

-- Check other FK references to user 1
SELECT conname, conrelid::regclass FROM pg_constraint WHERE confrelid = 'users'::regclass;

-- Verify before delete
SELECT id, email, role FROM users ORDER BY id;
