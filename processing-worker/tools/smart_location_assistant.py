"""
Smart Location Assistant
AI-powered location service for comprehensive property location needs

This assistant handles:
- Location information sharing (coordinates, addresses)
- Interactive location maps
- Nearby places discovery (hospitals, schools, malls, etc.)
- Route planning and directions
- Location-based property context

Uses AI for intent detection and provides enhanced user experience.
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger
from tools.property_details_tool import property_details_tool
from openai import AsyncOpenAI

logger = setup_logger(__name__)


class SmartLocationAssistant:
    """
    AI-powered location assistant that understands user intent and provides
    comprehensive location services for properties
    """
    
    def __init__(self):
        self.location_api_url = "https://auth.propzing.com/functions/v1/send_brochure_location"
        self.places_api_url = "https://auth.propzing.com/functions/v1/whatsapp_agency_tools"
        self.auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcyNTI5Mjc4NiwiZXhwIjoyMDQwODY4Nzg2fQ.CYPKYDqOuOtU7V9QhZ-U21C1fvuGZ-swUEm8beWc_X0"
        
        # Standard organization ID (can be parameterized if needed)
        self.default_org_id = "4462c6c4-3d71-4b4d-ace7-1659ebc8424a"
        
        # Initialize OpenAI client as instance attribute for easier testing
        self.openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    async def analyze_location_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Use AI to understand what kind of location help the user needs
        
        Args:
            user_message: What the user asked
            
        Returns:
            Dict with intent analysis and recommendations
        """
        try:
            prompt = f"""
Analyze this user message about location and determine their specific need:

User message: "{user_message}"

Classify their intent into ONE of these categories:

1. "share_location" - User wants detailed interactive location map
   Keywords: "share location", "location map", "interactive map", "location"

2. "send_brochure" - User wants property brochure PDF/document
   Keywords: "brochure", "property brochure", "pdf", "document"

3. "find_nearby" - User wants to find nearby places (hospitals, schools, etc.)
   Keywords: "nearby", "closest", "near", "around", plus place types

4. "get_directions" - User wants route planning or directions
   Keywords: "directions", "route", "how to get", "navigate"

If it's "find_nearby", also extract what type of place they want.

Respond in JSON:
{{
    "intent": "share_location|send_brochure|find_nearby|get_directions",
    "place_type": "hospital|school|mall|restaurant|etc." (only for find_nearby),
    "confidence": 0.0-1.0,
    "user_friendly_description": "Clear description of what user wants"
}}

Examples:
- "Share location" → {{"intent": "share_location", "confidence": 0.9, "user_friendly_description": "User wants interactive location map"}}
- "Send me the brochure" → {{"intent": "send_brochure", "confidence": 0.9, "user_friendly_description": "User wants property brochure PDF"}}
- "What are nearby schools" → {{"intent": "find_nearby", "place_type": "school", "confidence": 0.9, "user_friendly_description": "User wants to find nearby schools"}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at understanding location-related requests. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            logger.info(f"🧠 Location Intent Analysis: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ AI intent analysis failed: {str(e)}")
            # Fallback to simple keyword detection
            message_lower = user_message.lower()
            
            if any(word in message_lower for word in ['brochure', 'pdf', 'document']):
                return {"intent": "send_brochure", "confidence": 0.7, "user_friendly_description": "User likely wants property brochure"}
            elif any(word in message_lower for word in ['share location', 'location map', 'interactive map', 'map']):
                return {"intent": "share_location", "confidence": 0.7, "user_friendly_description": "User likely wants location map"}
            elif any(word in message_lower for word in ['nearby', 'closest', 'around', 'near']):
                return {"intent": "find_nearby", "place_type": "place", "confidence": 0.7, "user_friendly_description": "User wants to find nearby places"}
            elif any(word in message_lower for word in ['directions', 'route', 'navigate', 'how to get']):
                return {"intent": "get_directions", "confidence": 0.7, "user_friendly_description": "User wants directions"}
            else:
                return {"intent": "share_location", "confidence": 0.6, "user_friendly_description": "User wants basic location information"}
    
    async def handle_location_request(self, property_id: str, user_phone: str, whatsapp_account: str, user_message: str) -> str:
        """
        Main entry point - analyzes user intent and routes to appropriate service
        
        Args:
            property_id: Property UUID
            user_phone: User's phone number
            whatsapp_account: WhatsApp business account ID
            user_message: What the user asked for
            
        Returns:
            Response message for user
        """
        try:
            logger.info(f"🎯 Smart Location Assistant processing: '{user_message}' for property {property_id}")
            
            # Analyze what the user actually wants
            intent_analysis = await self.analyze_location_intent(user_message)
            intent = intent_analysis.get('intent')
            
            logger.info(f"🎯 Routing to intent: {intent}")
            
            # Route to appropriate service
            if intent == 'send_brochure':
                return await self.send_property_brochure(property_id, user_phone, whatsapp_account)
            elif intent == 'share_location':
                return await self.send_location_map(property_id, user_phone, whatsapp_account)
            elif intent == 'find_nearby':
                place_type = intent_analysis.get('place_type', 'place')
                return await self.find_nearby_places(property_id, place_type, user_phone)
            elif intent == 'get_directions':
                return await self.provide_directions_help(property_id)
            else:
                # Default to basic location
                return await self.send_basic_location(property_id, user_phone, whatsapp_account)
                
        except Exception as e:
            logger.error(f"❌ Error in smart location assistant: {str(e)}")
            return "I had trouble understanding your location request. Please try asking me to 'share location', 'send brochure', or ask about nearby places like 'find nearby schools'."
    
    async def send_property_brochure(self, property_id: str, user_phone: str, whatsapp_account: str) -> str:
        """Send property brochure PDF/document"""
        return await self._send_location_data(property_id, user_phone, whatsapp_account, "brochure")
    
    async def send_location_map(self, property_id: str, user_phone: str, whatsapp_account: str) -> str:
        """Send interactive location map"""
        return await self._send_location_data(property_id, user_phone, whatsapp_account, "location")
    
    async def _send_location_data(self, property_id: str, user_phone: str, whatsapp_account: str, data_type: str) -> str:
        """
        Internal method to send location data via API
        
        Args:
            property_id: Property UUID
            user_phone: User's phone number
            whatsapp_account: WhatsApp business account
            data_type: "location" or "brochure"
        """
        try:
            logger.info(f"📍 Sending {data_type} for property {property_id}")
            
            # Get property details first
            property_data = await property_details_tool.get_property_details(property_id)
            if not property_data:
                return "I couldn't find the property details. Please try again or select a different property."
            
            # Prepare API call
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.auth_token,
                'Cookie': '__cf_bm=6o8HOhMjeo4RWkHFWVjyQ7fGiB.FvyPVTv9u8xPhztA-1753794322-1.0.1.1-Mk_vIRYRXR.kF6J.wOINfroBfc_ExfYduSi3MJLtbGxCJP2kmoZBedMh5c9wZU8Cf.w.4P0BZxkA9e8X1_K_KS9zQiVTdGjVxy6riHbZTGA'
            }
            
            payload = {
                "project_id": property_id,
                "whatsapp_account_number": whatsapp_account,
                "send_to": user_phone.replace('+', ''),
                "type": data_type,
                "isProperty": True,
                "org_id": self.default_org_id
            }
            
            logger.info(f"🔧 API Call - URL: {self.location_api_url}")
            logger.info(f"🔧 Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                self.location_api_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            property_name = property_data.get('title') or property_data.get('building_name') or 'the property'
            address = property_data.get('address', {})
            if isinstance(address, str):
                try:
                    address = json.loads(address)
                except:
                    address = {}
            
            locality = address.get('locality', 'Dubai') if address else 'Dubai'
            
            if response.status_code == 200:
                logger.info(f"✅ {data_type.title()} sent successfully")
                
                if data_type == 'brochure':
                    return f"""📄 **Property Brochure Sent!**

I've sent you the detailed property brochure for *{property_name}* in {locality}.

📋 The brochure includes:
• Property details and specifications
• Floor plans and layouts
• High-quality photos
• Pricing and payment options
• Amenities and features

📱 You should receive it as a location card shortly. Check your chat!

💬 Need more help? I can:
• Find specific nearby places (hospitals, schools, malls)
• Provide route planning assistance
• Help with property viewing appointments"""
                
                else:
                    return f"""📍 **Interactive Location Map Sent!**

I've sent you the interactive location map for *{property_name}* in {locality}.

🗺️ The map includes:
• Interactive map with pinpoint location
• Nearby landmarks and amenities
• Transportation options
• Neighborhood highlights
• Street view integration

📱 You should receive it as a location card shortly. Check your chat!

🔍 Want more? I can also:
• Send you a detailed property brochure
• Find nearby hospitals, schools, or shopping centers
• Help with directions and route planning
• Assist with property viewing appointments"""
            
            else:
                logger.error(f"❌ API failed: {response.status_code} - {response.text}")
                
                # Provide helpful fallback response
                location_text = f"{locality}" if locality != 'Dubai' else "Dubai"
                
                return f"""📍 **Location Information**

*{property_name}* is located in {location_text}.

I'm having trouble sending the {data_type} right now, but I can help you with:

🗺️ **Alternative options:**
• Provide detailed address information
• Find nearby amenities (hospitals, schools, malls)
• Help with route planning
• Assist with property viewing arrangements

Just let me know what specific location information you need!"""
                
        except Exception as e:
            logger.error(f"❌ Error sending {data_type}: {str(e)}")
            return f"I encountered an issue sending the {data_type}. Please try again or let me know what specific location information you need."
    
    async def find_nearby_places(self, property_id: str, place_type: str, user_phone: str = None) -> str:
        """
        Find and return nearby places with AI-enhanced search
        
        Args:
            property_id: Property UUID
            place_type: Type of place to find
            user_phone: User's phone (for logging)
            
        Returns:
            Formatted response with nearby places
        """
        try:
            logger.info(f"🔍 Finding nearby {place_type} for property {property_id}")
            
            # Get property details
            property_data = await property_details_tool.get_property_details(property_id)
            if not property_data:
                return f"I couldn't find the property details to search for nearby {place_type}. Please try again."
            
            # Extract coordinates
            address_data = property_data.get('address', {})
            coordinates = self._extract_coordinates(address_data)
            
            if not coordinates:
                property_name = property_data.get('building_name', 'this property')
                return f"""😔 I don't have exact coordinates for *{property_name}* to find nearby {place_type}.

📍 **What I can do instead:**
• Send you the property location map
• Provide general area information
• Help with property details and viewing appointments

Try asking me to "share location" for a map with nearby amenities!"""
            
            # Search for places
            lat, lng = coordinates
            location_string = f"{lat},{lng}"
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjUyOTI3ODYsImV4cCI6MjA0MDg2ODc4Nn0.11GJjOlgPf4RocdFjMnWGJpBqFVk1wmbW27OmV0YAzs"
            }
            
            payload = {
                "action": "findNearestPlace",
                "query": place_type,
                "location": location_string,
                "k": 3
            }
            
            logger.info(f"🔧 Places API call: {json.dumps(payload, indent=2)}")
            
            response = requests.post(
                self.places_api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            property_name = property_data.get('building_name', 'the property')
            
            if response.status_code == 200:
                result = response.json()
                places = result.get('nearestPlaces', [])
                
                if not places:
                    return f"""😔 Sorry, I couldn't find any {place_type} near *{property_name}* right now.

💡 **Alternative options:**
• Try asking for a different type (hospital, school, mall, restaurant)
• Request the location map
• I can help with general area information

What else would you like to know about the location?"""
                
                # Format successful response
                response_lines = [f"🔍 **Nearest {place_type} to {property_name}:**\n"]
                
                for i, place in enumerate(places, 1):
                    name = place.get('name', 'Unknown Place')
                    address = place.get('address', 'No address available')
                    rating = place.get('rating')
                    
                    rating_str = f" ⭐ {rating}" if rating else ""
                    response_lines.append(f"{i}. **{name}**{rating_str}")
                    response_lines.append(f"   📍 {address}\n")
                
                response_lines.append("💡 **Need directions?** Ask me for route planning to any of these locations!")
                response_lines.append("📍 **Want more options?** I can help find other nearby amenities too.")
                
                return '\n'.join(response_lines)
            
            else:
                logger.error(f"❌ Places API failed: {response.status_code} - {response.text}")
                return f"""😔 I had trouble finding nearby {place_type} for *{property_name}* right now.

💡 **What I can help with:**
• Send location  with interactive map showing nearby places
• Provide general property location information
• Help with other property questions

Try asking to "share location" to see nearby amenities on a map!"""
                
        except Exception as e:
            logger.error(f"❌ Error finding nearby {place_type}: {str(e)}")
            return f"I encountered an issue finding nearby {place_type}. Please try again or ask to share location instead."
    
    async def provide_directions_help(self, property_id: str) -> str:
        """Provide directions and route planning assistance"""
        try:
            property_data = await property_details_tool.get_property_details(property_id)
            if not property_data:
                return "I couldn't find the property details for route planning. Please try again."
            
            property_name = property_data.get('building_name', 'the property')
            
            return f"""🗺️ **Route Planning for {property_name}**

I can help you with directions! Here's how:

📍 **For Navigation:**
• Ask me to "share location" for an interactive map
• The brochure includes GPS coordinates for your navigation app
• You'll get the exact location for Google Maps/Waze

🚗 **Route Options:**
• Tell me where you're coming from and I'll help plan the route
• Ask about nearby metro stations or public transport
• I can find nearby landmarks to help with navigation

💬 **Just ask me:**
• "Share location" - for interactive map
• "Find nearby metro stations" - for public transport
• "What's the exact address" - for manual navigation

What would you like to know about getting to *{property_name}*?"""
            
        except Exception as e:
            logger.error(f"❌ Error providing directions help: {str(e)}")
            return "I had trouble accessing the property information for directions. Please try asking to share location instead."
    
    def _extract_coordinates(self, address_data: Dict[str, Any]) -> Optional[tuple]:
        """Extract lat/lng coordinates from address data"""
        try:
            if not address_data:
                return None
            
            # Handle JSON string
            if isinstance(address_data, str):
                try:
                    address_data = json.loads(address_data)
                except json.JSONDecodeError:
                    return None
            
            # Try different coordinate formats
            lat = address_data.get('latitude') or address_data.get('lat')
            lng = address_data.get('longitude') or address_data.get('lng')
            
            if lat and lng:
                return (float(lat), float(lng))
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting coordinates: {str(e)}")
            return None


# Create global instance
smart_location_assistant = SmartLocationAssistant()
