import os
import json
import asyncio
import httpx
import logging
from typing import Any, Dict, List, Optional
import time
from datetime import datetime, timedelta
from src.config import config
from src.services.auth import get_valid_access_token, refresh_access_token

logger = logging.getLogger(__name__)

# Configuration for organization metadata API calls
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://auth.propzing.com")
TOOLS_EDGE_FUNCTION_URL = os.getenv("NEXT_PUBLIC_TOOLS_EDGE_FUNCTION_URL", 
                                   "https://auth.propzing.com/functions/v1/whatsapp_agency_tools")

async def fetch_org_metadata_internal(user_number: str, whatsapp_business_account: str) -> Dict[str, Any]:
    """
    Fetch organization metadata exactly like the reference implementation.
    This fetches org details using the user number and WhatsApp business account.
    """
    logger.info(f"[fetch_org_metadata_internal] Fetching metadata for user: {user_number}, whatsapp_business_account: {whatsapp_business_account}")
    
    if not SUPABASE_ANON_KEY:
        logger.error("[fetch_org_metadata_internal] Missing SUPABASE_ANON_KEY")
        return {"error": "Server configuration error - missing API key"}
    
    try:
        headers = {
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare API payload with required parameters
        payload = {
            "action": "fetchOrgMetadata",
            "user_number": user_number,
            "whatsapp_business_account": whatsapp_business_account
        }
        
        logger.info(f"[fetch_org_metadata_internal] API payload: {payload}")
        
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                TOOLS_EDGE_FUNCTION_URL,
                json=payload,
                headers=headers
            )
            
            logger.info(f"[fetch_org_metadata_internal] API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"[fetch_org_metadata_internal] API response data: {data}")
                return data
            else:
                error_msg = f"API request failed with status {response.status_code}: {response.text}"
                logger.error(f"[fetch_org_metadata_internal] {error_msg}")
                return {"error": error_msg}
                
    except httpx.TimeoutException:
        error_msg = "API request timed out"
        logger.error(f"[fetch_org_metadata_internal] {error_msg}")
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Error fetching metadata: {str(e)}"
        logger.error(f"[fetch_org_metadata_internal] {error_msg}")
        return {"error": error_msg}

# 🚨 FIX: Simple timestamp-based deduplication
processed_messages: Dict[str, float] = {}  # message_id -> timestamp
latest_message_timestamp: float = 0  # Track the latest message timestamp we've seen

def is_duplicate_message(message_id: str, message_timestamp: str = None) -> bool:
    """
    Check if a message is a duplicate or older than the latest message we've processed.
    
    Simple logic: If message timestamp <= latest timestamp we've seen, it's old/duplicate.
    """
    global latest_message_timestamp
    
    # Check if we've already processed this exact message ID
    if message_id in processed_messages:
        logger.warning(f"🚨 [DEDUP] EXACT DUPLICATE MESSAGE ID: {message_id}")
        return True
    
    # Check timestamp ordering
    if message_timestamp:
        try:
            msg_timestamp = float(message_timestamp)
            
            # If this message is older than or equal to the latest we've seen, ignore it
            if msg_timestamp <= latest_message_timestamp:
                logger.warning(f"🚨 [DEDUP] OLD MESSAGE: {message_id}, ts: {msg_timestamp}, latest: {latest_message_timestamp}")
                return True
            
            # This is a newer message - update our latest timestamp
            latest_message_timestamp = msg_timestamp
            logger.info(f"✅ [DEDUP] New message: {message_id}, ts: {msg_timestamp}")
            
        except (ValueError, TypeError):
            logger.warning(f"⚠️ [DEDUP] Invalid timestamp: {message_timestamp}")
    
    # Mark message as processed
    processed_messages[message_id] = time.time()
    return False

def generate_curl_command(method: str, url: str, headers: Dict[str, str], data: Any = None) -> str:
    """Generate a curl command for debugging API calls"""
    try:
        import shlex
        # Start with basic curl command
        curl_parts = ["curl", "-X", method.upper()]
        
        # Add headers
        for key, value in headers.items():
            curl_parts.extend(["-H", f"{key}: {value}"])
        
        # Add data if present
        if data:
            if isinstance(data, dict):
                json_data = json.dumps(data, separators=(',', ':'))
                curl_parts.extend(["-d", json_data])
            else:
                curl_parts.extend(["-d", str(data)])
        
        # Add URL
        curl_parts.append(url)
        
        # Use shlex.join for proper shell escaping
        return " ".join(shlex.quote(part) for part in curl_parts)
    except Exception as e:
        return f"Error generating curl command: {e}"

async def mark_message_as_read(message_id: str, whatsapp_business_account: str = None) -> bool:
    """
    Mark a WhatsApp message as read
    
    Args:
        message_id: The WhatsApp message ID (e.g., wamid.HBgMOTE4MjgxODQwNDYyFQIAEhggRDc3...)
        whatsapp_business_account: The WhatsApp business account ID
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get access token
        access_token = await get_valid_access_token(whatsapp_business_account)
        logger.info(f"🔄 [MARK_READ] Access token: {access_token}")
        if not access_token:
            logger.error(f"❌ [MARK_READ] No valid access token for business account: {whatsapp_business_account}")
            return False
            
        # Prepare API request data for mark-read (only messageId required)
        mark_read_data = {
            "messageId": message_id,
            "showTypingIndicator": "true"
        }
        
        # Note: Only using mark-read endpoint, not messages endpoint
        
        headers = {
            "Accept": "application/json, application/xml",
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        logger.info(f"📬 [MARK_READ] Marking message as read: {message_id[:20]}...")
        logger.info(f"🔄 [MARK_READ] Business Account: {whatsapp_business_account}")
        logger.info(f"📬 [MARK_READ] Mark-read data: {mark_read_data}")
        
        async with httpx.AsyncClient() as client:
            # First API call: mark-read endpoint (only messageId)
            mark_read_url = f"{config.AISENSY_BASE_URL}/direct-apis/t1/mark-read"
            
            # Generate and log curl command for debugging
            curl_command = generate_curl_command("POST", mark_read_url, headers, mark_read_data)
            logger.info(f"🔧 [CURL] Equivalent curl command for mark-read:")
            logger.info(f"🔧 [CURL] {curl_command}")
            
            response = await client.post(mark_read_url, headers=headers, json=mark_read_data, timeout=30.0)
            
            if response.status_code == 200:
                logger.info(f"✅ [MARK_READ] Successfully marked message as read")
                logger.info(f"📄 [MARK_READ] Mark-read response: {response.text}")
                return True
            else:
                logger.warning(f"⚠️ [MARK_READ] Failed to mark message as read. Status: {response.status_code}")
                logger.warning(f"⚠️ [MARK_READ] Response: {response.text}")
                logger.info(f"💡 [MARK_READ] This is non-critical, continuing with message processing")
                return True  # Return True to not break the flow
                
    except httpx.TimeoutException:
        logger.error(f"⏱️ [MARK_READ] Timeout marking message as read: {message_id[:20]}...")
        return False
    except Exception as e:
        logger.error(f"💥 [MARK_READ] Unexpected error marking message as read: {e}")
        return False

async def send_message_via_aisensy(to_phone: str, message: str, whatsapp_business_account: str = None, retry_count: int = 0) -> bool:
    """Send message back to user via AiSensy Direct API with automatic token refresh"""
    
    # Use the provided whatsapp_business_account or fallback to environment token
    if whatsapp_business_account:
        access_token = await get_valid_access_token(whatsapp_business_account)
    else:
        access_token = config.AISENSY_ACCESS_TOKEN
    
    if not access_token:
        logger.error("No valid access token available")
        return False
    
    # Correct AiSensy Direct API endpoint
    url = f"{config.AISENSY_BASE_URL}/direct-apis/t1/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, application/xml"
    }
    
    # Correct AiSensy Direct API message format
    payload = {
        "to": to_phone,
        "type": "text",
        "recipient_type": "individual",
        "text": {
            "body": message
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending message via AiSensy to {to_phone}: {message}")
            logger.info(f"Using endpoint: {url}")
            logger.info(f"Payload: {payload}")
            
            response = await client.post(url, json=payload, headers=headers)
            
            logger.info(f"AiSensy API response status: {response.status_code}")
            logger.info(f"AiSensy API response body: {response.text}")
            
            # If we get a 401 or 422 (token expired/invalid) and haven't retried yet, try to refresh token
            if response.status_code in [401, 422] and retry_count == 0 and whatsapp_business_account:
                response_data = response.text
                if "Invalid Token" in response_data or "token" in response_data.lower():
                    logger.info("Received token error, attempting to refresh token and retry...")
                    refreshed_token = await refresh_access_token(whatsapp_business_account)
                    if refreshed_token:
                        # Retry with new token
                        return await send_message_via_aisensy(to_phone, message, whatsapp_business_account, retry_count + 1)
                    else:
                        logger.error("Failed to refresh token")
                        return False
            
            if response.status_code == 200:
                logger.info(f"Message sent successfully to {to_phone}")
                return True
            else:
                logger.error(f"Failed to send message. Status: {response.status_code}, Response: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending message via AiSensy: {e}")
        return False

async def send_image_via_aisensy(to_phone: str, image_url: str, caption: str = "", whatsapp_business_account: str = None, retry_count: int = 0) -> bool:
    """Send image message via AiSensy Direct API"""
    
    # Use the provided whatsapp_business_account or fallback to environment token
    if whatsapp_business_account:
        access_token = await get_valid_access_token(whatsapp_business_account)
    else:
        access_token = config.AISENSY_ACCESS_TOKEN
    
    if not access_token:
        logger.error("No valid access token available")
        return False
    
    url = f"{config.AISENSY_BASE_URL}/direct-apis/t1/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, application/xml"
    }
    
    payload = {
        "to": to_phone,
        "type": "image",
        "image": {
            "caption": caption,
            "link": image_url
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending image via AiSensy to {to_phone}: {image_url}")
            logger.info(f"Payload: {payload}")
            
            response = await client.post(url, json=payload, headers=headers)
            
            logger.info(f"AiSensy API response status: {response.status_code}")
            logger.info(f"AiSensy API response body: {response.text}")
            
            if response.status_code in [401, 422] and retry_count == 0 and whatsapp_business_account:
                response_data = response.text
                if "Invalid Token" in response_data or "token" in response_data.lower():
                    logger.info("Received token error, attempting to refresh token and retry...")
                    refreshed_token = await refresh_access_token(whatsapp_business_account)
                    if refreshed_token:
                        return await send_image_via_aisensy(to_phone, image_url, caption, whatsapp_business_account, retry_count + 1)
                    else:
                        logger.error("Failed to refresh token")
                        return False
            
            if response.status_code == 200:
                logger.info(f"Image sent successfully to {to_phone}")
                return True
            else:
                logger.error(f"Failed to send image. Status: {response.status_code}, Response: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending image via AiSensy: {e}")
        return False

async def send_document_via_aisensy(to_phone: str, document_url: str, filename: str, caption: str = "", whatsapp_business_account: str = None, retry_count: int = 0) -> bool:
    """Send document message via AiSensy Direct API"""
    
    # Use the provided whatsapp_business_account or fallback to environment token
    if whatsapp_business_account:
        access_token = await get_valid_access_token(whatsapp_business_account)
    else:
        access_token = config.AISENSY_ACCESS_TOKEN
    
    if not access_token:
        logger.error("No valid access token available")
        return False
    
    url = f"{config.AISENSY_BASE_URL}/direct-apis/t1/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, application/xml"
    }
    
    payload = {
        "to": to_phone,
        "type": "document",
        "document": {
            "caption": caption,
            "link": document_url,
            "filename": filename
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending document via AiSensy to {to_phone}: {document_url}")
            logger.info(f"Payload: {payload}")
            
            response = await client.post(url, json=payload, headers=headers)
            
            logger.info(f"AiSensy API response status: {response.status_code}")
            logger.info(f"AiSensy API response body: {response.text}")
            
            if response.status_code in [401, 422] and retry_count == 0 and whatsapp_business_account:
                response_data = response.text
                if "Invalid Token" in response_data or "token" in response_data.lower():
                    logger.info("Received token error, attempting to refresh token and retry...")
                    refreshed_token = await refresh_access_token(whatsapp_business_account)
                    if refreshed_token:
                        return await send_document_via_aisensy(to_phone, document_url, filename, caption, whatsapp_business_account, retry_count + 1)
                    else:
                        logger.error("Failed to refresh token")
                        return False
            
            if response.status_code == 200:
                logger.info(f"Document sent successfully to {to_phone}")
                return True
            else:
                logger.error(f"Failed to send document. Status: {response.status_code}, Response: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error sending document via AiSensy: {e}")
        return False


async def log_ai_reply_async(
    org_id: str,
    lead_id: Optional[str],
    whatsapp_agent_id: str,
    to_phone: str,
    whatsapp_interaction_id: Optional[str]
) -> None:
    """
    Log AI reply to the edge function - completely non-blocking
    This tracks all AI agent replies sent to users
    
    Args:
        org_id: Organization ID
        lead_id: Lead ID from agent history (can be None)
        whatsapp_agent_id: WhatsApp business account ID
        to_phone: User's phone number
        whatsapp_interaction_id: Interaction ID from agent history (can be None)
    """
    try:
        logger.info(f"📊 [LOG_MESSAGE] Logging AI reply for {to_phone}")
        
        # Prepare payload with fixed category and template_name
        payload = {
            "org_id": org_id,
            "lead_id": lead_id or "pending",
            "whatsapp_agent_id": whatsapp_agent_id,
            "category": "AI_REPLY",
            "template_name": "ai_response_template",
            "to_phone": to_phone,
            "whatsapp_interaction_id": whatsapp_interaction_id or "pending"
        }
        
        logger.info(f"📊 [LOG_MESSAGE] Payload: {json.dumps(payload, indent=2)}")
        
        # Use the Supabase URL from environment
        log_url = f"{SUPABASE_URL}/functions/v1/log-message"
        
        headers = {
            "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        
        # Make async call with timeout
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(log_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"✅ [LOG_MESSAGE] Successfully logged AI reply for {to_phone}")
            else:
                logger.warning(f"⚠️ [LOG_MESSAGE] Failed to log: {response.status_code} - {response.text}")
                
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ [LOG_MESSAGE] Timeout logging AI reply (non-critical)")
    except Exception as e:
        # Don't let logging errors break the main flow
        logger.warning(f"⚠️ [LOG_MESSAGE] Error logging AI reply (non-critical): {e}")


def trigger_log_ai_reply(
    org_id: str,
    lead_id: Optional[str],
    whatsapp_agent_id: str,
    to_phone: str,
    whatsapp_interaction_id: Optional[str]
) -> None:
    """
    Trigger AI reply logging in background - completely non-blocking
    
    Args:
        org_id: Organization ID
        lead_id: Lead ID from agent history (can be None)
        whatsapp_agent_id: WhatsApp business account ID
        to_phone: User's phone number
        whatsapp_interaction_id: Interaction ID from agent history (can be None)
    """
    # Launch in background without waiting
    asyncio.create_task(log_ai_reply_async(
        org_id=org_id,
        lead_id=lead_id,
        whatsapp_agent_id=whatsapp_agent_id,
        to_phone=to_phone,
        whatsapp_interaction_id=whatsapp_interaction_id
    ))
    
    logger.info(f"🚀 [LOG_MESSAGE] Launched background task to log AI reply for {to_phone}")


# ============================================================================
# MESSAGE STATUS TRACKING (sent/delivered/read)
# ============================================================================

async def update_message_status(
    message_id: str, 
    status: str, 
    timestamp: str, 
    recipient_phone: str = None,
    whatsapp_business_account: str = None
) -> bool:
    """
    Update message status in the message_logs table (NON-BLOCKING)
    
    Args:
        message_id: The WhatsApp message ID (stored as bsp_msg_id)
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
        
        # Database URL and headers (updated to use message_logs table)
        search_url = f"{config.SUPABASE_URL}/rest/v1/message_logs"
        headers = {
            "apikey": config.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {config.SUPABASE_SERVICE_ROLE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Search for existing record using bsp_msg_id (new column name)
        search_params = {"bsp_msg_id": f"eq.{message_id}", "select": "id,whatsapp_status"}
        status_logger.info(f"🔍 [STATUS] Searching for existing record with bsp_msg_id: {message_id}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            search_response = await client.get(search_url, headers=headers, params=search_params)
            
            if search_response.status_code == 200:
                existing_records = search_response.json()
                status_logger.info(f"🔍 [STATUS] Found {len(existing_records)} existing records")
                
                if existing_records:
                    # Update existing record
                    record = existing_records[0]
                    existing_whatsapp_status = record.get("whatsapp_status", {})
                    status_logger.info(f"📋 [STATUS] Existing whatsapp_status: {existing_whatsapp_status}")
                    
                    # Parse existing whatsapp_status JSON or create new one
                    if isinstance(existing_whatsapp_status, dict):
                        updated_status = existing_whatsapp_status.copy()
                    else:
                        try:
                            updated_status = json.loads(existing_whatsapp_status) if existing_whatsapp_status else {}
                        except (json.JSONDecodeError, TypeError):
                            updated_status = {}
                    
                    # Add the new status with timestamp
                    updated_status[status] = iso_timestamp
                    
                    # Handle out-of-order delivery: if read comes before delivered
                    if status == "read" and "delivered" not in updated_status and "sent" in updated_status:
                        status_logger.info(f"⚠️ [STATUS] Read received before delivered - using same timestamp")
                        updated_status["delivered"] = iso_timestamp
                    
                    status_logger.info(f"🔄 [STATUS] Updated whatsapp_status JSON: {updated_status}")
                    
                    # Update the record using whatsapp_status column
                    update_url = f"{search_url}?id=eq.{record['id']}"
                    update_data = {"whatsapp_status": updated_status}
                    
                    update_response = await client.patch(update_url, headers=headers, json=update_data)
                    
                    if update_response.status_code in [200, 204]:
                        status_logger.info(f"✅ [STATUS] Successfully updated whatsapp_status")
                        return True
                    else:
                        status_logger.error(f"❌ [STATUS] Failed to update: {update_response.status_code}")
                        return False
                else:
                    # No existing record found - this is expected since message_logs entries 
                    # are created when messages are sent, not when status updates arrive
                    status_logger.info(f"📝 [STATUS] No existing record found for bsp_msg_id: {message_id}")
                    status_logger.info(f"ℹ️ [STATUS] This is normal - message_logs entries are created when sending messages")
                    return True  # Return True to not block the flow
            else:
                status_logger.error(f"❌ [STATUS] Search failed: {search_response.status_code}")
                return False
                
    except asyncio.TimeoutError:
        logger.warning(f"⏱️ [STATUS] Timeout updating status (non-critical)")
        return False
    except Exception as e:
        logger.warning(f"⚠️ [STATUS] Error updating message status (non-critical): {e}")
        return False


async def process_status_updates(
    statuses: List[Dict[str, Any]], 
    whatsapp_business_account: str = None
) -> bool:
    """
    Process multiple status updates from a webhook (NON-BLOCKING)
    
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


def trigger_status_update(statuses: List[Dict[str, Any]], whatsapp_business_account: str = None) -> None:
    """
    Trigger status update in background - completely non-blocking
    
    Args:
        statuses: List of status objects from webhook
        whatsapp_business_account: Business account ID (optional)
    """
    # Launch in background without waiting
    asyncio.create_task(process_status_updates(statuses, whatsapp_business_account))
    logger.info(f"🚀 [STATUS] Launched background task to update {len(statuses)} message statuses")