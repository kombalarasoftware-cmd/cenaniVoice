-- Transfer ALL FK references from user 1 to user 2
UPDATE number_lists SET owner_id = 2 WHERE owner_id = 1;
UPDATE sip_trunks SET owner_id = 2 WHERE owner_id = 1;
UPDATE webhook_endpoints SET owner_id = 2 WHERE owner_id = 1;
UPDATE api_keys SET owner_id = 2 WHERE owner_id = 1;
UPDATE knowledge_bases SET owner_id = 2 WHERE owner_id = 1;
UPDATE dial_lists SET owner_id = 2 WHERE owner_id = 1;
UPDATE dnc_list SET added_by = 2 WHERE added_by = 1;

-- Now delete user 1
DELETE FROM users WHERE id = 1;

-- Verify
SELECT id, email, role, is_active, is_approved FROM users ORDER BY id;
