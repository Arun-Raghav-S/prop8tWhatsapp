"""
Area Expert Service
Handles asynchronous calls to the area expert API when user provides location and transaction type
"""

import os
import httpx
import asyncio
import logging
from typing import Dict, Any, Optional

from ..config import config

logger = logging.getLogger(__name__)


class AreaExpertService:
    """Service for calling the area expert API in the background"""
    
    def __init__(self):
        self.api_url = "https://wpxcvnipnmdvdhrnlfed.supabase.co/functions/v1/info_area_expert"
        self.triggered_interactions = set()  # Track which interactions we've already triggered for
        
    async def trigger_area_expert(
        self, 
        area: str,
        rent_buy: str,  # "rent" or "buy"
        org_id: str,
        whatsapp_business_account: str,
        lead_id: Optional[str] = None,
        whatsapp_interaction_id: Optional[str] = None
    ):
        """
        Trigger area expert API in background - completely non-blocking
        
        Args:
            area: The location/area (e.g., "Dubai Marina", "JBR", "Downtown")
            rent_buy: Transaction type - "rent" or "buy"
            org_id: Organization ID
            whatsapp_business_account: WhatsApp business account ID
            lead_id: Lead ID from agent history response (optional)
            whatsapp_interaction_id: WhatsApp interaction ID from agent history response (optional)
        """
        # Create a unique key to avoid duplicate calls for same interaction
        interaction_key = f"{whatsapp_interaction_id or 'unknown'}_{area}_{rent_buy}"
        
        # Skip if we've already triggered this
        if interaction_key in self.triggered_interactions:
            logger.info(f"⏭️ [AREA_EXPERT] Already triggered for this interaction, skipping")
            return
            
        # Mark as triggered
        self.triggered_interactions.add(interaction_key)
        
        # Clean up old entries to prevent memory leak (keep last 1000)
        if len(self.triggered_interactions) > 1000:
            # Remove oldest half
            self.triggered_interactions = set(list(self.triggered_interactions)[-500:])
        
        # Launch in background without waiting
        asyncio.create_task(self._call_area_expert_async(
            area=area,
            rent_buy=rent_buy,
            org_id=org_id,
            whatsapp_business_account=whatsapp_business_account,
            lead_id=lead_id,
            whatsapp_interaction_id=whatsapp_interaction_id
        ))
        
        logger.info(f"🚀 [AREA_EXPERT] Launched background task for area: {area}, type: {rent_buy}")
    
    async def _call_area_expert_async(
        self,
        area: str,
        rent_buy: str,
        org_id: str,
        whatsapp_business_account: str,
        lead_id: Optional[str] = None,
        whatsapp_interaction_id: Optional[str] = None
    ):
        """Internal method to make the actual API call"""
        try:
            logger.info(f"📍 [AREA_EXPERT] Starting area expert API call")
            logger.info(f"📍 [AREA_EXPERT] Area: {area}")
            logger.info(f"📍 [AREA_EXPERT] Rent/Buy: {rent_buy}")
            logger.info(f"📍 [AREA_EXPERT] Org ID: {org_id}")
            logger.info(f"📍 [AREA_EXPERT] Lead ID: {lead_id or 'Not available yet'}")
            logger.info(f"📍 [AREA_EXPERT] WhatsApp Interaction ID: {whatsapp_interaction_id or 'Not available yet'}")
            
            # Prepare payload
            payload = {
                "area": area,
                "org_id": org_id,
                "whatsapp_interaction_id": whatsapp_interaction_id or "pending",
                "lead_id": lead_id or "pending",
                "rent_buy": rent_buy,
                "whatsapp_business_account": whatsapp_business_account
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Make the API call with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                
                # Log the response
                logger.info(f"📍 [AREA_EXPERT] Response Status: {response.status_code}")
                logger.info(f"📍 [AREA_EXPERT] Response Body: {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"✅ [AREA_EXPERT] Successfully called area expert API")
                    try:
                        response_data = response.json()
                        logger.info(f"📊 [AREA_EXPERT] Response Data: {response_data}")
                    except Exception as json_error:
                        logger.info(f"📊 [AREA_EXPERT] Response is not JSON: {json_error}")
                else:
                    logger.warning(f"⚠️ [AREA_EXPERT] Area expert API returned non-200: {response.status_code}")
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ [AREA_EXPERT] API call timed out (this is okay, won't affect main flow)")
        except Exception as e:
            # Don't let area expert errors break anything
            logger.warning(f"⚠️ [AREA_EXPERT] Error calling area expert API (non-critical): {e}")
            # Explicitly not re-raising - this should never disrupt the main flow


# Global instance
area_expert_service = AreaExpertService()


async def trigger_area_expert_if_ready(
    area: Optional[str],
    rent_buy: Optional[str],
    org_id: str,
    whatsapp_business_account: str,
    lead_id: Optional[str] = None,
    whatsapp_interaction_id: Optional[str] = None
):
    """
    Helper function to trigger area expert only if we have required data
    
    Args:
        area: Location/area
        rent_buy: Transaction type
        org_id: Organization ID
        whatsapp_business_account: WhatsApp business account ID
        lead_id: Lead ID (can be None initially)
        whatsapp_interaction_id: Interaction ID (can be None initially)
    """
    # Only trigger if we have the essential data: area and rent_buy
    if not area or not rent_buy:
        logger.debug(f"🔍 [AREA_EXPERT] Not ready yet - area: {area}, rent_buy: {rent_buy}")
        return
    
    # Normalize rent_buy to lowercase
    rent_buy = rent_buy.lower()
    if rent_buy not in ["rent", "buy"]:
        logger.warning(f"⚠️ [AREA_EXPERT] Invalid rent_buy value: {rent_buy}")
        return
    
    logger.info(f"✓ [AREA_EXPERT] Requirements met, triggering area expert")
    
    await area_expert_service.trigger_area_expert(
        area=area,
        rent_buy=rent_buy,
        org_id=org_id,
        whatsapp_business_account=whatsapp_business_account,
        lead_id=lead_id,
        whatsapp_interaction_id=whatsapp_interaction_id
    )

