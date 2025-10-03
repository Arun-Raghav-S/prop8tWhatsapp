# Area Expert API Integration

## Overview
This document explains how the Area Expert API is integrated into the WhatsApp agent system to automatically trigger when users provide their location and transaction type preferences.

## What Was Implemented

### 1. New Service: `area_expert_service.py`
Located at: `src/services/area_expert_service.py`

**Purpose:** Handles asynchronous calls to the area expert API without blocking the main conversation flow.

**Key Features:**
- ✅ Fully asynchronous and non-blocking
- ✅ Automatic deduplication to prevent multiple calls for same interaction
- ✅ Comprehensive error handling that won't break the main flow
- ✅ Detailed logging for debugging
- ✅ Memory-efficient with automatic cleanup of old tracking data

**API Endpoint:**
```
POST https://wpxcvnipnmdvdhrnlfed.supabase.co/functions/v1/info_area_expert
```

**Payload Structure:**
```json
{
  "area": "Dubai Marina",
  "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
  "whatsapp_interaction_id": "1e484b88-8862-4164-b69d-f6bd81de2d92",
  "lead_id": "610bd59b-f297-4bd7-98c4-80cafca1240b",
  "rent_buy": "rent",
  "whatsapp_business_account": "543107385407042"
}
```

### 2. Enhanced `agent_history.py`
**New Features:**
- ✅ Returns `lead_id` and `whatsapp_interaction_id` from API responses
- ✅ Stores latest IDs in memory for retrieval
- ✅ Enhanced logging to display response IDs
- ✅ New method `get_latest_ids()` to retrieve stored IDs

**What Changed:**
```python
# Before: No return value
async def update_agent_history(...):
    # Updates history
    
# After: Returns IDs
async def update_agent_history(...) -> tuple[Optional[str], Optional[str]]:
    # Updates history and returns (lead_id, whatsapp_interaction_id)
```

### 3. Enhanced `main.py`
**New Function:** `_handle_post_response_updates()`

This function:
1. Updates agent history and gets back `lead_id` and `whatsapp_interaction_id`
2. Extracts user requirements (area, transaction type) from session
3. Triggers area expert API if requirements are met
4. Runs completely in background without blocking conversation

**Integration Point:**
After every successful agent response, the system now:
```python
asyncio.create_task(_handle_post_response_updates(
    text_message=text_message,
    agent_response=agent_response,
    user_number=user_number,
    whatsapp_business_account=whatsapp_business_account,
    org_id=org_id,
    user_name=customer_name,
    session=session
))
```

## How It Works

### Flow Diagram
```
User Message → Agent Processing → Response Sent
                                        ↓
                                  (Background Tasks)
                                        ↓
                        ┌───────────────┴───────────────┐
                        ↓                               ↓
              Update Agent History              Extract Requirements
                        ↓                               ↓
            Get lead_id & interaction_id      Get area & rent/buy
                        ↓                               ↓
                        └───────────────┬───────────────┘
                                        ↓
                            Check if ready (area + rent/buy)
                                        ↓
                                  ┌─────┴─────┐
                                  ↓           ↓
                              Ready        Not Ready
                                  ↓           ↓
                        Trigger Area Expert  Skip
                                  ↓
                          Log Response
```

### Trigger Conditions
The area expert API is triggered when:
1. ✅ User has provided a location/area
2. ✅ User has specified buy or rent
3. ✅ Agent history has been successfully updated
4. ✅ Not already triggered for this interaction (deduplication)

### Example Scenario

**User Conversation:**
```
User: "I'm looking for apartments"
Bot: "To find the perfect property for you, I need to know:
      1️⃣ Are you looking to buy or rent?
      2️⃣ Which area in Dubai?"

User: "I want to rent in Dubai Marina"
Bot: "Great! Let me find rental apartments in Dubai Marina..."

[Background: Area Expert API is triggered]
```

**What Happens Behind the Scenes:**
1. User says "rent in Dubai Marina"
2. Agent extracts: `location = "Dubai Marina"`, `transaction_type = "rent"`
3. Agent sends response to user
4. Background task starts:
   - Update agent history → Get `lead_id` and `whatsapp_interaction_id`
   - Check requirements → Found area="Dubai Marina", rent_buy="rent"
   - Trigger area expert API with all parameters
5. Area expert processes in parallel (doesn't block conversation)

## Logging

### What You'll See in Logs

**When Requirements Not Met:**
```
🔍 [AREA_EXPERT_TRIGGER] Not ready - area: None, transaction_type: rent
```

**When Triggering:**
```
🎯 [AREA_EXPERT_TRIGGER] Area: Dubai Marina, Type: rent
✓ [AREA_EXPERT] Requirements met, triggering area expert
🚀 [AREA_EXPERT] Launched background task for area: Dubai Marina, type: rent
📍 [AREA_EXPERT] Starting area expert API call
📍 [AREA_EXPERT] Area: Dubai Marina
📍 [AREA_EXPERT] Rent/Buy: rent
📍 [AREA_EXPERT] Org ID: 4462c6c4-3d71-4b4d-ace7-1659ebc8424a
📍 [AREA_EXPERT] Lead ID: 610bd59b-f297-4bd7-98c4-80cafca1240b
📍 [AREA_EXPERT] WhatsApp Interaction ID: 1e484b88-8862-4164-b69d-f6bd81de2d92
📍 [AREA_EXPERT] Response Status: 200
📍 [AREA_EXPERT] Response Body: {...}
✅ [AREA_EXPERT] Successfully called area expert API
```

**If Error Occurs (Non-Breaking):**
```
⚠️ [AREA_EXPERT] Error calling area expert API (non-critical): <error message>
⚠️ [POST_RESPONSE_UPDATES] Error in background updates: <error message>
```

## Error Handling

### Robustness Features
1. **Non-Blocking:** All area expert calls run in background tasks
2. **Error Isolation:** Errors in area expert won't break conversation flow
3. **Timeout Protection:** 30-second timeout on API calls
4. **Graceful Degradation:** If area expert fails, conversation continues normally
5. **Deduplication:** Won't trigger multiple times for same interaction

### What Happens on Error
- ⚠️ Error is logged with details
- ✅ User conversation continues normally
- ✅ No error message sent to user
- ✅ Next interaction will retry if conditions met

## Configuration

### Environment Variables Required
All existing environment variables are used:
- `SUPABASE_ANON_KEY` - For agent history updates
- `OPENAI_API_KEY` - For AI processing
- Organization ID and WhatsApp business account from session

### No New Configuration Needed
The area expert API URL is hardcoded as specified:
```python
self.api_url = "https://wpxcvnipnmdvdhrnlfed.supabase.co/functions/v1/info_area_expert"
```

## Testing

### Manual Testing Steps
1. Start a conversation with the WhatsApp agent
2. Provide transaction type: "I want to rent"
3. Provide location: "in Dubai Marina"
4. Check logs for area expert trigger
5. Verify API was called with correct parameters

### Expected Behavior
- ✅ Area expert triggered once per conversation when requirements met
- ✅ No duplicate calls for same interaction
- ✅ API called with correct area, rent_buy, org_id, lead_id, interaction_id
- ✅ No impact on conversation flow even if API fails

## Maintenance

### Memory Management
- Deduplication set automatically cleans up after 1000 entries
- Keeps last 500 entries to prevent memory leaks
- No manual cleanup required

### Monitoring
Monitor these log patterns:
- `🎯 [AREA_EXPERT_TRIGGER]` - When trigger is attempted
- `✅ [AREA_EXPERT]` - Successful API calls
- `⚠️ [AREA_EXPERT]` - Warnings/errors (non-critical)

## Summary

✅ **Implemented:** Complete area expert integration  
✅ **Non-Blocking:** Runs in parallel without affecting conversation  
✅ **Robust:** Comprehensive error handling and logging  
✅ **Efficient:** Deduplication and memory management  
✅ **Production-Ready:** Safe to deploy, won't break existing flow  

The system now automatically enriches lead data with area expertise whenever users specify their location and transaction type preferences!

