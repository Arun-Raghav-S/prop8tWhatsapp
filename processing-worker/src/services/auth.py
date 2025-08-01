import os
import logging
import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta
from src.config import config

logger = logging.getLogger(__name__)

# In-memory token management for each business account
_token_cache = {}

def get_access_token(whatsapp_business_account: str) -> str:
    """Get the current access token for a business account"""
    global _token_cache
    return _token_cache.get(whatsapp_business_account, config.AISENSY_ACCESS_TOKEN)

def set_access_token(whatsapp_business_account: str, token: str):
    """Set the access token for a business account in memory"""
    global _token_cache
    _token_cache[whatsapp_business_account] = token
    logger.info(f"🔄 TOKEN_CACHED: Updated token for {whatsapp_business_account}")

async def fetch_tokens_from_database(whatsapp_business_account: str) -> Dict[str, Optional[str]]:
    """
    Fetch access_token and refresh_token from whatsapp_agents table
    
    Args:
        whatsapp_business_account: The WhatsApp business account ID
        
    Returns:
        Dict containing access_token and refresh_token, or None values if not found
    """
    if not config.SUPABASE_ANON_KEY:
        logger.error("Missing SUPABASE_ANON_KEY for database access")
        return {"access_token": None, "refresh_token": None}
    
    try:
        # Query the whatsapp_agents table
        url = f"{config.SUPABASE_URL}/rest/v1/whatsapp_agents"
        headers = {
            "apikey": config.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {config.SUPABASE_ANON_KEY}",
            "Content-Type": "application/json"
        }
        
        params = {
            "whatsapp_business_account": f"eq.{whatsapp_business_account}",
            "select": "access_token,refresh_token"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    agent_data = data[0]
                    logger.info(f"Successfully fetched tokens for business account: {whatsapp_business_account}")
                    
                    # Cache the access token in memory
                    if agent_data.get("access_token"):
                        set_access_token(whatsapp_business_account, agent_data["access_token"])
                    
                    return {
                        "access_token": agent_data.get("access_token"),
                        "refresh_token": agent_data.get("refresh_token")
                    }
                else:
                    logger.warning(f"No tokens found for business account: {whatsapp_business_account}")
                    return {"access_token": None, "refresh_token": None}
            else:
                logger.error(f"Failed to fetch tokens from database. Status: {response.status_code}, Response: {response.text}")
                return {"access_token": None, "refresh_token": None}
                
    except Exception as e:
        logger.error(f"Error fetching tokens from database: {e}")
        return {"access_token": None, "refresh_token": None}

async def update_access_token_in_database(whatsapp_business_account: str, new_access_token: str) -> bool:
    """
    Update access_token in whatsapp_agents table
    
    Args:
        whatsapp_business_account: The WhatsApp business account ID
        new_access_token: The new access token to save
        
    Returns:
        True if update was successful, False otherwise
    """
    if not config.SUPABASE_ANON_KEY:
        logger.error("Missing SUPABASE_ANON_KEY for database access")
        return False
    
    try:
        # Update the whatsapp_agents table
        url = f"{config.SUPABASE_URL}/rest/v1/whatsapp_agents"
        headers = {
            "apikey": config.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {config.SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        
        params = {
            "whatsapp_business_account": f"eq.{whatsapp_business_account}"
        }
        
        payload = {
            "access_token": new_access_token
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(url, headers=headers, params=params, json=payload)
            
            if response.status_code == 204:  # 204 No Content means successful update
                logger.info(f"Successfully updated access token for business account: {whatsapp_business_account}")
                return True
            else:
                logger.error(f"Failed to update access token in database. Status: {response.status_code}, Response: {response.text}")
                return False
                
    except Exception as e:
        logger.error(f"Error updating access token in database: {e}")
        return False

async def refresh_access_token(whatsapp_business_account: str) -> Optional[str]:
    """Refresh the AiSensy access token using the refresh token from database"""
    global current_access_token, token_expiry_time
    
    # Fetch refresh token from database
    tokens = await fetch_tokens_from_database(whatsapp_business_account)
    refresh_token = tokens.get("refresh_token")
    
    if not refresh_token:
        logger.error(f"Missing refresh_token for business account: {whatsapp_business_account}")
        # Fallback to environment variable if available
        refresh_token = os.getenv("AISENSY_REFRESH_TOKEN")
        if not refresh_token:
            logger.error("No refresh token available from database or environment")
            return None
    
    # AiSensy token regeneration endpoint (corrected URL)
    refresh_url = f"{config.AISENSY_BASE_URL}/direct-apis/t1/users/regenrate-token"
    
    payload = {
        "direct_api": True
    }
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {refresh_token}",
        "Content-Type": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Attempting to refresh AiSensy JWT token for business account: {whatsapp_business_account}...")
            response = await client.post(refresh_url, json=payload, headers=headers)
            
            logger.info(f"Token refresh response status: {response.status_code}")
            logger.info(f"Token refresh response body: {response.text}")
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Handle the nested response structure: {"users":[{"token":"..."}]}
                if "users" in token_data and len(token_data["users"]) > 0:
                    new_access_token = token_data["users"][0].get("token")
                else:
                    # Fallback to check for other possible field names
                    new_access_token = token_data.get("access_token") or token_data.get("jwt_token") or token_data.get("token")
                
                expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
                
                if new_access_token:
                    # Update global token (keep for backwards compatibility)
                    global current_access_token, token_expiry_time
                    current_access_token = new_access_token
                    token_expiry_time = datetime.now() + timedelta(seconds=expires_in)
                    
                    # Update token cache for this business account
                    set_access_token(whatsapp_business_account, new_access_token)
                    
                    logger.info(f"AiSensy JWT token refreshed successfully for business account: {whatsapp_business_account}. New token: {new_access_token[:20]}...")
                    
                    # Save the new access token to database
                    await update_access_token_in_database(whatsapp_business_account, new_access_token)
                    
                    # Optionally update the environment variable for this session
                    os.environ["AISENSY_ACCESS_TOKEN"] = new_access_token
                    
                    return new_access_token
                else:
                    logger.error("No access token in refresh response")
                    logger.error(f"Response data: {token_data}")
                    return None
            else:
                logger.error(f"Token refresh failed. Status: {response.status_code}, Response: {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Error refreshing AiSensy JWT token: {e}")
        return None

async def get_valid_access_token(whatsapp_business_account: str = None) -> Optional[str]:
    """Get a valid access token, using cache first, then refreshing if necessary"""
    global current_access_token, token_expiry_time
    
    # First check in-memory cache for this business account
    if whatsapp_business_account:
        cached_token = get_access_token(whatsapp_business_account)
        if cached_token and cached_token != config.AISENSY_ACCESS_TOKEN:
            logger.info(f"🔄 TOKEN_FROM_CACHE: Using cached token for {whatsapp_business_account}")
            return cached_token
    
    # If cached token is invalid, try to refresh
    if whatsapp_business_account:
        logger.info(f"🔄 TOKEN_REFRESH_ATTEMPT: Refreshing token for {whatsapp_business_account}")
        refreshed_token = await refresh_access_token(whatsapp_business_account)
        if refreshed_token:
            return refreshed_token
    
    # Fallback to environment variable
    logger.info(f"🔄 TOKEN_FALLBACK: Using environment token")
    return config.AISENSY_ACCESS_TOKEN