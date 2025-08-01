"""
WhatsApp Carousel Broadcast Tool
Sends property carousel messages when there are many search results
"""

import os
import json
import requests
from typing import List, Optional, Dict, Any
from utils.logger import setup_logger

logger = setup_logger(__name__)


class WhatsAppCarouselTool:
    """Tool for sending WhatsApp carousel broadcasts for property listings"""
    
    def __init__(self):
        self.carousel_api_url = "https://dsakezvdiwmoobugchgu.supabase.co/functions/v1/whatsapp_carousel_broadcast"
        self.whatsapp_business_number = "543107385407043"
    
    async def send_property_carousel(self, 
                                   to_phone: str, 
                                   property_ids: List[str], 
                                   max_properties: int = 10) -> Dict[str, Any]:
        """
        Send property carousel broadcast to WhatsApp user
        
        Args:
            to_phone: User's phone number
            property_ids: List of original property IDs
            max_properties: Maximum number of properties to send (default 10)
            
        Returns:
            Dict with success status and message
        """
        try:
            # Ensure we have at least 7 properties and at most max_properties
            if len(property_ids) < 7:
                logger.warning(f"Not enough properties for carousel: {len(property_ids)}. Minimum is 7.")
                return {
                    'success': False,
                    'message': f"Not enough properties for carousel. Need at least 7, got {len(property_ids)}",
                    'sent_carousel': False
                }
            
            # Limit to maximum properties
            limited_property_ids = property_ids[:max_properties]
            
            # Prepare request payload
            payload = {
                "whatsapp_business_number": self.whatsapp_business_number,
                "to": to_phone,
                "property_ids": limited_property_ids
            }
            
            logger.info(f"🎠 Sending carousel broadcast to {to_phone} with {len(limited_property_ids)} properties")
            
            # Send request to carousel API
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                self.carousel_api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ Carousel sent successfully to {to_phone}")
                return {
                    'success': True,
                    'message': f"Property carousel sent with {len(limited_property_ids)} properties",
                    'sent_carousel': True,
                    'property_count': len(limited_property_ids)
                }
            else:
                logger.error(f"❌ Carousel API failed: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'message': f"API request failed: {response.status_code}",
                    'sent_carousel': False
                }
                
        except Exception as e:
            logger.error(f"❌ Error sending carousel: {str(e)}")
            return {
                'success': False,
                'message': f"Error sending carousel: {str(e)}",
                'sent_carousel': False
            }
    
    def should_send_carousel(self, 
                           query: str, 
                           property_count: int, 
                           min_properties: int = 7) -> bool:
        """
        Determine if carousel should be sent based on query type and property count
        
        Args:
            query: User's search query
            property_count: Number of properties found
            min_properties: Minimum properties needed for carousel
            
        Returns:
            bool: True if carousel should be sent
        """
        if property_count < min_properties:
            return False
        
        # Convert query to lowercase for analysis
        query_lower = query.lower().strip()
        
        # General property queries that should use carousel
        general_queries = [
            'properties', 'property', 'show me properties', 'what properties do you have',
            'all properties', 'list properties', 'available properties',
            'cheapest properties', 'cheapest property', 'most affordable',
            'best properties', 'good properties', 'nice properties',
            'new properties', 'latest properties',
            'properties for sale', 'properties for rent',
            'villas', 'apartments', 'townhouses'
        ]
        
        # Keywords that indicate general searches
        general_keywords = [
            'cheapest', 'most affordable', 'best value', 'good deal',
            'all', 'show me', 'list', 'available', 'what do you have',
            'properties in', 'any properties'
        ]
        
        # Specific descriptive queries that should NOT use carousel
        descriptive_keywords = [
            'amenities', 'features', 'swimming pool', 'gym', 'facilities',
            'balcony', 'view', 'terrace', 'garden', 'parking',
            'what is', 'tell me about', 'describe', 'details about',
            'furnished', 'unfurnished', 'utilities included',
            'near', 'close to', 'walking distance'
        ]
        
        # Check if query contains descriptive keywords (should NOT use carousel)
        for keyword in descriptive_keywords:
            if keyword in query_lower:
                logger.info(f"🔍 Descriptive query detected ('{keyword}'): not using carousel")
                return False
        
        # Check if query matches general patterns (should use carousel)
        for general_query in general_queries:
            if general_query in query_lower:
                logger.info(f"🎠 General query detected ('{general_query}'): using carousel")
                return True
        
        # Check for general keywords
        for keyword in general_keywords:
            if keyword in query_lower:
                logger.info(f"🎠 General keyword detected ('{keyword}'): using carousel")
                return True
        
        # If query is very short and generic, use carousel
        if len(query_lower.split()) <= 3:
            logger.info(f"🎠 Short generic query: using carousel")
            return True
        
        # Default: don't use carousel for complex/specific queries
        logger.info(f"🔍 Complex/specific query: not using carousel")
        return False


# Initialize global instance
carousel_tool = WhatsAppCarouselTool()