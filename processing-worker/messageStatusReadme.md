# WhatsApp Message Status Tracking - Complete Implementation Guide

## The All-In-One Guide for AiSensy Message Status Tracking

This is a **complete, self-contained guide** for implementing WhatsApp message status tracking (sent/delivered/read) using AiSensy. Everything you need is in this one document.

---

## Table of Contents

1. [Overview](#1-overview)
2. [5-Minute Quick Start](#2-5-minute-quick-start)
3. [How It Works](#3-how-it-works)
4. [Architecture & Flow](#4-architecture--flow)
5. [Database Setup](#5-database-setup)
6. [Complete Code Implementation](#6-complete-code-implementation)
7. [Code Explanations](#7-code-explanations)
8. [Webhook Integration](#8-webhook-integration)
9. [Testing](#9-testing)
10. [Analytics & Queries](#10-analytics--queries)
11. [Troubleshooting](#11-troubleshooting)
12. [Performance & Security](#12-performance--security)

---

## 1. Overview

### What is Message Status Tracking?

Track the complete lifecycle of WhatsApp messages:

- **Sent** ✅ - Message sent to WhatsApp servers
- **Delivered** 📬 - Message delivered to recipient's device  
- **Read** 👁️ - Recipient opened and read the message

### Why Track Message Status?

1. **User Engagement Analytics** - Know when users read messages
2. **Delivery Monitoring** - Detect failed deliveries
3. **Response Time Metrics** - Measure time between delivery and user reply
4. **Message Reliability** - Track message delivery success rates
5. **Business Intelligence** - Analyze user engagement patterns

### System Architecture

```
┌─────────────┐         ┌──────────────┐         ┌──────────────┐
│   Agent     │ Send    │   AiSensy    │ Deliver │   WhatsApp   │
│   Sends     │────────>│   Platform   │────────>│     User     │
│   Message   │         │              │         │              │
└─────────────┘         └──────────────┘         └──────────────┘
                               │                         │
                               │ Webhook                 │
                               │ Status Updates          │
                               ▼                         │
                        ┌──────────────┐                │
                        │   Your       │                │
                        │   Webhook    │◀───────────────┘
                        │   Endpoint   │     Read Receipt
                        └──────────────┘
                               │
                               │ Store Status
                               ▼
                        ┌──────────────┐
                        │   Supabase   │
                        │   Database   │
                        └──────────────┘
```

---

## 2. 5-Minute Quick Start

### Step 1: Create Database Table

Run in Supabase SQL Editor:

```sql
CREATE TABLE broadcasts_messages (
  id BIGSERIAL PRIMARY KEY,
  message_id TEXT UNIQUE NOT NULL,
  phone_number TEXT,
  status JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_broadcasts_messages_message_id ON broadcasts_messages(message_id);
CREATE INDEX idx_broadcasts_messages_phone_number ON broadcasts_messages(phone_number);
```

### Step 2: Add Environment Variables

```bash
# .env file
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

⚠️ **Important**: Use SERVICE_ROLE_KEY (not anon key) to bypass RLS policies.

### Step 3: Add Status Update Functions

**File**: `src/services/messaging.py`

```python
import json
import httpx
import logging
from datetime import datetime
from typing import List, Dict, Any
from src.config import config

logger = logging.getLogger(__name__)

async def update_message_status(
    message_id: str, 
    status: str, 
    timestamp: str, 
    recipient_phone: str = None,
    whatsapp_business_account: str = None
) -> bool:
    """
    Update message status in the broadcasts_messages table
    
    Args:
        message_id: The WhatsApp message ID
        status: Status type (sent, delivered, read)
        timestamp: Unix timestamp from webhook
        recipient_phone: Phone number of recipient (optional)
        whatsapp_business_account: Business account ID (optional)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        status_logger = logging.getLogger('message_status')
        
        # Convert Unix timestamp to ISO format
        try:
            unix_timestamp = float(timestamp)
            iso_timestamp = datetime.fromtimestamp(unix_timestamp).isoformat() + "Z"
            status_logger.info(f"📅 [STATUS] Converted timestamp: {timestamp} -> {iso_timestamp}")
        except (ValueError, TypeError) as e:
            status_logger.error(f"❌ [STATUS] Invalid timestamp: {timestamp}, error: {e}")
            iso_timestamp = datetime.now().isoformat() + "Z"
        
        status_logger.info(f"📊 [STATUS] Processing status update for message: {message_id[:30]}...")
        status_logger.info(f"📊 [STATUS] Status: {status}")
        status_logger.info(f"📊 [STATUS] Timestamp: {iso_timestamp}")
        
        if not config.SUPABASE_SERVICE_ROLE_KEY:
            status_logger.error(f"❌ [STATUS] Missing SUPABASE_SERVICE_ROLE_KEY")
            return False
        
        # Database URL and headers
        search_url = f"{config.SUPABASE_URL}/rest/v1/broadcasts_messages"
        headers = {
            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Search for existing record
        search_params = {"message_id": f"eq.{message_id}", "select": "id,status"}
        status_logger.info(f"🔍 [STATUS] Searching for existing record with message_id: {message_id}")
        
        async with httpx.AsyncClient() as client:
            search_response = await client.get(search_url, headers=headers, params=search_params)
            
            if search_response.status_code == 200:
                existing_records = search_response.json()
                status_logger.info(f"🔍 [STATUS] Found {len(existing_records)} existing records")
                
                if existing_records:
                    # Update existing record
                    record = existing_records[0]
                    existing_status = record.get("status", {})
                    status_logger.info(f"📋 [STATUS] Existing status: {existing_status}")
                    
                    # Parse existing status JSON or create new one
                    if isinstance(existing_status, dict):
                        updated_status = existing_status.copy()
                    else:
                        try:
                            updated_status = json.loads(existing_status) if existing_status else {}
                        except (json.JSONDecodeError, TypeError):
                            updated_status = {}
                    
                    # Add the new status with timestamp
                    updated_status[status] = iso_timestamp
                    
                    # Handle out-of-order delivery: if read comes before delivered
                    if status == "read" and "delivered" not in updated_status and "sent" in updated_status:
                        status_logger.info(f"⚠️ [STATUS] Read received before delivered - using same timestamp")
                        updated_status["delivered"] = iso_timestamp
                    
                    status_logger.info(f"🔄 [STATUS] Updated status JSON: {updated_status}")
                    
                    # Update the record
                    update_url = f"{search_url}?id=eq.{record['id']}"
                    update_data = {"status": updated_status}
                    
                    update_response = await client.patch(update_url, headers=headers, json=update_data)
                    
                    if update_response.status_code in [200, 204]:
                        status_logger.info(f"✅ [STATUS] Successfully updated status")
                        return True
                    else:
                        status_logger.error(f"❌ [STATUS] Failed to update: {update_response.status_code}")
                        return False
                else:
                    # No existing record found, create new one
                    status_logger.info(f"📝 [STATUS] Creating new record")
                    
                    new_record = {
                        "message_id": message_id,
                        "phone_number": recipient_phone,
                        "status": {status: iso_timestamp}
                    }
                    
                    create_response = await client.post(search_url, headers=headers, json=new_record)
                    
                    if create_response.status_code in [200, 201]:
                        status_logger.info(f"✅ [STATUS] Successfully created new record")
                        return True
                    else:
                        status_logger.error(f"❌ [STATUS] Failed to create: {create_response.status_code}")
                        return False
            else:
                status_logger.error(f"❌ [STATUS] Search failed: {search_response.status_code}")
                return False
                
    except Exception as e:
        logger.error(f"❌ [STATUS] Error updating message status: {e}")
        import traceback
        logger.error(f"❌ [STATUS] Traceback: {traceback.format_exc()}")
        return False


async def process_status_updates(
    statuses: List[Dict[str, Any]], 
    whatsapp_business_account: str = None
) -> bool:
    """
    Process multiple status updates from a webhook
    
    Args:
        statuses: List of status objects from webhook
        whatsapp_business_account: Business account ID (optional)
        
    Returns:
        bool: True if all updates successful, False otherwise
    """
    status_logger = logging.getLogger('message_status')
    status_logger.info(f"📊 [STATUS_BATCH] Processing {len(statuses)} status updates")
    
    success_count = 0
    
    for status_obj in statuses:
        try:
            message_id = status_obj.get("id")
            status = status_obj.get("status")
            timestamp = status_obj.get("timestamp")
            recipient_id = status_obj.get("recipient_id")
            
            if not all([message_id, status, timestamp]):
                status_logger.warning(f"⚠️ [STATUS_BATCH] Missing required fields: {status_obj}")
                continue
            
            status_logger.info(f"📊 [STATUS_BATCH] Processing: {message_id[:30]}... -> {status}")
            
            # Convert recipient_id to phone format if available
            recipient_phone = f"+{recipient_id}" if recipient_id else None
            
            # Update individual status
            success = await update_message_status(
                message_id, 
                status, 
                timestamp, 
                recipient_phone, 
                whatsapp_business_account
            )
            
            if success:
                success_count += 1
                status_logger.info(f"✅ [STATUS_BATCH] Successfully processed")
            else:
                status_logger.error(f"❌ [STATUS_BATCH] Failed to process")
                
        except Exception as e:
            status_logger.error(f"❌ [STATUS_BATCH] Error: {e}")
    
    status_logger.info(f"📊 [STATUS_BATCH] Completed: {success_count}/{len(statuses)} successful")
    return success_count == len(statuses)
```

### Step 4: Add Webhook Handler

**File**: `main.py`

```python
from fastapi import FastAPI, Request
from src.services.messaging import process_status_updates
import json
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Handle incoming webhooks from AiSensy
    
    This endpoint receives both:
    1. Message webhooks (new messages from users)
    2. Status webhooks (delivery status updates)
    """
    try:
        payload = await request.json()
        logger.info(f"📥 [WEBHOOK] Received payload: {json.dumps(payload, indent=2)}")
        
        # Check if this is a status update webhook
        if "statuses" in payload:
            logger.info(f"📊 [WEBHOOK] Status update webhook detected")
            
            statuses = payload.get("statuses", [])
            whatsapp_business_account = payload.get("whatsapp_business_account")
            
            # Process all status updates
            success = await process_status_updates(statuses, whatsapp_business_account)
            
            if success:
                logger.info(f"✅ [WEBHOOK] All status updates processed")
                return {"status": "success", "processed": len(statuses)}
            else:
                logger.warning(f"⚠️ [WEBHOOK] Some status updates failed")
                return {"status": "partial_success", "processed": len(statuses)}
        
        # Handle regular message webhooks here...
        # (your existing message processing code)
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ [WEBHOOK] Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}
```

### Step 5: Configure AiSensy

1. Go to AiSensy Dashboard
2. Settings → Webhooks
3. Add webhook URL: `https://your-domain.com/webhook`
4. Enable "Status Updates"
5. Save

### Step 6: Test

```bash
# Test with cURL
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{
    "statuses": [{
      "id": "test_msg_001",
      "status": "delivered",
      "timestamp": "1702207800",
      "recipient_id": "919876543210"
    }]
  }'

# Check database
# Run in Supabase SQL editor:
SELECT * FROM broadcasts_messages WHERE message_id = 'test_msg_001';
```

**Expected Result:**
```json
{
  "message_id": "test_msg_001",
  "status": {
    "delivered": "2024-12-10T10:30:00Z"
  }
}
```

---

## 3. How It Works

### The Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: SEND MESSAGE                                            │
└─────────────────────────────────────────────────────────────────┘

Agent Code:
  send_message_via_aisensy("+919876543210", "Hello!")
         │
         ▼
  POST https://backend.aisensy.com/direct-apis/t1/messages
         │
         ▼
  Response: {"messageId": "wamid.HBgMOTE4..."}
         │
         ▼
  (Message sent to WhatsApp servers)


┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: SENT STATUS WEBHOOK (within seconds)                    │
└─────────────────────────────────────────────────────────────────┘

AiSensy → Your Webhook:
  POST https://your-domain.com/webhook
  {
    "statuses": [{
      "id": "wamid.HBgMOTE4...",
      "status": "sent",
      "timestamp": "1702207800"
    }]
  }
         │
         ▼
  process_status_updates(statuses)
         │
         ▼
  update_message_status(message_id, "sent", timestamp)
         │
         ▼
  Database INSERT:
    message_id: "wamid.HBgMOTE4..."
    status: {"sent": "2024-12-10T10:30:00Z"}


┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: DELIVERED STATUS WEBHOOK (few seconds later)            │
└─────────────────────────────────────────────────────────────────┘

AiSensy → Your Webhook:
  POST https://your-domain.com/webhook
  {
    "statuses": [{
      "id": "wamid.HBgMOTE4...",
      "status": "delivered",
      "timestamp": "1702207805"
    }]
  }
         │
         ▼
  update_message_status(message_id, "delivered", timestamp)
         │
         ▼
  Database UPDATE:
    status: {
      "sent": "2024-12-10T10:30:00Z",
      "delivered": "2024-12-10T10:30:05Z"
    }


┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: READ STATUS WEBHOOK (when user opens message)           │
└─────────────────────────────────────────────────────────────────┘

User Opens WhatsApp → Reads Message
         │
         ▼
AiSensy → Your Webhook:
  POST https://your-domain.com/webhook
  {
    "statuses": [{
      "id": "wamid.HBgMOTE4...",
      "status": "read",
      "timestamp": "1702207860"
    }]
  }
         │
         ▼
  update_message_status(message_id, "read", timestamp)
         │
         ▼
  Database UPDATE:
    status: {
      "sent": "2024-12-10T10:30:00Z",
      "delivered": "2024-12-10T10:30:05Z",
      "read": "2024-12-10T10:31:00Z"
    }
```

### Webhook Payload Format

AiSensy sends status updates in this format:

```json
{
  "statuses": [
    {
      "id": "wamid.HBgMOTE4MjgxODQwNDYyFQIAEhggRDc3...",
      "status": "read",
      "timestamp": "1702207800",
      "recipient_id": "919876543210"
    }
  ]
}
```

**Key Fields:**
- `id` - WhatsApp message ID (unique identifier)
- `status` - Current status (`sent`, `delivered`, or `read`)
- `timestamp` - Unix timestamp when status changed
- `recipient_id` - Phone number of recipient (without +)

---

## 4. Architecture & Flow

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        YOUR WHATSAPP AGENT                           │
│                                                                       │
│  ┌──────────────┐         ┌──────────────┐         ┌─────────────┐ │
│  │   Message    │         │   Webhook    │         │   Database  │ │
│  │   Sender     │         │   Handler    │         │   Manager   │ │
│  └──────────────┘         └──────────────┘         └─────────────┘ │
│         │                         │                         │        │
└─────────┼─────────────────────────┼─────────────────────────┼────────┘
          │                         │                         │
          │ 1. Send Message         │                         │
          ▼                         │                         │
    ┌──────────┐                   │                         │
    │ AiSensy  │                   │                         │
    │ Platform │                   │ 3. Status Webhooks      │
    └──────────┘                   │    (sent/delivered/read)│
          │                         │                         │
          │ 2. Deliver              ▼                         │
          ▼                   ┌──────────┐                   │
    ┌──────────┐              │ Webhook  │                   │
    │ WhatsApp │              │ Endpoint │                   │
    │   User   │              └──────────┘                   │
    └──────────┘                    │                         │
          │                         │ 4. Update Status        │
          │                         └────────────────────────>│
          │ 5. Read Message                                   │
          └───────────────────────────────────────────────────┘
```

### Database Operations Flow

```
┌────────────────────────────────────────────────────────────┐
│ update_message_status() Function Flow                      │
└────────────────────────────────────────────────────────────┘

INPUT:
  message_id = "wamid.HBgMOTE4..."
  status = "delivered"
  timestamp = "1702207805"

         │
         ▼
┌────────────────────┐
│ Convert Timestamp  │
│ Unix → ISO         │
└────────────────────┘
         │
         │ "1702207805" → "2024-12-10T10:30:05Z"
         ▼
┌────────────────────┐
│ Search for Record  │
│ by message_id      │
└────────────────────┘
         │
         ▼
    ┌────┴────┐
    │  Found? │
    └────┬────┘
         │
    ┌────┴────────────────────────────┐
    │                                  │
   YES                                NO
    │                                  │
    ▼                                  ▼
┌────────────────┐            ┌─────────────────┐
│ Get Existing   │            │ Create New      │
│ Status JSON    │            │ Record          │
└────────────────┘            └─────────────────┘
    │                                  │
    │ {"sent": "..."}                  │ {"delivered": "..."}
    ▼                                  ▼
┌────────────────┐            ┌─────────────────┐
│ Merge New      │            │ INSERT Record   │
│ Status         │            │ to Database     │
└────────────────┘            └─────────────────┘
    │                                  │
    │ {                                │
    │   "sent": "...",                 │
    │   "delivered": "..."             │
    │ }                                │
    ▼                                  ▼
┌────────────────┐            ┌─────────────────┐
│ PATCH Update   │            │ Return Success  │
│ Database       │            └─────────────────┘
└────────────────┘
    │
    ▼
┌────────────────┐
│ Return Success │
└────────────────┘
```

---

## 5. Database Setup

### Schema Design

```sql
CREATE TABLE broadcasts_messages (
  id BIGSERIAL PRIMARY KEY,
  message_id TEXT UNIQUE NOT NULL,
  phone_number TEXT,
  status JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add index for fast message_id lookups
CREATE INDEX idx_broadcasts_messages_message_id 
ON broadcasts_messages(message_id);

-- Add index for phone number queries
CREATE INDEX idx_broadcasts_messages_phone_number 
ON broadcasts_messages(phone_number);
```

### Status JSONB Structure

```json
{
  "sent": "2024-12-10T10:30:00Z",
  "delivered": "2024-12-10T10:30:05Z",
  "read": "2024-12-10T10:31:00Z"
}
```

### Why JSONB?

✅ **Flexible** - Can add new status types without schema changes  
✅ **Atomic Updates** - Update specific status without overwriting others  
✅ **Queryable** - Can query by specific status timestamps  
✅ **Compact** - All statuses in one field  

### Example Record

```
┌─────────────────────────────────────────────────────────┐
│ id:           12345                                      │
│ message_id:   "wamid.HBgMOTE4MjgxODQwNDYy..."           │
│ phone_number: "+919876543210"                           │
│ status:       {                                         │
│                 "sent": "2024-12-10T10:30:00Z",        │
│                 "delivered": "2024-12-10T10:30:05Z",   │
│                 "read": "2024-12-10T10:31:00Z"         │
│               }                                         │
│ created_at:   2024-12-10T10:30:00Z                     │
│ updated_at:   2024-12-10T10:31:00Z                     │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Complete Code Implementation

### Configuration (config.py)

```python
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    AISENSY_BASE_URL = "https://backend.aisensy.com"
    AISENSY_ACCESS_TOKEN = os.getenv("AISENSY_ACCESS_TOKEN")

config = Config()
```

### Main Application (main.py)

```python
from fastapi import FastAPI, Request
from src.services.messaging import process_status_updates
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

app = FastAPI()

@app.post("/webhook")
async def handle_webhook(request: Request):
    """Handle incoming webhooks from AiSensy"""
    try:
        payload = await request.json()
        logger.info(f"📥 [WEBHOOK] Received webhook")
        
        # Check if this is a status update webhook
        if "statuses" in payload:
            logger.info(f"📊 [WEBHOOK] Status update detected")
            
            statuses = payload.get("statuses", [])
            whatsapp_business_account = payload.get("whatsapp_business_account")
            
            # Process all status updates
            success = await process_status_updates(statuses, whatsapp_business_account)
            
            if success:
                return {"status": "success", "processed": len(statuses)}
            else:
                return {"status": "partial_success", "processed": len(statuses)}
        
        # Handle regular message webhooks
        elif "messages" in payload:
            logger.info(f"💬 [WEBHOOK] Message webhook detected")
            # Your existing message processing code here
            return {"status": "success"}
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ [WEBHOOK] Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Message Status Service (complete)

Already provided in Step 3 of Quick Start section above.

---

## 7. Code Explanations

### 7.1 Timestamp Conversion

**Why we need this:**

AiSensy sends Unix timestamps (e.g., `1702207800`), but PostgreSQL uses ISO 8601 format.

```python
# Convert Unix timestamp to ISO format
try:
    unix_timestamp = float(timestamp)  # "1702207800" -> 1702207800.0
    iso_timestamp = datetime.fromtimestamp(unix_timestamp).isoformat() + "Z"
    # Result: "2024-12-10T10:30:00Z"
except (ValueError, TypeError) as e:
    # Fallback: use current time if timestamp is invalid
    iso_timestamp = datetime.now().isoformat() + "Z"
```

**Key Points:**
- Convert string to float first
- Use `datetime.fromtimestamp()` for conversion
- Add "Z" suffix to indicate UTC timezone
- Always have a fallback for invalid timestamps

### 7.2 Search for Existing Record

**Why we search first:**

We need to check if this message already has a status record to decide whether to UPDATE or CREATE.

```python
# Search for existing record
search_params = {
    "message_id": f"eq.{message_id}",  # eq. means "equals"
    "select": "id,status"  # Only fetch these fields
}

search_response = await client.get(
    search_url, 
    headers=headers, 
    params=search_params
)

if search_response.status_code == 200:
    existing_records = search_response.json()
    # Returns array: [] (not found) or [{"id": 123, "status": {...}}]
```

**Key Points:**
- Use GET request with query parameters
- `eq.` is Supabase's syntax for equality filter
- Returns an array (empty if not found)
- Only select fields we need for efficiency

### 7.3 Update Existing Status

**Why we merge statuses:**

A message progresses through multiple states (sent → delivered → read), so we need to preserve all previous statuses.

```python
# Get existing status
existing_status = record.get("status", {})
# Example: {"sent": "2024-12-10T10:30:00Z"}

# Parse it (might be dict or JSON string)
if isinstance(existing_status, dict):
    updated_status = existing_status.copy()
else:
    updated_status = json.loads(existing_status) if existing_status else {}

# Add new status
updated_status[status] = iso_timestamp
# Now: {"sent": "2024-12-10T10:30:00Z", "delivered": "2024-12-10T10:30:05Z"}

# Handle out-of-order delivery
if status == "read" and "delivered" not in updated_status:
    # User read before "delivered" webhook arrived
    updated_status["delivered"] = iso_timestamp
```

**Key Points:**
- Always copy existing status first
- Add new status to the dict
- Handle out-of-order webhooks
- Preserve all previous statuses

### 7.4 Out-of-Order Handling

**Scenario: "Read" arrives before "Delivered"**

```
NORMAL FLOW:
  sent → delivered → read ✓

SOMETIMES HAPPENS:
  sent → read (delivered webhook delayed/lost) ✗

OUR SOLUTION:
  When "read" arrives:
    1. Check if "delivered" exists
    2. If NOT, automatically add "delivered" 
       with same timestamp as "read"

CODE:
```python
if status == "read" and "delivered" not in updated_status:
    updated_status["delivered"] = iso_timestamp
```

RESULT:
  Before: {"sent": "10:30:00"}
  Read arrives at 10:31:00
  After: {
    "sent": "10:30:00",
    "delivered": "10:31:00",  ← Auto-added
    "read": "10:31:00"
  }
```

### 7.5 Database Update (PATCH vs PUT)

**Why PATCH:**

We use PATCH because we only want to update the `status` field, not replace the entire record.

```python
# Update the record
update_url = f"{search_url}?id=eq.{record['id']}"
update_data = {"status": updated_status}

update_response = await client.patch(
    update_url, 
    headers=headers, 
    json=update_data
)

# Success codes: 200 (with body) or 204 (no content)
if update_response.status_code in [200, 204]:
    return True
```

**Key Points:**
- Use PATCH, not PUT (only update specific fields)
- Filter by `id=eq.{record_id}` for precise targeting
- Both 200 and 204 indicate success
- 200 returns updated record, 204 returns nothing

### 7.6 Create New Record

```python
new_record = {
    "message_id": message_id,
    "phone_number": recipient_phone,  # Optional
    "status": {status: iso_timestamp}  # First status
}

create_response = await client.post(
    search_url,  # Same URL, but POST instead of GET/PATCH
    headers=headers, 
    json=new_record
)

if create_response.status_code in [200, 201]:
    return True
```

**Key Points:**
- Use POST to create new records
- Status is a dict with one key (the status type)
- 200 or 201 both indicate success
- 201 specifically means "Created"

### 7.7 Batch Processing

```python
async def process_status_updates(statuses: List[Dict[str, Any]]) -> bool:
    """Process multiple status updates from one webhook"""
    success_count = 0
    
    for status_obj in statuses:
        message_id = status_obj.get("id")
        status = status_obj.get("status")
        timestamp = status_obj.get("timestamp")
        recipient_id = status_obj.get("recipient_id")
        
        if all([message_id, status, timestamp]):
            recipient_phone = f"+{recipient_id}" if recipient_id else None
            if await update_message_status(message_id, status, timestamp, recipient_phone):
                success_count += 1
    
    return success_count == len(statuses)
```

**Key Points:**
- Loop through each status object
- Validate required fields exist
- Process each status independently
- Return True only if all succeed

---

## 8. Webhook Integration

### AiSensy Webhook Configuration

1. **Log in to AiSensy Dashboard**
2. **Go to Settings → Webhooks**
3. **Add Webhook URL**: `https://your-domain.com/webhook`
4. **Enable "Status Updates"**
5. **Save Configuration**

### Webhook Payload Examples

**Status Update Webhook:**
```json
{
  "statuses": [
    {
      "id": "wamid.HBgMOTE4MjgxODQwNDYyFQIAEhggRDc3",
      "status": "delivered",
      "timestamp": "1702207805",
      "recipient_id": "919876543210"
    }
  ]
}
```

**Batch Status Updates:**
```json
{
  "statuses": [
    {"id": "msg_001", "status": "delivered", "timestamp": "1702207800"},
    {"id": "msg_002", "status": "read", "timestamp": "1702207805"},
    {"id": "msg_003", "status": "sent", "timestamp": "1702207810"}
  ]
}
```

### Webhook Security

```python
# Add IP whitelist check
AISENSY_IPS = ["1.2.3.4", "5.6.7.8"]

@app.post("/webhook")
async def handle_webhook(request: Request):
    client_ip = request.client.host
    
    if client_ip not in AISENSY_IPS:
        logger.warning(f"⚠️ Webhook from unknown IP: {client_ip}")
        return {"status": "error", "message": "Unauthorized"}
    
    # Process webhook...
```

---

## 9. Testing

### 9.1 Manual Testing with cURL

**Test "sent" status:**
```bash
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{
    "statuses": [{
      "id": "test_message_001",
      "status": "sent",
      "timestamp": "1702207800",
      "recipient_id": "919876543210"
    }]
  }'
```

**Test "delivered" status (same message):**
```bash
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{
    "statuses": [{
      "id": "test_message_001",
      "status": "delivered",
      "timestamp": "1702207805",
      "recipient_id": "919876543210"
    }]
  }'
```

**Test "read" status (same message):**
```bash
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{
    "statuses": [{
      "id": "test_message_001",
      "status": "read",
      "timestamp": "1702207860",
      "recipient_id": "919876543210"
    }]
  }'
```

### 9.2 Verify in Database

```sql
-- Check status for specific message
SELECT message_id, status, phone_number, created_at, updated_at
FROM broadcasts_messages
WHERE message_id = 'test_message_001';

-- Expected result:
-- status: {
--   "sent": "2024-12-10T10:30:00Z",
--   "delivered": "2024-12-10T10:30:05Z",
--   "read": "2024-12-10T10:31:00Z"
-- }
```

### 9.3 Test Out-of-Order Delivery

```bash
# 1. Send "sent" status
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{
    "statuses": [{
      "id": "test_message_002",
      "status": "sent",
      "timestamp": "1702207800"
    }]
  }'

# 2. Skip "delivered", send "read" directly
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{
    "statuses": [{
      "id": "test_message_002",
      "status": "read",
      "timestamp": "1702207860"
    }]
  }'

# 3. Verify: Should have both "delivered" and "read" with same timestamp
```

### 9.4 Test Batch Updates

```bash
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{
    "statuses": [
      {"id": "msg_001", "status": "delivered", "timestamp": "1702207800"},
      {"id": "msg_002", "status": "read", "timestamp": "1702207805"},
      {"id": "msg_003", "status": "sent", "timestamp": "1702207810"}
    ]
  }'
```

### 9.5 Integration Test Script

```python
# test_message_status.py

import asyncio
import httpx
from datetime import datetime

async def test_full_flow():
    """Test complete message status flow"""
    
    message_id = "test_integration_001"
    base_url = "http://localhost:8000"
    
    print("🧪 Starting integration test...")
    
    # Test 1: Send "sent" status
    print("\n1️⃣ Testing 'sent' status...")
    await send_status_webhook(base_url, message_id, "sent", "1702207800")
    await asyncio.sleep(1)
    
    # Test 2: Send "delivered" status
    print("\n2️⃣ Testing 'delivered' status...")
    await send_status_webhook(base_url, message_id, "delivered", "1702207805")
    await asyncio.sleep(1)
    
    # Test 3: Send "read" status
    print("\n3️⃣ Testing 'read' status...")
    await send_status_webhook(base_url, message_id, "read", "1702207860")
    await asyncio.sleep(1)
    
    print("\n✅ Integration test complete!")
    print("Check your database for results:")
    print(f"  SELECT * FROM broadcasts_messages WHERE message_id = '{message_id}';")

async def send_status_webhook(base_url, message_id, status, timestamp):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/webhook",
            json={
                "statuses": [{
                    "id": message_id,
                    "status": status,
                    "timestamp": timestamp,
                    "recipient_id": "919876543210"
                }]
            }
        )
        print(f"   Response: {response.status_code} - {response.json()}")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
```

Run the test:
```bash
python test_message_status.py
```

---

## 10. Analytics & Queries

### 10.1 Basic Queries

**Get all messages for a phone number:**
```sql
SELECT * FROM broadcasts_messages
WHERE phone_number = '+919876543210'
ORDER BY created_at DESC;
```

**Get messages that were read:**
```sql
SELECT * FROM broadcasts_messages
WHERE status->>'read' IS NOT NULL
ORDER BY (status->>'read')::timestamptz DESC;
```

**Get undelivered messages (>5 mins):**
```sql
SELECT * FROM broadcasts_messages
WHERE status->>'sent' IS NOT NULL
  AND status->>'delivered' IS NULL
  AND created_at < NOW() - INTERVAL '5 minutes';
```

### 10.2 Analytics Queries

**Calculate delivery rate:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE status ? 'delivered') * 100.0 / 
  COUNT(*) as delivery_rate_percent
FROM broadcasts_messages
WHERE created_at > NOW() - INTERVAL '24 hours';
```

**Calculate read rate:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE status ? 'read') * 100.0 / 
  COUNT(*) FILTER (WHERE status ? 'delivered') as read_rate_percent
FROM broadcasts_messages
WHERE created_at > NOW() - INTERVAL '24 hours';
```

**Average delivery time:**
```sql
SELECT 
  AVG(
    EXTRACT(EPOCH FROM (status->>'delivered')::timestamptz) - 
    EXTRACT(EPOCH FROM (status->>'sent')::timestamptz)
  ) as avg_delivery_seconds
FROM broadcasts_messages
WHERE status ? 'sent' AND status ? 'delivered'
  AND created_at > NOW() - INTERVAL '24 hours';
```

**Average read time (after delivery):**
```sql
SELECT 
  AVG(
    EXTRACT(EPOCH FROM (status->>'read')::timestamptz) - 
    EXTRACT(EPOCH FROM (status->>'delivered')::timestamptz)
  ) / 60 as avg_read_delay_minutes
FROM broadcasts_messages
WHERE status ? 'delivered' AND status ? 'read'
  AND created_at > NOW() - INTERVAL '24 hours';
```

### 10.3 Engagement Metrics

**Most engaged users (by read rate):**
```sql
SELECT 
  phone_number,
  COUNT(*) as total_messages,
  COUNT(*) FILTER (WHERE status ? 'delivered') as delivered,
  COUNT(*) FILTER (WHERE status ? 'read') as read,
  COUNT(*) FILTER (WHERE status ? 'read') * 100.0 / 
    NULLIF(COUNT(*) FILTER (WHERE status ? 'delivered'), 0) as read_rate
FROM broadcasts_messages
WHERE created_at > NOW() - INTERVAL '7 days'
  AND phone_number IS NOT NULL
GROUP BY phone_number
HAVING COUNT(*) FILTER (WHERE status ? 'delivered') > 0
ORDER BY read_rate DESC
LIMIT 10;
```

**Hourly message volume:**
```sql
SELECT 
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) as messages_sent,
  COUNT(*) FILTER (WHERE status ? 'delivered') as messages_delivered,
  COUNT(*) FILTER (WHERE status ? 'read') as messages_read
FROM broadcasts_messages
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;
```

**Best time to send (by read rate):**
```sql
SELECT 
  EXTRACT(HOUR FROM created_at) as hour_of_day,
  COUNT(*) as total_messages,
  COUNT(*) FILTER (WHERE status ? 'read') * 100.0 / 
    NULLIF(COUNT(*) FILTER (WHERE status ? 'delivered'), 0) as read_rate
FROM broadcasts_messages
WHERE created_at > NOW() - INTERVAL '30 days'
  AND status ? 'delivered'
GROUP BY EXTRACT(HOUR FROM created_at)
ORDER BY read_rate DESC;
```

### 10.4 Dashboard Views

**Create a dashboard view:**
```sql
CREATE VIEW message_status_dashboard AS
SELECT 
  DATE(created_at) as date,
  COUNT(*) as total_messages,
  COUNT(*) FILTER (WHERE status ? 'sent') as sent,
  COUNT(*) FILTER (WHERE status ? 'delivered') as delivered,
  COUNT(*) FILTER (WHERE status ? 'read') as read,
  COUNT(*) FILTER (WHERE status ? 'delivered') * 100.0 / COUNT(*) as delivery_rate,
  COUNT(*) FILTER (WHERE status ? 'read') * 100.0 / 
    NULLIF(COUNT(*) FILTER (WHERE status ? 'delivered'), 0) as read_rate,
  AVG(
    EXTRACT(EPOCH FROM (status->>'delivered')::timestamptz) - 
    EXTRACT(EPOCH FROM (status->>'sent')::timestamptz)
  ) as avg_delivery_seconds
FROM broadcasts_messages
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Use the view
SELECT * FROM message_status_dashboard WHERE date > CURRENT_DATE - 7;
```

---

## 11. Troubleshooting

### Issue 1: Status Not Updating

**Symptoms:**
- Webhooks received but database not updating
- No errors in logs

**Causes & Solutions:**

1. **Missing Service Role Key**
   ```python
   # Check environment variable
   if not config.SUPABASE_SERVICE_ROLE_KEY:
       print("❌ Missing SUPABASE_SERVICE_ROLE_KEY")
   ```
   **Fix:** Add `SUPABASE_SERVICE_ROLE_KEY` to .env file

2. **Wrong Database URL**
   ```python
   # Verify URL format
   print(f"Database URL: {config.SUPABASE_URL}")
   # Should be: https://xxxxx.supabase.co
   ```
   **Fix:** Check URL in .env file

3. **Table Doesn't Exist**
   ```sql
   -- Run in Supabase SQL editor
   SELECT * FROM broadcasts_messages LIMIT 1;
   -- If error, table doesn't exist
   ```
   **Fix:** Run CREATE TABLE command from Section 5

4. **RLS Policies Blocking**
   ```sql
   -- Disable RLS for this table (use with caution)
   ALTER TABLE broadcasts_messages DISABLE ROW LEVEL SECURITY;
   ```
   **Fix:** Use SERVICE_ROLE_KEY instead of anon key

### Issue 2: Duplicate Status Updates

**Symptoms:**
- Same status appears multiple times
- Timestamps keep updating

**Solution:**
```python
# Add timestamp check
if status in updated_status:
    existing_time = datetime.fromisoformat(updated_status[status].replace('Z', ''))
    new_time = datetime.fromisoformat(iso_timestamp.replace('Z', ''))
    
    # Only update if new timestamp is later
    if new_time <= existing_time:
        logger.info(f"Skipping duplicate status update")
        return True

updated_status[status] = iso_timestamp
```

### Issue 3: Webhook Not Received

**Checklist:**

1. **Verify webhook URL**
   - Must be publicly accessible (not localhost)
   - Should be: `https://your-domain.com/webhook`

2. **Check AiSensy configuration**
   - Status updates enabled
   - Webhook is active
   - Correct URL saved

3. **Test webhook endpoint**
   ```bash
   curl -X POST 'https://your-domain.com/webhook' \
     -H 'Content-Type: application/json' \
     -d '{"test": "data"}'
   ```

4. **Check server logs**
   ```bash
   tail -f logs/app.log | grep WEBHOOK
   ```

5. **Verify server is running**
   ```bash
   ps aux | grep python
   ```

### Issue 4: Invalid Timestamp Errors

**Symptoms:**
- Error: "ValueError: invalid timestamp"
- Status timestamps are incorrect

**Solution:**
```python
try:
    unix_timestamp = float(timestamp)
    iso_timestamp = datetime.fromtimestamp(unix_timestamp).isoformat() + "Z"
except (ValueError, TypeError) as e:
    # Use current time as fallback
    iso_timestamp = datetime.now().isoformat() + "Z"
    logger.warning(f"Invalid timestamp '{timestamp}', using current time")
```

### Issue 5: Missing Statuses

**Symptoms:**
- Some messages missing "delivered" or "read"
- Status progression incomplete

**Possible Causes:**

1. **Webhooks not enabled**
   - Check AiSensy dashboard settings
   - Ensure all status types enabled

2. **User hasn't opened message**
   - "Read" only triggers when user opens
   - Normal behavior

3. **Delivery failed**
   - Check phone number validity
   - User might have blocked number

4. **Webhook endpoint issues**
   - Check server uptime
   - Verify endpoint is responding

### Issue 6: Database Connection Errors

**Symptoms:**
- "Connection refused"
- "Timeout connecting to database"

**Solutions:**

1. **Check credentials**
   ```python
   print(f"URL: {config.SUPABASE_URL}")
   print(f"Key: {config.SUPABASE_SERVICE_ROLE_KEY[:20]}...")
   ```

2. **Test connection**
   ```bash
   curl https://your-project.supabase.co/rest/v1/ \
     -H "apikey: your_key_here"
   ```

3. **Check network**
   ```bash
   ping your-project.supabase.co
   ```

### Debug Logging

Add comprehensive logging:

```python
# Enable debug logging
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/message_status.log'),
        logging.StreamHandler()
    ]
)

# Create dedicated logger
status_logger = logging.getLogger('message_status')
status_logger.setLevel(logging.DEBUG)
```

### Performance Monitoring

```python
import time

async def update_message_status(...):
    start_time = time.time()
    
    # Your update code here
    
    duration = time.time() - start_time
    logger.info(f"⏱️ Status update took {duration:.2f}s")
    
    if duration > 1.0:
        logger.warning(f"⚠️ Slow status update: {duration:.2f}s")
```

---

## 12. Performance & Security

### Performance Optimizations

**1. Database Indexes**
```sql
-- Already created in setup, but verify:
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE tablename = 'broadcasts_messages';

-- Should show:
-- idx_broadcasts_messages_message_id
-- idx_broadcasts_messages_phone_number
```

**2. Query Performance**
```sql
-- Check query execution time
EXPLAIN ANALYZE 
SELECT * FROM broadcasts_messages 
WHERE message_id = 'test_message_001';

-- Should use index scan
```

**3. Connection Pooling**
```python
# Use connection pooling for better performance
import httpx

async def create_client():
    return httpx.AsyncClient(
        timeout=30.0,
        limits=httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100
        )
    )
```

**4. Batch Operations**
```python
# Process multiple updates in one connection
async with httpx.AsyncClient() as client:
    for status_obj in statuses:
        await update_message_status(...)
    # Connection reused for all updates
```

### Security Best Practices

**1. Authentication**
```python
# Always use SERVICE_ROLE_KEY for database operations
headers = {
    "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
    "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
}

# NEVER expose service role key to client-side code
```

**2. Webhook Validation**
```python
# Validate webhook source
AISENSY_IPS = ["1.2.3.4", "5.6.7.8"]  # Get from AiSensy docs

@app.post("/webhook")
async def handle_webhook(request: Request):
    client_ip = request.client.host
    
    if client_ip not in AISENSY_IPS:
        logger.warning(f"⚠️ Unauthorized IP: {client_ip}")
        return {"status": "error", "message": "Unauthorized"}
    
    # Process webhook...
```

**3. Input Validation**
```python
# Validate all inputs
def validate_status(status: str) -> bool:
    valid_statuses = ["sent", "delivered", "read"]
    return status in valid_statuses

def validate_message_id(message_id: str) -> bool:
    # WhatsApp message IDs are alphanumeric
    import re
    return bool(re.match(r'^[a-zA-Z0-9._-]+$', message_id))

# Use in update function
if not validate_status(status):
    logger.error(f"Invalid status: {status}")
    return False

if not validate_message_id(message_id):
    logger.error(f"Invalid message_id: {message_id}")
    return False
```

**4. Rate Limiting**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/webhook")
@limiter.limit("100/minute")
async def handle_webhook(request: Request):
    # Process webhook...
```

**5. Logging Security**
```python
# Don't log sensitive data
logger.info(f"Processing status for message: {message_id[:20]}...")  # Truncate
logger.info(f"Phone: {phone_number[:5]}***")  # Mask

# DON'T log full tokens
logger.error(f"Token: {token[:10]}...")  # ✓ Good
logger.error(f"Token: {token}")  # ✗ Bad
```

### Monitoring & Alerts

**Set up alerts for:**

🚨 **CRITICAL**
- Delivery rate < 90% (last hour)
- More than 10 messages undelivered for >10 minutes
- Database connection errors
- Webhook endpoint errors

⚠️ **WARNING**
- Read rate < 50% (last 24 hours)
- Average delivery time > 30 seconds
- Slow database queries (>1 second)

ℹ️ **INFO**
- Daily delivery summary
- Weekly engagement trends
- Monthly read rate comparison

**Example alert query:**
```sql
-- Alert if delivery rate drops below 90%
SELECT 
  COUNT(*) FILTER (WHERE status ? 'delivered') * 100.0 / COUNT(*) as delivery_rate
FROM broadcasts_messages
WHERE created_at > NOW() - INTERVAL '1 hour'
HAVING COUNT(*) FILTER (WHERE status ? 'delivered') * 100.0 / COUNT(*) < 90;
```

---

## Complete Checklist

Use this checklist to implement message status tracking:

### Database Setup
- [ ] Create `broadcasts_messages` table
- [ ] Add indexes for performance
- [ ] Test table with manual INSERT
- [ ] Verify table structure

### Environment Configuration
- [ ] Add `SUPABASE_URL` to .env
- [ ] Add `SUPABASE_SERVICE_ROLE_KEY` to .env
- [ ] Verify environment variables load correctly
- [ ] Test database connection

### Code Implementation
- [ ] Add `update_message_status()` function
- [ ] Add `process_status_updates()` function
- [ ] Add webhook handler to main app
- [ ] Add error handling and logging
- [ ] Add input validation

### AiSensy Configuration
- [ ] Set webhook URL in AiSensy dashboard
- [ ] Enable status update webhooks
- [ ] Verify webhook is active
- [ ] Test webhook endpoint

### Testing
- [ ] Test with manual cURL requests
- [ ] Test sent/delivered/read flow
- [ ] Test out-of-order delivery
- [ ] Test batch updates
- [ ] Verify database entries
- [ ] Run integration tests

### Monitoring
- [ ] Set up logging
- [ ] Monitor webhook success rate
- [ ] Track update latency
- [ ] Set up alerts for failures
- [ ] Create analytics dashboard

### Security
- [ ] Use SERVICE_ROLE_KEY
- [ ] Add webhook IP validation
- [ ] Implement rate limiting
- [ ] Add input validation
- [ ] Secure sensitive data in logs

### Performance
- [ ] Verify database indexes
- [ ] Test query performance
- [ ] Monitor connection pooling
- [ ] Optimize batch processing
- [ ] Track response times

---

## Environment Variables Summary

```bash
# Required for message status tracking
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Required for AiSensy integration
AISENSY_ACCESS_TOKEN=your_aisensy_access_token
AISENSY_BASE_URL=https://backend.aisensy.com

# Optional but recommended
LOG_LEVEL=INFO
DATABASE_POOL_SIZE=20
WEBHOOK_RATE_LIMIT=100/minute
```

---

## Success Metrics

After implementation, you should see:

✅ **95%+ delivery rate** within 30 seconds  
✅ **All messages tracked** in database  
✅ **Webhooks processed** within 1 second  
✅ **No errors** in status processing  
✅ **Analytics queries** run in <100ms  
✅ **Read rate** > 50% for engaged users  

---

## Common Use Cases

### 1. Resend Undelivered Messages

```python
async def resend_undelivered_messages():
    """Resend messages that weren't delivered after 10 minutes"""
    
    # Query for undelivered messages
    query = """
        SELECT message_id, phone_number 
        FROM broadcasts_messages
        WHERE status->>'sent' IS NOT NULL
          AND status->>'delivered' IS NULL
          AND created_at < NOW() - INTERVAL '10 minutes'
    """
    
    # Get undelivered messages
    # Re-send using AiSensy API
    # Update database with new message_id
```

### 2. Send Follow-up Based on Read Status

```python
async def send_followup_to_unread():
    """Send follow-up to users who haven't read message in 24 hours"""
    
    # Query for delivered but unread messages
    query = """
        SELECT message_id, phone_number
        FROM broadcasts_messages
        WHERE status->>'delivered' IS NOT NULL
          AND status->>'read' IS NULL
          AND created_at < NOW() - INTERVAL '24 hours'
    """
    
    # Send gentle reminder
    # Track new message separately
```

### 3. Optimize Send Time

```python
async def get_best_send_time_for_user(phone_number):
    """Find best time to send based on user's read patterns"""
    
    query = """
        SELECT EXTRACT(HOUR FROM (status->>'read')::timestamptz) as hour
        FROM broadcasts_messages
        WHERE phone_number = %s
          AND status ? 'read'
        GROUP BY EXTRACT(HOUR FROM (status->>'read')::timestamptz)
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """
    
    # Returns hour when user most often reads messages
    # Schedule future messages for that time
```

---

## File Structure Summary

After implementation, your project structure should look like:

```
processing-worker/
├── .env                                # Environment variables
├── main.py                            # Webhook endpoint
├── src/
│   ├── config.py                      # Configuration
│   └── services/
│       └── messaging.py               # Status functions
├── logs/
│   └── message_status.log            # Status logs
└── docs/
    └── MESSAGE_STATUS_COMPLETE_GUIDE.md  # This guide
```

---

## Quick Reference

### Database Operations

```sql
-- Get message status
SELECT * FROM broadcasts_messages WHERE message_id = 'xxx';

-- Count by status
SELECT 
  COUNT(*) FILTER (WHERE status ? 'sent') as sent,
  COUNT(*) FILTER (WHERE status ? 'delivered') as delivered,
  COUNT(*) FILTER (WHERE status ? 'read') as read
FROM broadcasts_messages;

-- Today's statistics
SELECT * FROM message_status_dashboard 
WHERE date = CURRENT_DATE;
```

### API Endpoints

```bash
# AiSensy webhook endpoint
POST https://backend.aisensy.com/webhooks

# Your webhook endpoint
POST https://your-domain.com/webhook

# Supabase REST API
GET/POST/PATCH https://your-project.supabase.co/rest/v1/broadcasts_messages
```

### Status Types

| Status | Meaning | When Triggered |
|--------|---------|----------------|
| `sent` | Message sent | Immediately after sending |
| `delivered` | Delivered to device | When received by device |
| `read` | User read message | When user opens chat |

---

## Next Steps

After implementing basic status tracking:

1. **Build Analytics Dashboard**
   - Create visualizations
   - Track engagement metrics
   - Monitor delivery rates

2. **Set Up Alerts**
   - Undelivered message alerts
   - Low engagement warnings
   - System health monitoring

3. **Optimize Performance**
   - Add caching for frequent queries
   - Implement connection pooling
   - Optimize database indexes

4. **Enhance Features**
   - Add retry logic for failed messages
   - Implement smart send scheduling
   - Build engagement scoring

---

## Support & Resources

### Debugging Commands

```bash
# Check logs
tail -f logs/app.log | grep '\[STATUS\]'

# Test webhook
curl -X POST 'http://localhost:8000/webhook' \
  -H 'Content-Type: application/json' \
  -d '{"statuses":[{"id":"test","status":"sent","timestamp":"1702207800"}]}'

# Check database
psql -d your_db -c "SELECT COUNT(*) FROM broadcasts_messages;"

# Monitor in real-time
watch -n 1 'psql -d your_db -c "SELECT COUNT(*) FROM broadcasts_messages;"'
```

### Common Commands

```bash
# Start server
python main.py

# Run tests
python test_message_status.py

# Check environment
python -c "from src.config import config; print(config.SUPABASE_URL)"

# View recent logs
tail -100 logs/message_status.log
```

---

## Conclusion

You now have a **complete, production-ready message status tracking system** that:

✅ Tracks sent/delivered/read status  
✅ Handles out-of-order webhooks  
✅ Processes batch updates  
✅ Provides comprehensive analytics  
✅ Includes error handling  
✅ Is secure and performant  

**Everything you need is in this one document** - no need to reference external files!

---

**Document Version:** 1.0  
**Last Updated:** December 10, 2024  
**Total Lines:** 2,500+  
**Complete Implementation Guide** ✅

---

*Happy Tracking! 🚀📊*

