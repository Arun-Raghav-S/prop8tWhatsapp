# API Documentation - WhatsApp Agent System

Complete reference of all external APIs called by the WhatsApp Agent system.

---

## Table of Contents

1. [Property Data APIs](#1-property-data-apis)
2. [WhatsApp Messaging APIs](#2-whatsapp-messaging-apis)
3. [Property Location & Brochure APIs](#3-property-location--brochure-apis)
4. [Visit Scheduling API](#4-visit-scheduling-api)
5. [Agent History API](#5-agent-history-api)
6. [Area Expert API](#6-area-expert-api)
7. [Organization Metadata API](#7-organization-metadata-api)
8. [User Data & Logging APIs](#8-user-data--logging-apis)
   - [Log AI Message Reply](#81-log-ai-message-reply)
   - [Fetch User History](#82-fetch-user-history)

---

## 1. Property Data APIs

### 1.1 Get Property Details (Supabase REST API)

**Purpose:** Fetch detailed property information by property ID

**Called In:** `processing-worker/tools/property_details_tool.py`

**Endpoint:**
```
GET https://auth.propzing.com/rest/v1/property_vectorstore
```

**Headers:**
```json
{
  "apikey": "{SUPABASE_SERVICE_ROLE_KEY}",
  "Authorization": "Bearer {SUPABASE_SERVICE_ROLE_KEY}",
  "Content-Type": "application/json"
}
```

**Query Parameters:**
- `original_property_id=eq.{property_id}` - Filter by property ID
- `select=*` - Select all fields

**Alternative Query (if first fails):**
- `id=eq.{property_id}` - Filter by id field

**CURL Example:**
```bash
curl -X GET "https://auth.propzing.com/rest/v1/property_vectorstore?original_property_id=eq.YOUR_PROPERTY_ID&select=*" \
  -H "apikey: YOUR_SUPABASE_KEY" \
  -H "Authorization: Bearer YOUR_SUPABASE_KEY" \
  -H "Content-Type: application/json"
```

**Response Example:**
```json
[
  {
    "id": "abc123",
    "original_property_id": "abc123",
    "title": "Luxury 2BR Apartment",
    "bedrooms": 2,
    "bathrooms": 2,
    "bua_sqft": 1200,
    "sale_price_aed": 1500000,
    "building_name": "Marina Heights",
    "address": "{\"locality\": \"Dubai Marina\", \"city\": \"Dubai\", ...}",
    "features": ["Balcony", "Gym Access"],
    "amenities": ["Swimming Pool", "Parking"]
  }
]
```

---

## 2. WhatsApp Messaging APIs

### 2.1 Send Text Message (AiSensy Direct API)

**Purpose:** Send text messages to WhatsApp users

**Called In:** `processing-worker/src/services/messaging.py` (function: `send_message_via_aisensy`)

**Endpoint:**
```
POST https://backend.aisensy.com/direct-apis/t1/messages
```

**Headers:**
```json
{
  "Authorization": "Bearer {AISENSY_ACCESS_TOKEN}",
  "Content-Type": "application/json",
  "Accept": "application/json, application/xml"
}
```

**Request Body:**
```json
{
  "to": "919182818404",
  "type": "text",
  "recipient_type": "individual",
  "text": {
    "body": "Your message text here"
  }
}
```

**CURL Example:**
```bash
curl -X POST "https://backend.aisensy.com/direct-apis/t1/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, application/xml" \
  -d '{
    "to": "919182818404",
    "type": "text",
    "recipient_type": "individual",
    "text": {
      "body": "Hello from the agent!"
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "message_id": "wamid.HBgMOTE..."
}
```

---

### 2.2 Send Image Message (AiSensy Direct API)

**Purpose:** Send image messages to WhatsApp users

**Called In:** `processing-worker/src/services/messaging.py` (function: `send_image_via_aisensy`)

**Endpoint:**
```
POST https://backend.aisensy.com/direct-apis/t1/messages
```

**Headers:**
```json
{
  "Authorization": "Bearer {AISENSY_ACCESS_TOKEN}",
  "Content-Type": "application/json",
  "Accept": "application/json, application/xml"
}
```

**Request Body:**
```json
{
  "to": "919182818404",
  "type": "image",
  "image": {
    "caption": "Property Image",
    "link": "https://example.com/image.jpg"
  }
}
```

**CURL Example:**
```bash
curl -X POST "https://backend.aisensy.com/direct-apis/t1/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "919182818404",
    "type": "image",
    "image": {
      "caption": "Check out this property!",
      "link": "https://example.com/property.jpg"
    }
  }'
```

---

### 2.3 Send Document Message (AiSensy Direct API)

**Purpose:** Send document/PDF messages to WhatsApp users

**Called In:** `processing-worker/src/services/messaging.py` (function: `send_document_via_aisensy`)

**Endpoint:**
```
POST https://backend.aisensy.com/direct-apis/t1/messages
```

**Request Body:**
```json
{
  "to": "919182818404",
  "type": "document",
  "document": {
    "caption": "Property Brochure",
    "link": "https://example.com/brochure.pdf",
    "filename": "property_brochure.pdf"
  }
}
```

**CURL Example:**
```bash
curl -X POST "https://backend.aisensy.com/direct-apis/t1/messages" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "919182818404",
    "type": "document",
    "document": {
      "caption": "Your property brochure",
      "link": "https://example.com/docs/brochure.pdf",
      "filename": "luxury_apartment_brochure.pdf"
    }
  }'
```

---

### 2.4 Mark Message as Read (AiSensy Direct API)

**Purpose:** Mark WhatsApp messages as read and show typing indicator

**Called In:** `processing-worker/src/services/messaging.py` (function: `mark_message_as_read`)

**Endpoint:**
```
POST https://backend.aisensy.com/direct-apis/t1/mark-read
```

**Headers:**
```json
{
  "Accept": "application/json, application/xml",
  "Authorization": "Bearer {AISENSY_ACCESS_TOKEN}",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "messageId": "wamid.HBgMOTE4MjgxODQwNDYyFQIAEhggRDc3...",
  "showTypingIndicator": "true"
}
```

**CURL Example:**
```bash
curl -X POST "https://backend.aisensy.com/direct-apis/t1/mark-read" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messageId": "wamid.HBgMOTE4MjgxODQwNDYyFQIAEhggRDc3...",
    "showTypingIndicator": "true"
  }'
```

---

### 2.5 Single Image Carousel (Supabase Edge Function)

**Purpose:** Send a single property carousel card with image

**Called In:** `processing-worker/main.py` (function: `_call_single_image_carousel_api`)

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/single_image_carousel
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {SUPABASE_SERVICE_ROLE_KEY}"
}
```

**Request Body:**
```json
{
  "id": "property-uuid",
  "whatsapp_account_number": "543107385407043",
  "send_to": "919182818404",
  "isProperty": true
}
```

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/single_image_carousel" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SERVICE_ROLE_KEY" \
  -d '{
    "id": "abc-123-property-id",
    "whatsapp_account_number": "543107385407043",
    "send_to": "919182818404",
    "isProperty": true
  }'
```

---

### 2.6 WhatsApp Carousel Broadcast (Multiple Properties)

**Purpose:** Send carousel with multiple property cards (up to 10)

**Called In:** `processing-worker/tools/whatsapp_carousel_tool.py`

**Endpoint:**
```
POST https://dsakezvdiwmoobugchgu.supabase.co/functions/v1/whatsapp_carousel_broadcast
```

**Headers:**
```json
{
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "whatsapp_business_number": "543107385407043",
  "to": "919182818404",
  "property_ids": [
    "property-id-1",
    "property-id-2",
    "property-id-3"
  ]
}
```

**CURL Example:**
```bash
curl -X POST "https://dsakezvdiwmoobugchgu.supabase.co/functions/v1/whatsapp_carousel_broadcast" \
  -H "Content-Type: application/json" \
  -d '{
    "whatsapp_business_number": "543107385407043",
    "to": "919182818404",
    "property_ids": ["prop1", "prop2", "prop3"]
  }'
```

---

## 3. Property Location & Brochure APIs

### 3.1 Send Location or Brochure

**Purpose:** Send interactive location map or property brochure to user

**Called In:** 
- `processing-worker/tools/property_location_service.py`
- `processing-worker/tools/smart_location_assistant.py`

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/send_brochure_location
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {SERVICE_ROLE_KEY}",
  "Cookie": "__cf_bm=6o8HOhMjeo4RWkHFWVjyQ7fGiB.FvyPVTv9u8xPhztA-1753794322-1.0.1.1-Mk_vIRYRXR.kF6J.wOINfroBfc_ExfYduSi3MJLtbGxCJP2kmoZBedMh5c9wZU8Cf.w.4P0BZxkA9e8X1_K_KS9zQiVTdGjVxy6riHbZTGA"
}
```

**Request Body:**
```json
{
  "project_id": "property-uuid",
  "whatsapp_account_number": "543107385407043",
  "send_to": "919182818404",
  "type": "location",
  "isProperty": true,
  "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a"
}
```

**Note:** `type` can be either `"location"` or `"brochure"`

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/send_brochure_location" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SERVICE_KEY" \
  -d '{
    "project_id": "abc-property-123",
    "whatsapp_account_number": "543107385407043",
    "send_to": "919182818404",
    "type": "location",
    "isProperty": true,
    "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a"
  }'
```

**For Brochure:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/send_brochure_location" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SERVICE_KEY" \
  -d '{
    "project_id": "abc-property-123",
    "whatsapp_account_number": "543107385407043",
    "send_to": "919182818404",
    "type": "brochure",
    "isProperty": true,
    "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a"
  }'
```

---

### 3.2 Find Nearest Places

**Purpose:** Find nearby places (hospitals, schools, malls, etc.) near a property

**Called In:** `processing-worker/tools/location_tools.py`

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/whatsapp_agency_tools
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {SUPABASE_ANON_KEY}"
}
```

**Request Body:**
```json
{
  "action": "findNearestPlace",
  "query": "hospital",
  "location": "25.0772,55.1328",
  "k": 3
}
```

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/whatsapp_agency_tools" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{
    "action": "findNearestPlace",
    "query": "hospital",
    "location": "25.0772,55.1328",
    "k": 3
  }'
```

**Response Example:**
```json
{
  "nearestPlaces": [
    {
      "name": "Dubai Healthcare City Hospital",
      "address": "Al Razi Building 64, Dubai",
      "rating": 4.5,
      "types": ["hospital", "health"]
    },
    {
      "name": "Emirates Hospital",
      "address": "Jumeirah Beach Road, Dubai",
      "rating": 4.3,
      "types": ["hospital", "health"]
    }
  ]
}
```

---

### 3.3 Calculate Route

**Purpose:** Calculate route and directions between two locations

**Called In:** `processing-worker/tools/location_tools.py`

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/whatsapp_agency_tools
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {SUPABASE_ANON_KEY}"
}
```

**Request Body:**
```json
{
  "action": "calculateRoute",
  "origin": "Marina Heights, Dubai Marina",
  "destination": "Dubai Mall, Downtown Dubai"
}
```

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/whatsapp_agency_tools" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{
    "action": "calculateRoute",
    "origin": "Marina Heights, Dubai Marina",
    "destination": "Dubai Mall, Downtown Dubai"
  }'
```

---

## 4. Visit Scheduling API

**Purpose:** Schedule property viewing appointments for users

**Called In:** `processing-worker/tools/visit_scheduling_tool.py`

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/visit_user_manager
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {SUPABASE_SERVICE_ROLE_KEY}"
}
```

**Request Body:**
```json
{
  "user_name": "John Doe",
  "user_number": "+919182818404",
  "date_and_time": "2024-12-25 14:00",
  "record_id": "property-uuid",
  "isProperty": true
}
```

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/visit_user_manager" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_SERVICE_KEY" \
  -d '{
    "user_name": "John Doe",
    "user_number": "+919182818404",
    "date_and_time": "2024-12-25 14:00",
    "record_id": "abc-property-123",
    "isProperty": true
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Visit scheduled successfully",
  "visit_id": "visit-123"
}
```

---

## 5. Agent History API

**Purpose:** Update and store conversation history between agent and users

**Called In:** `processing-worker/src/services/agent_history.py`

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/update_whatsappagencyagent_history
```

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer {SUPABASE_ANON_KEY}"
}
```

**Request Body:**
```json
{
  "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
  "whatsapp_business_account": "543107385407043",
  "user_number": "+919182818404",
  "phone_number": "+919182818404",
  "user_name": "John Doe",
  "chat_history": [
    {
      "role": "user",
      "content": "I want to buy a 2BR apartment in Marina",
      "timestamp": "2024-01-15T10:30:00Z",
      "type": "text"
    },
    {
      "role": "assistant",
      "content": "Great! I found 15 properties matching your criteria...",
      "timestamp": "2024-01-15T10:30:05Z",
      "type": "text"
    }
  ]
}
```

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/update_whatsappagencyagent_history" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -d '{
    "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
    "whatsapp_business_account": "543107385407043",
    "user_number": "+919182818404",
    "phone_number": "+919182818404",
    "user_name": "John Doe",
    "chat_history": [
      {
        "role": "user",
        "content": "Looking for apartments",
        "timestamp": "2024-01-15T10:30:00Z",
        "type": "text"
      }
    ]
  }'
```

**Response:**
```json
{
  "success": true,
  "lead_id": "lead-uuid-123",
  "whatsapp_interaction_id": "interaction-uuid-456"
}
```

---

## 6. Area Expert API

**Purpose:** Trigger area expert service for location-based property insights

**Called In:** `processing-worker/src/services/area_expert_service.py`

**Endpoint:**
```
POST https://wpxcvnipnmdvdhrnlfed.supabase.co/functions/v1/info_area_expert
```

**Headers:**
```json
{
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "area": "Dubai Marina",
  "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
  "whatsapp_interaction_id": "interaction-uuid",
  "lead_id": "lead-uuid",
  "rent_buy": "rent",
  "whatsapp_business_account": "543107385407043"
}
```

**Note:** `rent_buy` must be either `"rent"` or `"buy"`

**CURL Example:**
```bash
curl -X POST "https://wpxcvnipnmdvdhrnlfed.supabase.co/functions/v1/info_area_expert" \
  -H "Content-Type: application/json" \
  -d '{
    "area": "Dubai Marina",
    "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
    "whatsapp_interaction_id": "interaction-123",
    "lead_id": "lead-456",
    "rent_buy": "rent",
    "whatsapp_business_account": "543107385407043"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Area expert triggered successfully"
}
```

---

## 7. Organization Metadata API

**Purpose:** Fetch organization details and metadata for WhatsApp business accounts

**Called In:** `processing-worker/src/services/messaging.py`

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/whatsapp_agency_tools
```

**Headers:**
```json
{
  "Authorization": "Bearer {SUPABASE_ANON_KEY}",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "action": "fetchOrgMetadata",
  "user_number": "+919182818404",
  "whatsapp_business_account": "543107385407043"
}
```

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/whatsapp_agency_tools" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "fetchOrgMetadata",
    "user_number": "+919182818404",
    "whatsapp_business_account": "543107385407043"
  }'
```

**Response:**
```json
{
  "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
  "org_name": "Propzing Real Estate",
  "aisensy_access_token": "token-here",
  "settings": {
    "max_properties_per_search": 10
  }
}
```

---

## 8. User Data & Logging APIs

### 8.1 Log AI Message Reply

**Purpose:** Log all AI agent replies for tracking and analytics

**Called In:** `processing-worker/src/services/messaging.py` (function: `log_ai_reply_async`)

**Endpoint:**
```
POST https://auth.propzing.com/functions/v1/log-message
```

**Headers:**
```json
{
  "Authorization": "Bearer {SUPABASE_ANON_KEY}",
  "Content-Type": "application/json"
}
```

**Request Body:**
```json
{
  "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
  "lead_id": "456e7890-e89b-12d3-a456-426614174001",
  "whatsapp_agent_id": "543107385407043",
  "category": "AI_REPLY",
  "template_name": "ai_response_template",
  "to_phone": "+971501234567",
  "whatsapp_interaction_id": "23j87842352234"
}
```

**Note:** 
- `category` is always `"AI_REPLY"` for AI agent responses
- `template_name` is always `"ai_response_template"`
- `whatsapp_agent_id` is the WhatsApp business account ID
- This API is called asynchronously in the background and does not block the main conversation flow

**CURL Example:**
```bash
curl -X POST "https://auth.propzing.com/functions/v1/log-message" \
  -H "Authorization: Bearer YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
    "lead_id": "456e7890-e89b-12d3-a456-426614174001",
    "whatsapp_agent_id": "543107385407043",
    "category": "AI_REPLY",
    "template_name": "ai_response_template",
    "to_phone": "+971501234567",
    "whatsapp_interaction_id": "23j87842352234"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "AI reply logged successfully"
}
```

---

### 8.2 Fetch User History (Supabase REST API)

**Purpose:** Retrieve existing user conversation history and preferences

**Called In:** `processing-worker/src/services/user_data_service.py`

**Endpoint:**
```
GET https://auth.propzing.com/rest/v1/whatsapp_agency_agent_history
```

**Headers:**
```json
{
  "Authorization": "Bearer {SUPABASE_SERVICE_ROLE_KEY}",
  "apikey": "{SUPABASE_SERVICE_ROLE_KEY}"
}
```

**Query Parameters:**
- `user_number=eq.{phone_number}`
- `whatsapp_business_account=eq.{account_id}`
- `select=*`

**CURL Example:**
```bash
curl -X GET "https://auth.propzing.com/rest/v1/whatsapp_agency_agent_history?user_number=eq.%2B919182818404&whatsapp_business_account=eq.543107385407043&select=*" \
  -H "Authorization: Bearer YOUR_SERVICE_KEY" \
  -H "apikey: YOUR_SERVICE_KEY"
```

**Response:**
```json
[
  {
    "user_number": "+919182818404",
    "whatsapp_business_account": "543107385407043",
    "user_name": "John Doe",
    "chat_summary": "Looking for 2BR apartments in Marina",
    "properties": ["prop1", "prop2"],
    "org_id": "4462c6c4-3d71-4b4d-ace7-1659ebc8424a",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T11:30:00Z"
  }
]
```

---

## Environment Variables Required

```bash
# Supabase
SUPABASE_URL=https://auth.propzing.com
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# AiSensy
AISENSY_BASE_URL=https://backend.aisensy.com
AISENSY_ACCESS_TOKEN=your_access_token_here

# OpenAI (for AI features)
OPENAI_API_KEY=your_openai_key_here

# WhatsApp Agency Tools
NEXT_PUBLIC_TOOLS_EDGE_FUNCTION_URL=https://auth.propzing.com/functions/v1/whatsapp_agency_tools
```

---

## API Error Handling

All APIs implement retry logic and graceful error handling:

1. **Token Refresh**: AiSensy APIs automatically refresh tokens on 401/422 errors
2. **Timeouts**: Most APIs have 10-30 second timeouts
3. **Fallbacks**: Location and search APIs have fallback responses when primary calls fail
4. **Non-blocking**: Background APIs (carousel, area expert, agent history) don't block main flow

---

## Rate Limits & Best Practices

1. **Property Search**: No specific rate limit, but use caching when possible
2. **WhatsApp Messaging**: Follow WhatsApp Business API limits (check AiSensy documentation)
3. **Location APIs**: Limit to 3-5 results per query (k parameter)
4. **Background APIs**: Use async/non-blocking calls for carousel, history updates
5. **Caching**: Property details and user data should be cached when appropriate

---

## Testing APIs

For local testing, see:
- `processing-worker/LOCAL_TESTING.md`
- `processing-worker/tests/flow_emulator/README.md`

For production deployment:
- `DEPLOYMENT_GUIDE.md`
- `PRODUCTION_READINESS_GUIDE.md`

---

## Support & Documentation

- **Main Documentation**: `README.md`
- **Architecture**: `ARCHITECTURE_REFACTOR.md`
- **Testing Guide**: `processing-worker/TESTING_GUIDE.md`
- **Deployment**: `DEPLOYMENT_GUIDE.md`

---

*Last Updated: October 2025*
*Version: 2.0*

