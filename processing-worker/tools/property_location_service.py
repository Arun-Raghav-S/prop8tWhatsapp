"""
Property Location Service
Comprehensive service for handling property location requests, brochures, and nearby places
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger
from tools.location_tools import location_tools_handler
from tools.property_details_tool import property_details_tool

logger = setup_logger(__name__)


class PropertyLocationService:
    """
    Unified service for all property location operations
    """
    
    def __init__(self):
        self.brochure_api_url = "https://auth.propzing.com/functions/v1/send_brochure_location"
        self.auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTI5Mjc4NiwiZXhwIjoyMDQwODY4Nzg2fQ.CYPKYDqOuOtU7V9QhZ-U21C1fvuGZ-swUEm8beWc_X0"
        self.location_tools = location_tools_handler
    
    async def send_property_location_brochure(self, property_id: str, user_phone: str, whatsapp_account: str, org_id: str = "4462c6c4-3d71-4b4d-ace7-1659ebc8424a") -> Dict[str, Any]:
        """
        Send property location brochure using the specific API endpoint
        
        Args:
            property_id: The property UUID
            user_phone: User's phone number (without +)
            whatsapp_account: WhatsApp business account ID
            org_id: Organization ID
            
        Returns:
            Dict with success status and response
        """
        try:
            logger.info(f"📍 Sending location brochure for property: {property_id} to {user_phone}")
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.auth_token,
                'Cookie': '__cf_bm=6o8HOhMjeo4RWkHFWVjyQ7fGiB.FvyPVTv9u8xPhztA-1753794322-1.0.1.1-Mk_vIRYRXR.kF6J.wOINfroBfc_ExfYduSi3MJLtbGxCJP2kmoZBedMh5c9wZU8Cf.w.4P0BZxkA9e8X1_K_KS9zQiVTdGjVxy6riHbZTGA'
            }
            
            # Clean phone number (remove + if present)
            clean_phone = user_phone.replace('+', '')
            
            payload = {
                "project_id": property_id,  # Use property_id as project_id
                "whatsapp_account_number": whatsapp_account,
                "send_to": clean_phone,
                "type": "brochure",
                "isProperty": True,  # Set to True for property location
                "org_id": org_id
            }
            
            logger.info(f"🔧 Location brochure API call:")
            logger.info(f"🔧 URL: {self.brochure_api_url}")
            logger.info(f"🔧 Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                self.brochure_api_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Location brochure sent successfully: {result}")
                return {
                    "success": True,
                    "message": "Location brochure sent successfully",
                    "response": result
                }
            else:
                logger.error(f"❌ Location brochure API failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "message": "Failed to send location brochure"
                }
                
        except Exception as e:
            logger.error(f"❌ Error sending location brochure: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Error sending location brochure"
            }
    
    async def handle_location_request(self, property_id: str, user_phone: str, whatsapp_account: str, message: str = "") -> str:
        """
        Handle any location-related request for a property
        
        Args:
            property_id: The property UUID
            user_phone: User's phone number
            whatsapp_account: WhatsApp business account ID
            message: User's original message for context
            
        Returns:
            Response message for the user
        """
        try:
            logger.info(f"🗺️ Handling location request for property: {property_id}")
            
            # Get property details first
            property_data = await property_details_tool.get_property_details(property_id)
            
            if not property_data:
                return "I couldn't find the property details. Please try again or select a different property."
            
            # Send location brochure
            brochure_result = await self.send_property_location_brochure(
                property_id=property_id,
                user_phone=user_phone,
                whatsapp_account=whatsapp_account
            )
            
            if brochure_result.get("success"):
                # Extract property name for response
                property_name = property_data.get('title') or property_data.get('building_name') or 'the property'
                address = property_data.get('address', {})
                if isinstance(address, str):
                    try:
                        address = json.loads(address)
                    except:
                        address = {}
                
                locality = address.get('locality', 'Dubai') if address else 'Dubai'
                
                response = f"""📍 **Location Details Sent!**

I've sent you the detailed location information for *{property_name}* in {locality}.

📱 The location brochure includes:
• Interactive map with exact location
• Nearby landmarks and amenities
• Transportation links
• Neighborhood highlights

🗺️ You should receive it as a separate message shortly. Check your chat for the location card!

💬 Need anything else about this property? I can help with:
• Nearby hospitals, schools, or malls
• Route planning and directions
• Property viewing appointments"""

                return response
            else:
                # Fallback response if brochure fails
                property_name = property_data.get('title') or property_data.get('building_name') or 'this property'
                address = property_data.get('address', {})
                if isinstance(address, str):
                    try:
                        address = json.loads(address)
                    except:
                        address = {}
                
                location_text = ""
                if address:
                    locality = address.get('locality', '')
                    city = address.get('city', 'Dubai')
                    area = address.get('area', '')
                    
                    location_parts = [part for part in [locality, area, city] if part]
                    location_text = ', '.join(location_parts)
                
                if not location_text:
                    location_text = "Dubai"
                
                return f"""📍 **Location Information**

*{property_name}* is located in {location_text}.

I'm having trouble sending the detailed location brochure right now, but I can help you with:

🗺️ **What would you like to know?**
• Nearby hospitals, schools, or shopping malls
• Route planning from your location
• Transportation options
• Neighborhood amenities

Just ask me about any specific nearby places!"""
                
        except Exception as e:
            logger.error(f"❌ Error handling location request: {str(e)}")
            return "I encountered an issue getting the location details. Please try again or let me know what specific location information you need."
    
    async def find_nearest_places(self, property_id: str, query: str, user_phone: str = None) -> str:
        """
        Find nearest places to a property and format response
        
        Args:
            property_id: The property UUID
            query: What to search for (e.g., "hospital", "school", "mall")
            user_phone: User's phone for logging
            
        Returns:
            Formatted response with nearest places
        """
        try:
            logger.info(f"🔍 Finding nearest {query} for property: {property_id}")
            
            # Get property details
            property_data = await property_details_tool.get_property_details(property_id)
            
            if not property_data:
                return f"I couldn't find the property details to search for nearby {query}. Please try again."
            
            # Use location tools to find nearest places
            result = await self.location_tools.find_nearest_place(property_data, query, k=3)
            
            if result.get('error'):
                # Check if we have fallback information, otherwise provide user-friendly message
                if result.get('has_fallback'):
                    # Use the fallback formatter which provides user-friendly message
                    return self.location_tools.format_nearest_places_response(result)
                else:
                    # Provide user-friendly message for other errors
                    property_name = property_data.get('building_name', 'this property')
                    return f"😔 Sorry, I couldn't find nearby {query} for *{property_name}* right now.\n\n💡 **What I can help you with:**\n• Send you the property location brochure\n• Provide property details and viewing information\n• Help you with other questions about the property\n\nTry asking me to \"send location brochure\" for an interactive map!"
            
            # Format the response
            formatted_response = self.location_tools.format_nearest_places_response(result)
            
            # Add helpful footer
            formatted_response += f"\n\n💡 **Need directions?** Ask me for route planning to any of these locations!"
            formatted_response += f"\n📍 **Want more details?** I can help you find other nearby amenities too."
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"❌ Error finding nearest {query}: {str(e)}")
            return f"I encountered an issue finding nearby {query}. Please try again or ask me about other nearby places."
    
    def detect_location_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect if a message is asking for location information
        
        Args:
            message: User's message
            
        Returns:
            Dict with intent detection results
        """
        message_lower = message.lower()
        
        # Location request keywords
        location_keywords = [
            'location', 'where', 'address', 'map', 'directions', 'route',
            'brochure', 'link', 'coordinates', 'navigate', 'find', 'show me'
        ]
        
        # Nearest places keywords
        nearest_keywords = [
            'nearest', 'nearby', 'close', 'around', 'near'
        ]
        
        # Specific place types
        place_types = [
            'hospital', 'school', 'mall', 'restaurant', 'pharmacy', 'bank',
            'metro', 'station', 'airport', 'beach', 'park', 'gym', 'clinic',
            'supermarket', 'grocery', 'cafe', 'hotel', 'mosque', 'church'
        ]
        
        is_location_request = any(keyword in message_lower for keyword in location_keywords)
        is_nearest_request = any(keyword in message_lower for keyword in nearest_keywords)
        
        place_type = None
        for place in place_types:
            if place in message_lower:
                place_type = place
                break
        
        # Determine intent
        if is_nearest_request and place_type:
            intent = "find_nearest"
            query = place_type
        elif is_location_request:
            intent = "get_location"
            query = None
        else:
            intent = "none"
            query = None
        
        return {
            "intent": intent,
            "query": query,
            "is_location_related": is_location_request or is_nearest_request,
            "confidence": 0.9 if (is_location_request or is_nearest_request) else 0.0
        }


# Global instance
property_location_service = PropertyLocationService()
