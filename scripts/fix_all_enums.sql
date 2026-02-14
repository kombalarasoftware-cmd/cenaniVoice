-- Fix all DB enum values to match Python model .value (lowercase)
-- callstatus and calloutcome are already lowercase, skip them

-- userrole: ADMIN->admin, MANAGER->manager, OPERATOR->operator
ALTER TYPE userrole RENAME VALUE 'ADMIN' TO 'admin';
ALTER TYPE userrole RENAME VALUE 'MANAGER' TO 'manager';
ALTER TYPE userrole RENAME VALUE 'OPERATOR' TO 'operator';

-- agentstatus: DRAFT->draft, ACTIVE->active, INACTIVE->inactive
ALTER TYPE agentstatus RENAME VALUE 'DRAFT' TO 'draft';
ALTER TYPE agentstatus RENAME VALUE 'ACTIVE' TO 'active';
ALTER TYPE agentstatus RENAME VALUE 'INACTIVE' TO 'inactive';

-- campaignstatus: DRAFT->draft, SCHEDULED->scheduled, etc.
ALTER TYPE campaignstatus RENAME VALUE 'DRAFT' TO 'draft';
ALTER TYPE campaignstatus RENAME VALUE 'SCHEDULED' TO 'scheduled';
ALTER TYPE campaignstatus RENAME VALUE 'RUNNING' TO 'running';
ALTER TYPE campaignstatus RENAME VALUE 'PAUSED' TO 'paused';
ALTER TYPE campaignstatus RENAME VALUE 'COMPLETED' TO 'completed';
ALTER TYPE campaignstatus RENAME VALUE 'CANCELLED' TO 'cancelled';

-- appointmentstatus
ALTER TYPE appointmentstatus RENAME VALUE 'PENDING' TO 'pending';
ALTER TYPE appointmentstatus RENAME VALUE 'CONFIRMED' TO 'confirmed';
ALTER TYPE appointmentstatus RENAME VALUE 'CANCELLED' TO 'cancelled';
ALTER TYPE appointmentstatus RENAME VALUE 'COMPLETED' TO 'completed';
ALTER TYPE appointmentstatus RENAME VALUE 'NO_SHOW' TO 'no_show';

-- appointmenttype
ALTER TYPE appointmenttype RENAME VALUE 'CONSULTATION' TO 'consultation';
ALTER TYPE appointmenttype RENAME VALUE 'SITE_VISIT' TO 'site_visit';
ALTER TYPE appointmenttype RENAME VALUE 'INSTALLATION' TO 'installation';
ALTER TYPE appointmenttype RENAME VALUE 'MAINTENANCE' TO 'maintenance';
ALTER TYPE appointmenttype RENAME VALUE 'DEMO' TO 'demo';
ALTER TYPE appointmenttype RENAME VALUE 'OTHER' TO 'other';

-- leadstatus
ALTER TYPE leadstatus RENAME VALUE 'NEW' TO 'new';
ALTER TYPE leadstatus RENAME VALUE 'CONTACTED' TO 'contacted';
ALTER TYPE leadstatus RENAME VALUE 'QUALIFIED' TO 'qualified';
ALTER TYPE leadstatus RENAME VALUE 'CONVERTED' TO 'converted';
ALTER TYPE leadstatus RENAME VALUE 'LOST' TO 'lost';

-- leadinteresttype
ALTER TYPE leadinteresttype RENAME VALUE 'CALLBACK' TO 'callback';
ALTER TYPE leadinteresttype RENAME VALUE 'ADDRESS_COLLECTION' TO 'address_collection';
ALTER TYPE leadinteresttype RENAME VALUE 'PURCHASE_INTENT' TO 'purchase_intent';
ALTER TYPE leadinteresttype RENAME VALUE 'DEMO_REQUEST' TO 'demo_request';
ALTER TYPE leadinteresttype RENAME VALUE 'QUOTE_REQUEST' TO 'quote_request';
ALTER TYPE leadinteresttype RENAME VALUE 'SUBSCRIPTION' TO 'subscription';
ALTER TYPE leadinteresttype RENAME VALUE 'INFORMATION' TO 'information';
ALTER TYPE leadinteresttype RENAME VALUE 'OTHER' TO 'other';

-- surveystatus
ALTER TYPE surveystatus RENAME VALUE 'NOT_STARTED' TO 'not_started';
ALTER TYPE surveystatus RENAME VALUE 'IN_PROGRESS' TO 'in_progress';
ALTER TYPE surveystatus RENAME VALUE 'COMPLETED' TO 'completed';
ALTER TYPE surveystatus RENAME VALUE 'ABANDONED' TO 'abandoned';

-- realtimemodel: special case - some lowercase values already exist
-- First update data from UPPERCASE to lowercase equivalents
UPDATE agents SET model_type = 'grok-2-realtime' WHERE model_type = 'XAI_GROK';
UPDATE agents SET model_type = 'gemini-live-2.5-flash-native-audio' WHERE model_type = 'GEMINI_LIVE';
UPDATE agents SET model_type = 'gemini-live-2.5-flash-preview-native-audio-09-2025' WHERE model_type = 'GEMINI_LIVE_PREVIEW';
UPDATE agents SET model_type = 'gpt-realtime' WHERE model_type = 'GPT_REALTIME';
UPDATE agents SET model_type = 'gpt-realtime-mini' WHERE model_type = 'GPT_REALTIME_MINI';
UPDATE agents SET model_type = 'ultravox-v0.7' WHERE model_type = 'ULTRAVOX';
UPDATE agents SET model_type = 'ultravox-v0.6' WHERE model_type = 'ULTRAVOX_V0_6';
UPDATE agents SET model_type = 'ultravox-v0.6-gemma3-27b' WHERE model_type = 'ULTRAVOX_V0_6_GEMMA3_27B';
UPDATE agents SET model_type = 'ultravox-v0.6-llama3.3-70b' WHERE model_type = 'ULTRAVOX_V0_6_LLAMA3_3_70B';
-- Rename UPPERCASE values that DON'T have lowercase duplicates (safe to rename)
-- The ones that DO have duplicates (grok-2-realtime etc.) are left as orphaned enum values
-- PostgreSQL does not support removing enum values but orphaned ones cause no harm
