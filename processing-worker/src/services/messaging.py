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
            "messageId": message_id
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