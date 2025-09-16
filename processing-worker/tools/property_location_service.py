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
from tools.smart_location_assistant import smart_location_assistant
from openai import AsyncOpenAI

logger = setup_logger(__name__)


class PropertyLocationService:
    """
    Unified service for all property location operations
    """
    
    def __init__(self):
        self.location_brochure_api_url = "https://auth.propzing.com/functions/v1/send_brochure_location"
        self.auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTI5Mjc4NiwiZXhwIjoyMDQwODY4Nzg2fQ.CYPKYDqOuOtU7V9QhZ-U21C1fvuGZ-swUEm8beWc_X0"
        self.location_tools = location_tools_handler
        self.openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    async def send_location_or_brochure_via_api(self, property_id: str, user_phone: str, whatsapp_account: str, request_type: str = "location", org_id: str = "4462c6c4-3d71-4b4d-ace7-1659ebc8424a") -> Dict[str, Any]:
        """
        Send location map or property brochure using the API endpoint
        
        Args:
            property_id: The property UUID
            user_phone: User's phone number (without +)
            whatsapp_account: WhatsApp business account ID
            request_type: "location" or "brochure"
            org_id: Organization ID
            
        Returns:
            Dict with success status and response
        """
        try:
            logger.info(f"📍 Sending {request_type} for property: {property_id} to {user_phone}")
            
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
                "type": request_type,  # Use the actual request type (location or brochure)
                "isProperty": True,  # Set to True for property location
                "org_id": org_id
            }
            
            logger.info(f"🔧 {request_type.title()} API call:")
            logger.info(f"🔧 URL: {self.location_brochure_api_url}")
            logger.info(f"🔧 Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                self.location_brochure_api_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ {request_type.title()} sent successfully: {result}")
                return {
                    "success": True,
                    "message": f"{request_type.title()} sent successfully",
                    "response": result
                }
            else:
                logger.error(f"❌ {request_type.title()} API failed: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "message": f"Failed to send {request_type}"
                }
                
        except Exception as e:
            logger.error(f"❌ Error sending {request_type}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Error sending {request_type}"
            }
    
    async def handle_location_request_router(self, property_id: str, user_phone: str, whatsapp_account: str, message: str = "") -> str:
        """
        Main router for handling all types of location-related requests
        
        Args:
            property_id: The property UUID
            user_phone: User's phone number
            whatsapp_account: WhatsApp business account ID
            message: User's original message for context
            
        Returns:
            Response message for the user
        """
        try:
            # Use AI to detect the user's intent
            intent_result = await self.detect_location_intent_ai(message)
            intent = intent_result.get('intent')
            
            if intent == 'find_nearest':
                # User wants to find nearby places
                place_query = intent_result.get('place_query', 'places')
                return await self.find_nearest_places(property_id, place_query, user_phone)
            
            elif intent in ['get_location', 'get_brochure']:
                # User wants location info or brochure
                return await self.send_location_or_brochure_request(property_id, user_phone, whatsapp_account, message)
            
            else:
                # Fallback for unclear requests
                return await self.send_location_or_brochure_request(property_id, user_phone, whatsapp_account, message)
                
        except Exception as e:
            logger.error(f"❌ Error routing location request: {str(e)}")
            return "I encountered an issue understanding your location request. Please try asking me to 'send location' or 'send brochure' or ask about nearby places."
    
    async def send_location_or_brochure_request(self, property_id: str, user_phone: str, whatsapp_account: str, message: str = "") -> str:
        """
        Handle location or brochure requests for a property
        
        Args:
            property_id: The property UUID
            user_phone: User's phone number
            whatsapp_account: WhatsApp business account ID
            message: User's original message for context
            
        Returns:
            Response message for the user
        """
        try:
            logger.info(f"🗺️ Handling location/brochure request for property: {property_id}")
            
            # Get property details first
            property_data = await property_details_tool.get_property_details(property_id)
            
            if not property_data:
                return "I couldn't find the property details. Please try again or select a different property."
            
            # Detect the specific intent from the message
            intent_result = await self.detect_location_intent_ai(message)
            request_type = intent_result.get('request_type', 'location')
            
            # Send location map or property brochure based on user intent
            api_result = await self.send_location_or_brochure_via_api(
                property_id=property_id,
                user_phone=user_phone,
                whatsapp_account=whatsapp_account,
                request_type=request_type
            )
            
            if api_result.get("success"):
                # Extract property name for response
                property_name = property_data.get('title') or property_data.get('building_name') or 'the property'
                address = property_data.get('address', {})
                if isinstance(address, str):
                    try:
                        address = json.loads(address)
                    except:
                        address = {}
                
                locality = address.get('locality', 'Dubai') if address else 'Dubai'
                
                if request_type == 'brochure':
                    response = f"""📄 **Property Brochure Sent!**

I've sent you the detailed property brochure for *{property_name}* in {locality}.

📋 The brochure includes:
• Property specifications and details
• Floor plans and layouts
• High-quality photos
• Pricing and payment options
• Amenities and features

📄 You should receive it as a separate message shortly. Check your chat for the property brochure!

💬 Need anything else about this property? I can help with:
• Nearby hospitals, schools, or malls
• Route planning and directions
• Property viewing appointments"""
                else:
                    response = f"""📍 **Interactive Location Map Sent!**

I've sent you the interactive location map for *{property_name}* in {locality}.

🗺️ The map includes:
• Interactive map with exact location
• Nearby landmarks and amenities
• Transportation links
• Neighborhood highlights

📱 You should receive it as a location card shortly. Check your chat!

💬 Need more details? I can help with:
• Sending the property brochure with specifications
• Finding nearby hospitals, schools, or malls
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

I'm having trouble sending the {request_type} right now, but I can help you with:

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
                    return f"😔 Sorry, I couldn't find nearby {query} for *{property_name}* right now.\n\n💡 **What I can help you with:**\n• Send you the property location information\n• Send you a detailed location map\n• Provide property details and viewing information\n• Help you with other questions about the property\n\nTry asking me to \"share location\" for an interactive map!"
            
            # Format the response
            formatted_response = self.location_tools.format_nearest_places_response(result)
            
            # Add helpful footer
            formatted_response += f"\n\n💡 **Need directions?** Ask me for route planning to any of these locations!"
            formatted_response += f"\n📍 **Want more details?** I can help you find other nearby amenities too."
            
            return formatted_response
            
        except Exception as e:
            logger.error(f"❌ Error finding nearest {query}: {str(e)}")
            return f"I encountered an issue finding nearby {query}. Please try again or ask me about other nearby places."
    
    async def detect_location_intent_ai(self, message: str) -> Dict[str, Any]:
        """
        Use AI to detect location intent and determine the specific request type
        
        Args:
            message: User's message
            
        Returns:
            Dict with intent detection results
        """
        try:
            prompt = f"""
Analyze the following user message and determine their location-related intent.

User message: "{message}"

Classify the intent into one of these categories:
1. "get_location" - User wants basic location/address information
2. "get_brochure" - User specifically wants a brochure or detailed location card
3. "find_nearest" - User wants to find nearby places (hospitals, schools, malls, etc.)
4. "none" - Not location related

If it's "find_nearest", extract what type of place they're looking for.

Respond in JSON format:
{{
    "intent": "get_location|get_brochure|find_nearest|none",
    "request_type": "location|brochure" (only for get_location or get_brochure),
    "place_query": "extracted place type" (only for find_nearest),
    "confidence": 0.0-1.0
}}

Examples:
- "Share location" -> {{"intent": "get_location", "request_type": "location", "confidence": 0.9}}
- "Send brochure" -> {{"intent": "get_brochure", "request_type": "brochure", "confidence": 0.9}}
- "What are nearby schools" -> {{"intent": "find_nearest", "place_query": "school", "confidence": 0.9}}
- "Hello" -> {{"intent": "none", "confidence": 0.1}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at understanding user location-related intents. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result_str = response.choices[0].message.content.strip()
            result = json.loads(result_str)
            
            logger.info(f"🧠 AI Location Intent Analysis: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in AI intent detection: {str(e)}")
            # Fallback to basic keyword detection
            message_lower = message.lower()
            
            if any(word in message_lower for word in ['brochure', 'card', 'detailed']):
                return {"intent": "get_brochure", "request_type": "brochure", "confidence": 0.7}
            elif any(word in message_lower for word in ['location', 'address', 'where', 'share']):
                return {"intent": "get_location", "request_type": "location", "confidence": 0.7}
            elif any(word in message_lower for word in ['nearby', 'nearest', 'close', 'around']):
                # Try to extract place type
                place_types = ['hospital', 'school', 'mall', 'restaurant', 'pharmacy', 'bank', 'metro', 'station', 'airport', 'beach', 'park', 'gym', 'clinic', 'supermarket', 'grocery', 'cafe', 'hotel', 'mosque', 'church']
                place_query = next((place for place in place_types if place in message_lower), "places")
                return {"intent": "find_nearest", "place_query": place_query, "confidence": 0.7}
            else:
                return {"intent": "none", "confidence": 0.1}


    # Enhanced method using new smart assistant
    async def handle_location_request(self, property_id: str, user_phone: str, whatsapp_account: str, message: str = "") -> str:
        """
        Enhanced location request handler using Smart Location Assistant
        Provides backward compatibility while using improved AI-based routing
        """
        logger.info(f"🔄 Routing location request to Smart Location Assistant")
        return await smart_location_assistant.handle_location_request(
            property_id=property_id,
            user_phone=user_phone,
            whatsapp_account=whatsapp_account,
            user_message=message
        )
    
    # Legacy methods for backward compatibility
    async def handle_location_request_router(self, property_id: str, user_phone: str, whatsapp_account: str, message: str = "") -> str:
        """Legacy method - redirects to the new smart assistant"""
        return await self.handle_location_request(property_id, user_phone, whatsapp_account, message)
    
    def detect_location_intent(self, message: str) -> Dict[str, Any]:
        """
        Legacy sync method for backward compatibility
        Note: This is a blocking call and should be avoided. Use detect_location_intent_ai instead.
        """
        logger.warning(f"⚠️ Using legacy sync detect_location_intent method. Consider upgrading to detect_location_intent_ai")
        # Provide a basic fallback using simple keyword detection
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['nearby', 'nearest', 'close', 'around']):
            # Try to extract place type
            place_types = ['hospital', 'school', 'mall', 'restaurant', 'pharmacy', 'bank', 'metro', 'station', 'airport', 'beach', 'park', 'gym', 'clinic', 'supermarket', 'grocery', 'cafe', 'hotel', 'mosque', 'church']
            place_query = next((place for place in place_types if place in message_lower), "places")
            return {"intent": "find_nearest", "query": place_query, "confidence": 0.7}
        elif any(word in message_lower for word in ['brochure', 'card', 'detailed']):
            return {"intent": "get_brochure", "confidence": 0.7}
        elif any(word in message_lower for word in ['location', 'address', 'where', 'share']):
            return {"intent": "get_location", "confidence": 0.7}
        else:
            return {"intent": "get_location", "confidence": 0.5}


# Global instance
property_location_service = PropertyLocationService()
