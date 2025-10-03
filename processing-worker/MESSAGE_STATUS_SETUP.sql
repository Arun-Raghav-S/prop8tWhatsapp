-- ============================================================================
-- WhatsApp Message Status Tracking - Database Setup (Updated for message_logs)
-- ============================================================================
-- The message_logs table should already exist in your database.
-- This script adds indexes for better performance on status queries.

-- Verify the message_logs table exists
-- SELECT table_name FROM information_schema.tables WHERE table_name = 'message_logs';

-- Create indexes for fast lookups on the existing message_logs table
CREATE INDEX IF NOT EXISTS idx_message_logs_bsp_msg_id 
ON message_logs(bsp_msg_id);

CREATE INDEX IF NOT EXISTS idx_message_logs_to_phone 
ON message_logs(to_phone);

-- Create index for whatsapp_status queries (GIN index for JSONB)
CREATE INDEX IF NOT EXISTS idx_message_logs_whatsapp_status 
ON message_logs USING GIN (whatsapp_status);

-- Create index for org_id (for organization-specific queries)
CREATE INDEX IF NOT EXISTS idx_message_logs_org_id 
ON message_logs(org_id);

-- Create composite index for common queries (org_id + created_at)
CREATE INDEX IF NOT EXISTS idx_message_logs_org_created 
ON message_logs(org_id, created_at DESC);

-- Note: The message_logs table already has the following structure:
-- - id (uuid, primary key)
-- - org_id (uuid, foreign key to organization)
-- - bsp_msg_id (text) - This is where WhatsApp message IDs are stored
-- - whatsapp_status (jsonb) - This is where status updates are stored
-- - to_phone (text) - Phone number
-- - created_at (timestamptz)
-- - And other columns for message metadata

-- ============================================================================
-- Example Queries (Updated for message_logs table)
-- ============================================================================

-- Get all messages with their WhatsApp status
-- SELECT bsp_msg_id, to_phone, whatsapp_status, created_at 
-- FROM message_logs 
-- WHERE bsp_msg_id IS NOT NULL
-- ORDER BY created_at DESC 
-- LIMIT 10;

-- Get messages that were read
-- SELECT bsp_msg_id, to_phone, whatsapp_status->>'read' as read_at
-- FROM message_logs
-- WHERE whatsapp_status ? 'read'
-- ORDER BY (whatsapp_status->>'read')::timestamptz DESC;

-- Calculate delivery rate (last 24 hours)
-- SELECT 
--   COUNT(*) FILTER (WHERE whatsapp_status ? 'delivered') * 100.0 / COUNT(*) as delivery_rate_percent
-- FROM message_logs
-- WHERE created_at > NOW() - INTERVAL '24 hours'
--   AND bsp_msg_id IS NOT NULL;

-- Calculate read rate (last 24 hours)
-- SELECT 
--   COUNT(*) FILTER (WHERE whatsapp_status ? 'read') * 100.0 / 
--   COUNT(*) FILTER (WHERE whatsapp_status ? 'delivered') as read_rate_percent
-- FROM message_logs
-- WHERE created_at > NOW() - INTERVAL '24 hours'
--   AND bsp_msg_id IS NOT NULL;

-- Average delivery time (in seconds)
-- SELECT 
--   AVG(
--     EXTRACT(EPOCH FROM (whatsapp_status->>'delivered')::timestamptz) - 
--     EXTRACT(EPOCH FROM (whatsapp_status->>'sent')::timestamptz)
--   ) as avg_delivery_seconds
-- FROM message_logs
-- WHERE whatsapp_status ? 'sent' AND whatsapp_status ? 'delivered'
--   AND created_at > NOW() - INTERVAL '24 hours';

-- Get messages by organization
-- SELECT org_id, COUNT(*) as total_messages,
--        COUNT(*) FILTER (WHERE whatsapp_status ? 'delivered') as delivered,
--        COUNT(*) FILTER (WHERE whatsapp_status ? 'read') as read
-- FROM message_logs
-- WHERE created_at > NOW() - INTERVAL '24 hours'
--   AND bsp_msg_id IS NOT NULL
-- GROUP BY org_id;

-- ============================================================================
-- Verification
-- ============================================================================
-- Verify message_logs table exists
-- SELECT table_name, column_name, data_type 
-- FROM information_schema.columns 
-- WHERE table_name = 'message_logs'
-- ORDER BY ordinal_position;

-- Verify indexes were created
-- SELECT schemaname, tablename, indexname 
-- FROM pg_indexes 
-- WHERE tablename = 'message_logs'
-- ORDER BY indexname;

-- Test query to verify whatsapp_status column works
-- SELECT bsp_msg_id, whatsapp_status 
-- FROM message_logs 
-- WHERE whatsapp_status IS NOT NULL 
-- LIMIT 5;

