"""
User Data Service
Handles fetching existing user data from whatsapp_agency_agent_history table
"""

import os
import httpx
import asyncio
import logging
from typing import Dict, Any, Optional

from ..config import config

logger = logging.getLogger(__name__)

class UserDataService:
    """Service for fetching existing user data from database"""
    
    def __init__(self):
        self.supabase_url = config.SUPABASE_URL or "https://auth.propzing.com"
        # Use service role key for admin access to bypass RLS policies
        self.service_key = config.SUPABASE_SERVICE_ROLE_KEY
        
        # Log key availability for debugging
        if self.service_key:
            logger.info(f"✅ [USER_DATA] Supabase service role key found (length: {len(self.service_key)})")
        else:
            available_keys = [key for key in os.environ.keys() if 'SUPABASE' in key.upper()]
            logger.warning(f"❌ [USER_DATA] No Supabase service role key found. Available SUPABASE env vars: {available_keys}")
            logger.warning(f"❌ [USER_DATA] Config SUPABASE_SERVICE_ROLE_KEY: {config.SUPABASE_SERVICE_ROLE_KEY}")
            logger.warning(f"❌ [USER_DATA] Config SUPABASE_URL: {config.SUPABASE_URL}")
        
    async def fetch_user_data(
        self, 
        user_number: str,
        whatsapp_business_account: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch existing user data from whatsapp_agency_agent_history table
        
        Args:
            user_number: The user's phone number
            whatsapp_business_account: The WhatsApp business account ID
            
        Returns:
            User data dict if found, None otherwise
        """
        try:
            logger.info(f"🔍 [USER_DATA] Fetching existing data for {user_number}")
            
            if not self.service_key:
                logger.warning("[USER_DATA] Missing service role key, skipping user data fetch")
                return None
            
            # Use Supabase REST API to query the table directly
            api_url = f"{self.supabase_url}/rest/v1/whatsapp_agency_agent_history"
            
            # Filter by user_number and whatsapp_business_account
            params = {
                "user_number": f"eq.{user_number}",
                "whatsapp_business_account": f"eq.{whatsapp_business_account}",
                "select": "user_name,chat_summary,properties,org_id,created_at,updated_at"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.service_key}",
                "apikey": self.service_key
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(api_url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Debug: Log the raw response
                    logger.info(f"🔍 [USER_DATA] Raw response data: {data}")
                    logger.info(f"🔍 [USER_DATA] Response type: {type(data)}, Length: {len(data) if isinstance(data, list) else 'N/A'}")
                    
                    # Supabase returns an array, get first result
                    if data and len(data) > 0:
                        user_record = data[0]
                        logger.info(f"✅ [USER_DATA] Successfully fetched user data for {user_number}")
                        logger.info(f"🔍 [USER_DATA] First record: {user_record}")
                        
                        # Extract relevant information
                        user_data = {
                            "user_name": user_record.get("user_name"),
                            "chat_summary": user_record.get("chat_summary"),
                            "properties": user_record.get("properties", []),
                            "org_id": user_record.get("org_id"),
                            "created_at": user_record.get("created_at"),
                            "updated_at": user_record.get("updated_at")
                        }
                        
                        logger.info(f"📋 [USER_DATA] User name: {user_data.get('user_name') or 'Not found'}")
                        return user_data
                    else:
                        logger.info(f"👤 [USER_DATA] No existing data found for {user_number}")
                        logger.info(f"🔍 [USER_DATA] Data was: {data}")
                        return None
                        
                else:
                    logger.warning(f"[USER_DATA] Failed to fetch user data: {response.status_code} - {response.text}")
                    return None
                        
        except Exception as e:
            logger.error(f"[USER_DATA] Error fetching user data: {e}")
            return None
    
    def extract_user_name(self, user_data: Optional[Dict[str, Any]]) -> Optional[str]:
        """
        Extract user name from fetched data
        
        Args:
            user_data: The fetched user data
            
        Returns:
            User name if available, None otherwise
        """
        if not user_data:
            return None
            
        user_name = user_data.get("user_name")
        if user_name and user_name.strip():
            return user_name.strip()
            
        return None
    
    def extract_context_info(self, user_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract context information from fetched data
        
        Args:
            user_data: The fetched user data
            
        Returns:
            Context information dict
        """
        if not user_data:
            return {}
            
        context = {}
        
        # Add chat summary for context
        if user_data.get("chat_summary"):
            context["previous_chat_summary"] = user_data["chat_summary"]
        
        # Add properties if any
        if user_data.get("properties"):
            context["previous_properties"] = user_data["properties"]
        
        # Add timing info
        if user_data.get("updated_at"):
            context["last_interaction"] = user_data["updated_at"]
            
        return context

# Global instance
user_data_service = UserDataService()

async def fetch_and_initialize_user_data(
    user_number: str,
    whatsapp_business_account: str
) -> tuple[Optional[str], Dict[str, Any]]:
    """
    Fetch user data and return name and context
    
    Args:
        user_number: The user's phone number
        whatsapp_business_account: The WhatsApp business account ID
        
    Returns:
        Tuple of (user_name, context_info)
    """
    user_data = await user_data_service.fetch_user_data(user_number, whatsapp_business_account)
    user_name = user_data_service.extract_user_name(user_data)
    context_info = user_data_service.extract_context_info(user_data)
    
    return user_name, context_info