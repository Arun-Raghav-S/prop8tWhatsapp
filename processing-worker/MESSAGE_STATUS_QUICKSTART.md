# Message Status Tracking - Quick Start ⚡

## 🎯 What Was Done

Message status tracking (sent/delivered/read) has been implemented in your WhatsApp agent. It's **non-blocking**, **async**, and **won't disrupt your conversation flow**.

## ✅ Files Changed

1. **`src/services/messaging.py`** - Added 3 functions:
   - `update_message_status()` - Update individual status
   - `process_status_updates()` - Process batch updates
   - `trigger_status_update()` - Non-blocking trigger

2. **`main.py`** - Updated webhook handler:
   - Detects status updates in webhooks
   - Processes them in background
   - Doesn't block message processing

3. **`MESSAGE_STATUS_SETUP.sql`** - Database schema
4. **`MESSAGE_STATUS_IMPLEMENTATION.md`** - Full guide
5. **`test_message_status.py`** - Test script

## 🚀 Quick Setup (5 Minutes)

### Step 1: Add Database Indexes

The `message_logs` table should already exist. Add performance indexes:

```sql
-- Run in Supabase SQL Editor:
CREATE INDEX IF NOT EXISTS idx_message_logs_bsp_msg_id 
ON message_logs(bsp_msg_id);

CREATE INDEX IF NOT EXISTS idx_message_logs_whatsapp_status 
ON message_logs USING GIN (whatsapp_status);
```

Or just run the entire `MESSAGE_STATUS_SETUP.sql` file.

### Step 2: Verify Environment Variables

Check your `.env` file has:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key  # ⚠️ Important: SERVICE_ROLE_KEY, not anon key!
```

### Step 3: Deploy

```bash
# Your existing deployment process
cd processing-worker
# Deploy...
```

### Step 4: Test

1. **Send a message** to a user via your agent
2. **Check database:**
   ```sql
   SELECT bsp_msg_id, to_phone, whatsapp_status FROM message_logs 
   WHERE bsp_msg_id IS NOT NULL 
   ORDER BY created_at DESC LIMIT 5;
   ```
3. **Expected result:**
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

## 📊 Quick Analytics

### Check delivery rate:
```sql
SELECT 
  COUNT(*) FILTER (WHERE whatsapp_status ? 'delivered') * 100.0 / COUNT(*) as delivery_rate
FROM message_logs
WHERE created_at > NOW() - INTERVAL '24 hours' AND bsp_msg_id IS NOT NULL;
```

### Check read rate:
```sql
SELECT 
  COUNT(*) FILTER (WHERE whatsapp_status ? 'read') * 100.0 / 
  COUNT(*) FILTER (WHERE whatsapp_status ? 'delivered') as read_rate
FROM message_logs
WHERE created_at > NOW() - INTERVAL '24 hours' AND bsp_msg_id IS NOT NULL;
```

### Most engaged users:
```sql
SELECT 
  to_phone,
  COUNT(*) as messages,
  COUNT(*) FILTER (WHERE whatsapp_status ? 'read') * 100.0 / COUNT(*) as read_rate
FROM message_logs
WHERE created_at > NOW() - INTERVAL '7 days' AND bsp_msg_id IS NOT NULL
GROUP BY to_phone
HAVING COUNT(*) > 5
ORDER BY read_rate DESC
LIMIT 10;
```

## 🔍 Verify It's Working

### In Logs:
Look for these log messages:
```
📊 [STATUS_WEBHOOK] Received 1 status updates
🚀 [STATUS] Launched background task to update 1 message statuses
✅ [STATUS] Successfully updated status
```

### In Database:
```sql
-- Should see new entries with WhatsApp status
SELECT COUNT(*) FROM message_logs WHERE whatsapp_status IS NOT NULL;

-- Should see status updates
SELECT bsp_msg_id, whatsapp_status FROM message_logs 
WHERE whatsapp_status IS NOT NULL 
ORDER BY created_at DESC LIMIT 3;
```

## 🛠️ Test Script

Run the test script to verify:
```bash
# Edit test_message_status.py first:
# - Set BASE_URL to your server
# - Set BUSINESS_ACCOUNT_ID to your WhatsApp business account ID

python test_message_status.py
```

## ⚠️ Troubleshooting

### Problem: Status not updating

**Check:**
```bash
# 1. Verify SERVICE_ROLE_KEY is set
python -c "from src.config import config; print('✅ Key exists' if config.SUPABASE_SERVICE_ROLE_KEY else '❌ Key missing')"

# 2. Verify table exists
# Run in Supabase: SELECT * FROM message_logs LIMIT 1;

# 3. Check logs for errors
grep "STATUS" logs/*.log
```

### Problem: Webhooks not received

**Check:**
1. AiSensy Dashboard → Settings → Webhooks → Status Updates is enabled
2. Webhook URL is correct
3. Server is publicly accessible

## 📚 More Information

- **Full documentation**: `MESSAGE_STATUS_IMPLEMENTATION.md`
- **Complete guide**: `messageStatusReadme.md` (reference)
- **Database schema**: `MESSAGE_STATUS_SETUP.sql`
- **Test script**: `test_message_status.py`

## ✨ Key Features

✅ **Non-blocking** - Runs in background, won't slow down responses  
✅ **Error-safe** - Errors won't crash your main flow  
✅ **Async** - Uses asyncio for efficient processing  
✅ **Out-of-order handling** - Handles read before delivered  
✅ **Batch processing** - Processes multiple updates efficiently  
✅ **Analytics ready** - Query status data for insights

## 🎉 That's It!

You're done! Message status tracking is now live and tracking sent/delivered/read statuses for all your WhatsApp messages.

---

**Need Help?** Check `MESSAGE_STATUS_IMPLEMENTATION.md` for detailed docs.

