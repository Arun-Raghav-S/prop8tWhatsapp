"""
AI Mode Service
Handles checking if AI mode is enabled for a WhatsApp business account
"""

import httpx
import logging
from typing import Optional

from ..config import config

logger = logging.getLogger(__name__)

class AiModeService:
    """Service for checking AI mode status from whatsapp_agents table"""
    
    def __init__(self):
        self.supabase_url = config.SUPABASE_URL or "https://auth.propzing.com"
        # Use service role key for admin access to bypass RLS policies
        self.service_key = config.SUPABASE_SERVICE_ROLE_KEY
        
        # Log key availability for debugging
        if self.service_key:
            logger.info(f"✅ [AI_MODE] Supabase service role key found (length: {len(self.service_key)})")
        else:
            logger.warning(f"❌ [AI_MODE] No Supabase service role key found")
            logger.warning(f"❌ [AI_MODE] Config SUPABASE_SERVICE_ROLE_KEY: {config.SUPABASE_SERVICE_ROLE_KEY}")
            logger.warning(f"❌ [AI_MODE] Config SUPABASE_URL: {config.SUPABASE_URL}")
        
    async def is_ai_mode_enabled(self, whatsapp_business_account: str) -> bool:
        """
        Check if AI mode is enabled for a WhatsApp business account
        
        Args:
            whatsapp_business_account: The WhatsApp business account ID
            
        Returns:
            True if AI mode is enabled, False otherwise
            If there's an error or no record found, defaults to False for safety
        """
        try:
            logger.info(f"🔍 [AI_MODE] Checking AI mode status for {whatsapp_business_account}")
            
            if not self.service_key:
                logger.warning("[AI_MODE] Missing service role key, defaulting to AI mode disabled")
                return False
            
            # Use Supabase REST API to query the whatsapp_agents table
            api_url = f"{self.supabase_url}/rest/v1/whatsapp_agents"
            
            # Filter by whatsapp_business_account and select only ai_mode field
            params = {
                "whatsapp_business_account": f"eq.{whatsapp_business_account}",
                "select": "ai_mode"
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
                    
                    # Supabase returns an array, get first result
                    if data and len(data) > 0:
                        agent_record = data[0]
                        ai_mode = agent_record.get("ai_mode", False)  # Default to False if not set
                        
                        logger.info(f"✅ [AI_MODE] Found agent record - AI mode: {ai_mode} for {whatsapp_business_account}")
                        return bool(ai_mode)
                    else:
                        logger.warning(f"❌ [AI_MODE] No agent record found for {whatsapp_business_account}, defaulting to disabled")
                        return False
                        
                else:
                    logger.warning(f"[AI_MODE] Failed to fetch AI mode status: {response.status_code} - {response.text}")
                    return False
                        
        except Exception as e:
            logger.error(f"[AI_MODE] Error checking AI mode status: {e}")
            return False

# Global instance
ai_mode_service = AiModeService()

async def check_ai_mode_enabled(whatsapp_business_account: str) -> bool:
    """
    Convenience function to check if AI mode is enabled
    
    Args:
        whatsapp_business_account: The WhatsApp business account ID
        
    Returns:
        True if AI mode is enabled, False otherwise
    """
    return await ai_mode_service.is_ai_mode_enabled(whatsapp_business_account)
