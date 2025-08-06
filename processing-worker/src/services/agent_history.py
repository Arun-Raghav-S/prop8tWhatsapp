"""
Agent History Service
Handles updating agent conversation history to the database
"""

import os
import httpx
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from ..config import config

logger = logging.getLogger(__name__)

class AgentHistoryService:
    """Service for managing agent conversation history via API"""
    
    def __init__(self):
        self.api_url = "https://auth.propzing.com/functions/v1/update_whatsappagencyagent_history"
        # Use config file for anon key (which handles environment variables)
        self.anon_key = config.SUPABASE_ANON_KEY
        
        # Log key availability for debugging
        if self.anon_key:
            logger.info(f"✅ [AGENT_HISTORY] Supabase anon key found (length: {len(self.anon_key)})")
        else:
            available_keys = [key for key in os.environ.keys() if 'SUPABASE' in key.upper()]
            logger.warning(f"❌ [AGENT_HISTORY] No Supabase anon key found. Available SUPABASE env vars: {available_keys}")
            logger.warning(f"❌ [AGENT_HISTORY] Config SUPABASE_ANON_KEY: {config.SUPABASE_ANON_KEY}")
            logger.warning(f"❌ [AGENT_HISTORY] Config SUPABASE_URL: {config.SUPABASE_URL}")
        
    async def update_agent_history(
        self, 
        user_message: str, 
        agent_response: str,
        user_number: str,
        whatsapp_business_account: str,
        org_id: Optional[str] = None,
        user_name: Optional[str] = None
    ):
        """Update agent history via API endpoint in background - non-blocking"""
        try:
            logger.info("🔄 [AGENT_HISTORY] Starting agent history API update")
            
            if not self.anon_key:
                logger.warning("[AGENT_HISTORY] Missing anon key, skipping agent history update")
                logger.warning("[AGENT_HISTORY] Please set SUPABASE_ANON_KEY environment variable")
                return
            
            # Prepare chat history entries with proper timestamp
            timestamp = datetime.utcnow().isoformat() + "Z"
            
            chat_history_entries = []
            
            # Add user message with type
            chat_history_entries.append({
                "role": "user",
                "content": user_message,
                "timestamp": timestamp,
                "type": "text"  # Adding type field as requested
            })
            
            # Add agent response with type
            chat_history_entries.append({
                "role": "assistant", 
                "content": agent_response,
                "timestamp": timestamp,
                "type": "text"  # Adding type field as requested
            })
            
            # Prepare API payload
            payload = {
                "org_id": org_id or "unknown",  # Will now have actual org_id from session
                "whatsapp_business_account": whatsapp_business_account,
                "user_number": user_number,
                "chat_history": chat_history_entries,
                "phone_number": user_number,
                "user_name": user_name
            }
            
            logger.info(f"🔄 [AGENT_HISTORY] Using org_id: {org_id}")
            logger.info(f"🔄 [AGENT_HISTORY] Using user_name: {user_name}")
            
            # Make API call
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.anon_key}"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    logger.info("[AGENT_HISTORY] Successfully updated agent history")
                else:
                    logger.warning(f"[AGENT_HISTORY] Failed to update agent history: {response.status_code} - {response.text}")
                        
        except Exception as e:
            # Don't let agent history errors break the conversation
            logger.error(f"[AGENT_HISTORY] Error updating agent history: {e}")

# Global instance
agent_history_service = AgentHistoryService()

async def update_agent_history_async(
    user_message: str, 
    agent_response: str,
    user_number: str,
    whatsapp_business_account: str,
    org_id: Optional[str] = None,
    user_name: Optional[str] = None
):
    """Async helper function to update agent history"""
    await agent_history_service.update_agent_history(
        user_message=user_message,
        agent_response=agent_response,
        user_number=user_number,
        whatsapp_business_account=whatsapp_business_account,
        org_id=org_id,
        user_name=user_name
    )