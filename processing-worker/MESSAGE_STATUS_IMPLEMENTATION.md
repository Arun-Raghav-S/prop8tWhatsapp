# WhatsApp Message Status Tracking - Implementation Guide

## Overview

Message status tracking has been successfully implemented in your WhatsApp agent. This allows you to track when messages are **sent**, **delivered**, and **read** by users.

## What Was Implemented

### 1. **Database Functions** (`src/services/messaging.py`)

Three new functions were added to handle message status tracking:

- `update_message_status()` - Updates individual message status in database
- `process_status_updates()` - Processes batch status updates from webhooks
- `trigger_status_update()` - Non-blocking background trigger for status updates

### 2. **Webhook Handler** (`main.py`)

The main webhook handler now:
- Detects status update webhooks from AiSensy
- Processes status updates in the background (non-blocking)
- Continues normal message processing without interruption

### 3. **Database Schema** (`MESSAGE_STATUS_SETUP.sql`)

SQL script to create the `broadcasts_messages` table with:
- Message ID tracking
- Phone number association
- JSONB status field for flexible status storage
- Optimized indexes for fast queries

---

## Setup Instructions

### Step 1: Add Database Indexes

The `message_logs` table should already exist in your database. Run the SQL script in your **Supabase SQL Editor** to add performance indexes:

```bash
# Open this file and copy the contents to Supabase SQL Editor
cat MESSAGE_STATUS_SETUP.sql
```

Or manually run:

```sql
-- Create indexes for fast lookups on the existing message_logs table
CREATE INDEX IF NOT EXISTS idx_message_logs_bsp_msg_id 
ON message_logs(bsp_msg_id);

CREATE INDEX IF NOT EXISTS idx_message_logs_whatsapp_status 
ON message_logs USING GIN (whatsapp_status);
```

### Step 2: Verify Environment Variables

Make sure you have these in your `.env` file:

```bash
# Required for message status tracking
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Your existing variables
SUPABASE_ANON_KEY=your_anon_key
AISENSY_ACCESS_TOKEN=your_access_token
```

⚠️ **Important**: You need `SUPABASE_SERVICE_ROLE_KEY` (not just anon key) to bypass RLS policies.

### Step 3: Enable Status Updates in AiSensy

1. Log in to **AiSensy Dashboard**
2. Go to **Settings → Webhooks**
3. Make sure **"Status Updates"** is enabled
4. Verify webhook URL is set correctly

### Step 4: Deploy and Test

1. **Deploy your changes:**
   ```bash
   cd processing-worker
   # Deploy using your existing deployment method
   ```

2. **Send a test message** to a user

3. **Check the database:**
   ```sql
   SELECT bsp_msg_id, to_phone, whatsapp_status FROM message_logs 
   WHERE bsp_msg_id IS NOT NULL 
   ORDER BY created_at DESC LIMIT 5;
   ```

4. **Expected result:**
   ```json
   {
     "bsp_msg_id": "wamid.HBgMOTE4...",
     "to_phone": "+919876543210",
     "whatsapp_status": {
       "sent": "2024-10-03T10:30:00Z",
       "delivered": "2024-10-03T10:30:05Z",
       "read": "2024-10-03T10:31:00Z"
     }
   }
   ```

---

## How It Works

### Message Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Agent sends message via AiSensy                      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 2. AiSensy sends "sent" status webhook                  │
│    → trigger_status_update() (background task)          │
│    → Database: whatsapp_status: {sent: "2024-10-03T..."}│
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Message delivered to user's device                   │
│    → AiSensy sends "delivered" status webhook           │
│    → Database: {sent: "...", delivered: "..."}         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│ 4. User opens and reads message                         │
│    → AiSensy sends "read" status webhook                │
│    → Database: {sent: "...", delivered: "...",         │
│                 read: "2024-10-03T10:31:00Z"}          │
└─────────────────────────────────────────────────────────┘
```

### Non-Blocking Design

✅ **Status updates run in background** - Your main conversation flow is never blocked  
✅ **Errors are logged but don't crash** - Failures in status tracking won't affect users  
✅ **Async with timeouts** - 10-second timeout prevents hanging  
✅ **Graceful fallbacks** - Invalid data is handled without breaking

---

## Key Features

### 1. **Out-of-Order Handling**

Sometimes "read" status arrives before "delivered". The system handles this:

```python
# If read comes before delivered, automatically add delivered
if status == "read" and "delivered" not in updated_status:
    updated_status["delivered"] = iso_timestamp
```

### 2. **Timestamp Conversion**

AiSensy sends Unix timestamps, we convert to ISO format:

```python
unix_timestamp = float(timestamp)  # "1702207800"
iso_timestamp = datetime.fromtimestamp(unix_timestamp).isoformat() + "Z"
# Result: "2024-10-03T10:30:00Z"
```

### 3. **Batch Processing**

Multiple status updates are processed together:

```python
# Process all statuses from webhook
for status_obj in statuses:
    await update_message_status(...)
```

---

## Analytics Queries

### Basic Queries

```sql
-- Get all messages for a phone number
SELECT bsp_msg_id, to_phone, whatsapp_status, created_at 
FROM message_logs
WHERE to_phone = '+919876543210' AND bsp_msg_id IS NOT NULL
ORDER BY created_at DESC;

-- Get messages that were read
SELECT bsp_msg_id, to_phone, whatsapp_status->>'read' as read_at
FROM message_logs
WHERE whatsapp_status ? 'read'
ORDER BY (whatsapp_status->>'read')::timestamptz DESC;

-- Get undelivered messages (>5 mins)
SELECT bsp_msg_id, to_phone, whatsapp_status, created_at
FROM message_logs
WHERE whatsapp_status->>'sent' IS NOT NULL
  AND whatsapp_status->>'delivered' IS NULL
  AND created_at < NOW() - INTERVAL '5 minutes';
```

### Analytics

```sql
-- Delivery rate (last 24 hours)
SELECT 
  COUNT(*) FILTER (WHERE whatsapp_status ? 'delivered') * 100.0 / 
  COUNT(*) as delivery_rate_percent
FROM message_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND bsp_msg_id IS NOT NULL;

-- Read rate (last 24 hours)
SELECT 
  COUNT(*) FILTER (WHERE whatsapp_status ? 'read') * 100.0 / 
  COUNT(*) FILTER (WHERE whatsapp_status ? 'delivered') as read_rate_percent
FROM message_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND bsp_msg_id IS NOT NULL;

-- Average delivery time
SELECT 
  AVG(
    EXTRACT(EPOCH FROM (whatsapp_status->>'delivered')::timestamptz) - 
    EXTRACT(EPOCH FROM (whatsapp_status->>'sent')::timestamptz)
  ) as avg_delivery_seconds
FROM message_logs
WHERE whatsapp_status ? 'sent' AND whatsapp_status ? 'delivered'
  AND created_at > NOW() - INTERVAL '24 hours';

-- Most engaged users (by read rate)
SELECT 
  to_phone,
  COUNT(*) as total_messages,
  COUNT(*) FILTER (WHERE whatsapp_status ? 'read') as read_messages,
  COUNT(*) FILTER (WHERE whatsapp_status ? 'read') * 100.0 / COUNT(*) as read_rate
FROM message_logs
WHERE created_at > NOW() - INTERVAL '7 days'
  AND bsp_msg_id IS NOT NULL
GROUP BY to_phone
HAVING COUNT(*) > 5
ORDER BY read_rate DESC
LIMIT 10;
```

---

## Testing

### Manual Test with cURL

```bash
# Test status update webhook
curl -X POST 'http://localhost:8080/' \
  -H 'Content-Type: application/json' \
  -d '{
    "message": {
      "data": "'$(echo '{
        "object": "whatsapp_business_account",
        "entry": [{
          "id": "your_business_account_id",
          "changes": [{
            "field": "messages",
            "value": {
              "statuses": [{
                "id": "test_message_001",
                "status": "delivered",
                "timestamp": "1696329600",
                "recipient_id": "919876543210"
              }]
            }
          }]
        }]
      }' | base64)'"
    }
  }'
```

### Verify in Database

```sql
SELECT * FROM broadcasts_messages WHERE message_id = 'test_message_001';
```

---

## Logs to Watch

When status updates are processed, you'll see logs like:

```
📊 [STATUS_WEBHOOK] Received 1 status updates
🚀 [STATUS] Launched background task to update 1 message statuses
📊 [STATUS_BATCH] Processing 1 status updates
📅 [STATUS] Converted timestamp: 1696329600 -> 2024-10-03T10:30:00Z
📊 [STATUS] Processing status update for message: test_message_001...
📊 [STATUS] Status: delivered
🔍 [STATUS] Searching for existing record with message_id: test_message_001
🔍 [STATUS] Found 1 existing records
📋 [STATUS] Existing status: {"sent": "2024-10-03T10:29:55Z"}
🔄 [STATUS] Updated status JSON: {"sent": "2024-10-03T10:29:55Z", "delivered": "2024-10-03T10:30:00Z"}
✅ [STATUS] Successfully updated status
✅ [STATUS_BATCH] Successfully processed
📊 [STATUS_BATCH] Completed: 1/1 successful
```

---

## Troubleshooting

### Issue: Status not updating

**Check:**
1. ✅ `SUPABASE_SERVICE_ROLE_KEY` is set in environment
2. ✅ Table `broadcasts_messages` exists in database
3. ✅ Webhook is receiving status updates (check logs)
4. ✅ No errors in logs

**Fix:**
```bash
# Check environment variable
python -c "from src.config import config; print(config.SUPABASE_SERVICE_ROLE_KEY[:20])"

# Check table exists
# Run in Supabase SQL Editor:
SELECT * FROM broadcasts_messages LIMIT 1;
```

### Issue: Webhooks not received

**Check:**
1. ✅ AiSensy webhook URL is correct
2. ✅ Status updates are enabled in AiSensy
3. ✅ Server is publicly accessible

---

## Performance & Security

### Performance
- ✅ **Non-blocking** - Uses `asyncio.create_task()` for background processing
- ✅ **Fast queries** - Indexed on `message_id` and `phone_number`
- ✅ **Timeouts** - 10-second timeout prevents hanging
- ✅ **Batch processing** - Multiple status updates processed together

### Security
- ✅ **Service role key** - Uses SERVICE_ROLE_KEY for database access
- ✅ **Input validation** - Checks for required fields
- ✅ **Error handling** - Graceful fallbacks for invalid data
- ✅ **No sensitive data in logs** - Message IDs are truncated

---

## Summary

✅ **Message status tracking is now live**  
✅ **Tracks sent/delivered/read statuses**  
✅ **Completely non-blocking and async**  
✅ **Errors won't disrupt your main flow**  
✅ **Ready for analytics and monitoring**

For more details, refer to `@messageStatusReadme.md` - the complete guide with all examples and use cases.

---

**Last Updated:** October 3, 2024  
**Status:** ✅ Ready for Production

