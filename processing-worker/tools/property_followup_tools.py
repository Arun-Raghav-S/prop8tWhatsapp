"""
Property Follow-up Tools for WhatsApp Agent System
Tools for handling follow-up questions about active properties
"""

import os
import json
import time
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from datetime import datetime

from utils.logger import setup_logger
from utils.text_processor import MessageProcessor

logger = setup_logger(__name__)
message_processor = MessageProcessor()


class PropertyLocationTool:
    """
    Tool for providing detailed location information about active properties
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai = openai_client
    
    async def get_location_details(self, property_data: Dict[str, Any]) -> str:
        """
        Get detailed location information for a property
        """
        try:
            # Log the API call that would be made
            property_id = property_data.get('id', 'unknown')
            logger.info(f"🗺️ LOCATION API CALL: property_id={property_id}")
            logger.info(f"🗺️ API URL would be: /api/properties/{property_id}/location")
            
            # Extract location info from property data
            address = property_data.get('address', {})
            building_name = property_data.get('building_name', 'N/A')
            
            # Create a comprehensive location response
            location_info = {
                "building": building_name,
                "locality": address.get('locality', 'N/A'),
                "city": address.get('city', 'N/A'),
                "area": address.get('area', 'N/A'),
                "emirate": address.get('emirate', 'Dubai'),
                "property_type": property_data.get('property_type', 'N/A'),
                "nearby_landmarks": self._get_nearby_landmarks(address.get('locality', ''))
            }
            
            # Generate WhatsApp-optimized location response
            from utils.whatsapp_formatter import whatsapp_formatter
            property_data_formatted = {
                'building_name': building_name,
                'address': address
            }
            return whatsapp_formatter.format_location_info(property_data_formatted)
            
        except Exception as e:
            logger.error(f"Location tool failed: {str(e)}")
            return "I'm sorry, I couldn't retrieve the location details for this property right now."
    
    def _get_nearby_landmarks(self, locality: str) -> list:
        """
        Get nearby landmarks based on locality (mock data for now)
        """
        landmark_map = {
            "dubai marina": ["Marina Mall", "JBR Beach", "Marina Walk"],
            "downtown dubai": ["Burj Khalifa", "Dubai Mall", "Dubai Fountain"],
            "jumeirah beach residence": ["The Beach Mall", "JBR Beach", "Marina Walk"],
            "palm jumeirah": ["Atlantis Resort", "Nakheel Mall", "Golden Mile"],
            "business bay": ["Burj Khalifa", "Dubai Water Canal", "Business Bay Metro"],
            "difc": ["Emirates Towers", "Dubai International Financial Centre", "Gate Village"],
            "jlt": ["JLT Metro Station", "Cluster Lakes", "Dubai Marina"]
        }
        
        locality_lower = locality.lower()
        for area, landmarks in landmark_map.items():
            if area in locality_lower:
                return landmarks
        
        return ["Dubai Metro", "Major Shopping Centers", "Healthcare Facilities"]
    
    async def _generate_location_response(self, location_info: Dict[str, Any]) -> str:
        """
        Generate a natural language response about the location
        """
        try:
            landmarks_text = ", ".join(location_info["nearby_landmarks"])
            
            prompt = f"""
Generate a friendly and informative location response for a property. Keep it concise and mobile-friendly.

Property Location Details:
- Building: {location_info["building"]}
- Area: {location_info["locality"]}
- City: {location_info["city"]}
- Property Type: {location_info["property_type"]}
- Nearby Landmarks: {landmarks_text}

Generate a response that:
1. Confirms the location clearly
2. Mentions key nearby landmarks/amenities
3. Uses appropriate emojis for WhatsApp
4. Keeps it under 200 words
5. Sounds natural and helpful

Start with "📍 Here's the location:" and make it conversational.
"""

            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=250
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Location response generation failed: {str(e)}")
            return f"📍 Here's the location:\n\n🏢 **{location_info['building']}**\n📍 {location_info['locality']}, {location_info['city']}\n\n🌟 **Nearby:** {', '.join(location_info['nearby_landmarks'])}"


class PropertyVisitScheduler:
    """
    Tool for scheduling property visits
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai = openai_client
    
    async def collect_visit_details(self, message: str, property_data: Dict[str, Any], session_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract visit scheduling details from user message
        """
        try:
            # Check if we already have partial booking data
            booking_data = session_context.get('pending_visit_booking', {})
            
            # Extract date and time from the message
            extraction_prompt = f"""
Extract visit scheduling information from this message: "{message}"

Current booking data: {json.dumps(booking_data)}

Extract and return JSON with:
{{
    "has_date": boolean,
    "has_time": boolean,
    "date": "YYYY-MM-DD or null",
    "time": "HH:MM or null", 
    "date_text": "extracted date text or null",
    "time_text": "extracted time text or null",
    "is_complete": boolean,
    "missing_info": ["date", "time"] // what's still needed
}}

Examples:
- "tomorrow at 3pm" → has_date: true, has_time: true, is_complete: true
- "next Friday" → has_date: true, has_time: false, is_complete: false
- "at 2 o'clock" → has_date: false, has_time: true, is_complete: false
- "schedule a visit" → has_date: false, has_time: false, is_complete: false

Return only valid JSON.
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Update booking data
            if extracted_data.get('has_date'):
                booking_data['date'] = extracted_data.get('date')
                booking_data['date_text'] = extracted_data.get('date_text')
            
            if extracted_data.get('has_time'):
                booking_data['time'] = extracted_data.get('time')
                booking_data['time_text'] = extracted_data.get('time_text')
            
            booking_data['property_id'] = property_data.get('id')
            booking_data['property_info'] = {
                'building_name': property_data.get('building_name'),
                'locality': property_data.get('address', {}).get('locality'),
                'property_type': property_data.get('property_type')
            }
            
            return {
                'booking_data': booking_data,
                'is_complete': extracted_data.get('is_complete', False),
                'missing_info': extracted_data.get('missing_info', [])
            }
            
        except Exception as e:
            logger.error(f"Visit details collection failed: {str(e)}")
            return {
                'booking_data': {},
                'is_complete': False,
                'missing_info': ['date', 'time']
            }
    
    async def schedule_visit(self, booking_data: Dict[str, Any]) -> str:
        """
        Schedule the property visit with proper booking confirmation
        """
        try:
            property_id = booking_data.get('property_id')
            visit_date = booking_data.get('date')
            visit_time = booking_data.get('time')
            property_info = booking_data.get('property_info', {})
            
            # Generate a unique booking reference
            import uuid
            booking_ref = str(uuid.uuid4())[:8].upper()
            
            # Log the successful booking
            logger.info(f"✅ VISIT SCHEDULED: {booking_ref} for property {property_id}")
            logger.info(f"📅 Date: {booking_data.get('date_text', visit_date)}, Time: {booking_data.get('time_text', visit_time)}")
            
            # In a real implementation, this would make an API call to the booking system
            # For now, we'll create a comprehensive confirmation
            
            from utils.whatsapp_formatter import whatsapp_formatter
            return whatsapp_formatter.format_followup_booking(property_id, booking_ref)
            
        except Exception as e:
            logger.error(f"Visit scheduling failed: {str(e)}")
            return "I'm sorry, I couldn't schedule the visit right now. Please try again or contact us directly."
    
    async def ask_for_missing_info(self, missing_info: list, property_data: Dict[str, Any]) -> str:
        """
        Generate a response asking for missing visit information
        """
        try:
            property_info = f"{property_data.get('building_name', 'the property')} in {property_data.get('address', {}).get('locality', 'Dubai')}"
            
            if 'date' in missing_info and 'time' in missing_info:
                return f"🗓️ I'd be happy to schedule a visit to **{property_info}**!\n\nWhen would you like to visit? Please let me know your preferred date and time.\n\n📅 **Example:** \"Tomorrow at 3 PM\" or \"Next Friday at 10 AM\""
            
            elif 'date' in missing_info:
                return f"📅 What date would you prefer for visiting **{property_info}**?\n\n**Example:** \"Tomorrow\", \"Next Friday\", or \"January 15th\""
            
            elif 'time' in missing_info:
                return f"⏰ What time would work best for your visit to **{property_info}**?\n\n**Example:** \"10 AM\", \"3 PM\", or \"Evening\""
            
            else:
                return f"✅ Perfect! Let me schedule your visit to **{property_info}**."
                
        except Exception as e:
            logger.error(f"Missing info response generation failed: {str(e)}")
            return "Please provide the date and time for your visit."


class PropertyFollowupHandler:
    """
    Main handler for property follow-up tools
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai = openai_client
        self.location_tool = PropertyLocationTool(openai_client)
        self.visit_scheduler = PropertyVisitScheduler(openai_client)
        
        # Import location tools handler
        from .location_tools import location_tools_handler
        self.location_tools = location_tools_handler
    
    async def detect_followup_intent(self, message: str, has_active_properties: bool) -> Dict[str, Any]:
        """
        Professional intent detection with spell correction and pattern matching
        """
        if not has_active_properties:
            return {"is_followup": False, "intent": None}
        
        try:
            # STEP 1: Professional message processing
            processed = message_processor.process_message(message)
            corrected_message = processed['corrected']
            
            logger.info(f"🔧 Message processed: '{message}' → '{corrected_message}'")
            if processed['corrections_made']:
                logger.info(f"✏️ Corrections: {processed['corrections_made']}")
            
            # STEP 2: Fast intent detection using processed message
            if message_processor.is_booking_message(processed):
                property_ref = message_processor.extract_property_reference(processed)
                return {
                    "is_followup": True,
                    "intent": "visit",
                    "property_reference": property_ref or "first",
                    "confidence": processed['confidence']
                }
            
            # STEP 3: Check for nearest place queries
            nearest_place_keywords = ['nearest', 'nearby', 'close', 'hospital', 'school', 'restaurant', 'mall', 'airport', 'metro', 'bus', 'pharmacy', 'bank', 'grocery', 'market', 'gym', 'park']
            if any(keyword in corrected_message.lower() for keyword in nearest_place_keywords):
                property_ref = message_processor.extract_property_reference(processed)
                return {
                    "is_followup": True,
                    "intent": "nearest_place",
                    "property_reference": property_ref or "first",
                    "confidence": processed['confidence'],
                    "query": corrected_message
                }
            
            # STEP 4: Check for route/direction queries
            route_keywords = ['route', 'direction', 'how to reach', 'how to get', 'distance', 'travel time', 'driving', 'walking', 'commute']
            if any(keyword in corrected_message.lower() for keyword in route_keywords):
                property_ref = message_processor.extract_property_reference(processed)
                return {
                    "is_followup": True,
                    "intent": "route",
                    "property_reference": property_ref or "first",
                    "confidence": processed['confidence'],
                    "query": corrected_message
                }
            
            # STEP 5: Check for general location queries
            location_keywords = ['where', 'location', 'address', 'area']
            if any(keyword in corrected_message.lower() for keyword in location_keywords):
                property_ref = message_processor.extract_property_reference(processed)
                return {
                    "is_followup": True,
                    "intent": "location",
                    "property_reference": property_ref or "first",
                    "confidence": processed['confidence']
                }
            
            # STEP 6: General property questions
            property_keywords = ['price', 'cost', 'features', 'amenities', 'details', 'info', 'tell me']
            if any(keyword in corrected_message.lower() for keyword in property_keywords):
                property_ref = message_processor.extract_property_reference(processed)
                return {
                    "is_followup": True,
                    "intent": "general",
                    "property_reference": property_ref or "first", 
                    "confidence": processed['confidence']
                }
            
            # STEP 7: Fallback for unclear messages
            if processed['intent_signals']['has_property_reference']:
                return {
                    "is_followup": True,
                    "intent": "general",
                    "property_reference": "first",
                    "confidence": 0.6
                }
            
            return {"is_followup": False, "intent": None}
            
        except Exception as e:
            logger.error(f"Intent detection failed: {str(e)}")
            
            # Emergency fallback for booking-like patterns
            booking_indicators = ['tomorrow', 'tyomorrow', 'am', 'pm', 'schedule', 'book', 'visit']
            if any(indicator in message.lower() for indicator in booking_indicators):
                return {
                    "is_followup": True,
                    "intent": "visit",
                    "property_reference": "first",
                    "confidence": 0.7
                }
            
            return {"is_followup": False, "intent": None}