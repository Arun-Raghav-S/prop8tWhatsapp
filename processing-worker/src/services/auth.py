import os
import logging
import httpx
from typing import Dict, Optional
from datetime import datetime, timedelta
from src.config import config

logger = logging.getLogger(__name__)

# Token management
current_access_token = config.AISENSY_ACCESS_TOKEN
token_expiry_time = None

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
                    current_access_token = new_access_token
                    token_expiry_time = datetime.now() + timedelta(seconds=expires_in)
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

async def get_valid_access_token(whatsapp_business_account: str) -> Optional[str]:
    """Get a valid access token, refreshing if necessary"""
    global current_access_token, token_expiry_time
    
    # First try to get the current token from database
    tokens = await fetch_tokens_from_database(whatsapp_business_account)
    db_access_token = tokens.get("access_token")
    
    # Use database token if available, otherwise fall back to current in-memory token
    if db_access_token:
        current_access_token = db_access_token
    elif not current_access_token:
        # If no token in memory and no token in database, use environment variable
        current_access_token = config.AISENSY_ACCESS_TOKEN
    
    # If token is about to expire (within 5 minutes), refresh it
    if token_expiry_time and datetime.now() >= (token_expiry_time - timedelta(minutes=5)):
        logger.info(f"Token is about to expire, refreshing for business account: {whatsapp_business_account}...")
        refreshed_token = await refresh_access_token(whatsapp_business_account)
        return refreshed_token if refreshed_token else current_access_token
    
    return current_access_token