"""
Location-based Tools for WhatsApp Agent System
Tools for finding nearest places and calculating routes using property coordinates
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger
from openai import AsyncOpenAI

# Import smart location assistant for enhanced functionality
# Note: Import is done later to avoid circular imports

logger = setup_logger(__name__)


class LocationToolsHandler:
    """
    Advanced location-based tools using AI for intent detection and place finding
    Handles finding nearest places and calculating routes using property coordinates
    """
    
    def __init__(self):
        self.api_base_url = "https://auth.propzing.com/functions/v1/whatsapp_agency_tools"
        self.auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjUyOTI3ODYsImV4cCI6MjA0MDg2ODc4Nn0.11GJjOlgPf4RocdFjMnWGJpBqFVk1wmbW27OmV0YAzs"
        self.openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Common place types for AI to recognize
        self.place_types = [
            'hospital', 'clinic', 'medical center', 'pharmacy', 'doctor',
            'school', 'university', 'college', 'kindergarten', 'academy',
            'mall', 'shopping center', 'supermarket', 'grocery', 'store',
            'restaurant', 'cafe', 'food', 'dining', 'bakery',
            'bank', 'atm', 'financial', 'metro', 'station', 'transport',
            'airport', 'beach', 'park', 'garden', 'gym', 'fitness',
            'hotel', 'accommodation', 'mosque', 'church', 'temple'
        ]
    
    def extract_coordinates_from_address(self, address_data: Dict[str, Any]) -> Optional[tuple]:
        """
        Extract latitude and longitude from address JSON field
        Returns tuple (lat, lng) or None if not found
        Supports both old format (lat/lng) and new format (latitude/longitude)
        """
        try:
            if not address_data:
                logger.info(f"🗺️ No address data provided for coordinate extraction")
                return None
                
            # Handle if address is a string (JSON string)
            if isinstance(address_data, str):
                logger.info(f"🗺️ Address data is string, attempting JSON parse")
                try:
                    address_data = json.loads(address_data)
                    logger.info(f"🗺️ Successfully parsed address JSON")
                except json.JSONDecodeError:
                    logger.warning(f"❌ Failed to parse address JSON: {address_data[:100]}...")
                    return None
            
            logger.info(f"🗺️ Address data keys: {list(address_data.keys()) if address_data else 'None'}")
            
            # Try new format first (latitude/longitude)
            latitude = address_data.get('latitude')
            longitude = address_data.get('longitude')
            
            logger.info(f"🗺️ New format - latitude: {latitude}, longitude: {longitude}")
            
            # If not found, try old format (lat/lng)
            if not (latitude and longitude):
                latitude = address_data.get('lat')
                longitude = address_data.get('lng')
                logger.info(f"🗺️ Old format - lat: {latitude}, lng: {longitude}")
            
            if latitude and longitude:
                try:
                    coords = (float(latitude), float(longitude))
                    logger.info(f"✅ Successfully extracted coordinates: {coords}")
                    return coords
                except (ValueError, TypeError) as e:
                    logger.warning(f"❌ Invalid coordinate values: lat={latitude}, lng={longitude}, error={e}")
                    return None
            else:
                logger.warning(f"❌ No valid coordinates found in address data")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error extracting coordinates from address: {str(e)}")
            return None
    
    def get_property_location_string(self, property_data: Dict[str, Any]) -> str:
        """
        Get location string for property (building_name + locality)
        """
        try:
            building_name = property_data.get('building_name', '')
            
            # Extract locality from address field
            address_data = property_data.get('address', {})
            if isinstance(address_data, str):
                try:
                    address_data = json.loads(address_data)
                except json.JSONDecodeError:
                    address_data = {}
            
            locality = address_data.get('locality', '') if address_data else ''
            
            # Combine building name and locality
            location_parts = []
            if building_name:
                location_parts.append(building_name)
            if locality:
                location_parts.append(locality)
                
            return ', '.join(location_parts) if location_parts else 'Unknown Location'
            
        except Exception as e:
            logger.error(f"Error getting property location string: {str(e)}")
            return 'Unknown Location'
    
    def _get_fallback_address_info(self, address_data: Dict[str, Any], property_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Get address information for fallback when coordinates are not available
        """
        try:
            # Parse address data if it's a string
            if isinstance(address_data, str):
                try:
                    address_data = json.loads(address_data)
                except json.JSONDecodeError:
                    address_data = {}
            
            if not address_data:
                address_data = {}
            
            # Extract address components
            building_name = property_data.get('building_name', '')
            locality = address_data.get('locality', '')
            city = address_data.get('city', 'Dubai')
            country = address_data.get('country', 'UAE')
            zipcode = address_data.get('zipcode', '')
            map_location = address_data.get('map_location', '')
            
            return {
                "building_name": building_name,
                "locality": locality,
                "city": city,
                "country": country,
                "zipcode": zipcode,
                "map_location": map_location,
                "full_address": self.get_property_location_string(property_data)
            }
            
        except Exception as e:
            logger.error(f"Error getting fallback address info: {str(e)}")
            return {
                "building_name": property_data.get('building_name', ''),
                "locality": '',
                "city": 'Dubai',
                "country": 'UAE',
                "zipcode": '',
                "map_location": '',
                "full_address": property_data.get('building_name', 'Unknown Location')
            }
    
    async def find_nearest_place_enhanced(self, property_data: Dict[str, Any], user_query: str, k: int = 3) -> Dict[str, Any]:
        """
        Find nearest places using AI-enhanced place type detection and multiple search attempts
        
        Args:
            property_data: Property data containing address with lat/lng
            user_query: User's original query or extracted place type
            k: Number of results to return (default 3)
        
        Returns:
            Dict containing nearestPlaces array or error message
        """
        try:
            # Use AI to extract and enhance the place type
            place_analysis = await self.extract_place_type_with_ai(user_query)
            primary_query = place_analysis.get('place_type', user_query)
            search_terms = place_analysis.get('search_terms', [primary_query])
            
            logger.info(f"🧠 Enhanced search - Primary query: '{primary_query}', Search terms: {search_terms}")
            
            # Try each search term until we find results
            for search_term in search_terms:
                logger.info(f"🔍 Trying search term: '{search_term}'")
                result = await self._find_nearest_place_basic(property_data, search_term, k)
                
                # If we got results, return them
                if not result.get('error') and result.get('nearestPlaces') and len(result['nearestPlaces']) > 0:
                    logger.info(f"✅ Found results with search term '{search_term}'")
                    result['search_analysis'] = place_analysis
                    result['successful_search_term'] = search_term
                    return result
                
                logger.info(f"⚠️ No results for search term '{search_term}', trying next...")
            
            # If no search term worked, return the last result with enhanced error info
            logger.warning(f"❌ No results found for any search terms: {search_terms}")
            if 'result' in locals():
                result['search_analysis'] = place_analysis
                result['attempted_search_terms'] = search_terms
                return result
            else:
                return {
                    "error": f"Could not find any {primary_query} nearby",
                    "property_name": property_data.get('building_name', 'Unknown Property'),
                    "search_analysis": place_analysis,
                    "attempted_search_terms": search_terms
                }
                
        except Exception as e:
            logger.error(f"❌ Error in enhanced place search: {str(e)}")
            # Fallback to basic search
            return await self._find_nearest_place_basic(property_data, user_query, k)
    
    async def _find_nearest_place_basic(self, property_data: Dict[str, Any], query: str, k: int = 3) -> Dict[str, Any]:
        """
        Basic nearest place finding (internal method)
        
        Args:
            property_data: Property data containing address with lat/lng
            query: What type of place to find (e.g., "hospital", "school", "restaurant")
            k: Number of results to return (default 3)
        
        Returns:
            Dict containing nearestPlaces array or error message
        """
        try:
            # Extract coordinates from property address
            address_data = property_data.get('address', {})
            logger.info(f"🗺️ Attempting to extract coordinates for property: {property_data.get('building_name', 'Unknown')}")
            logger.info(f"🗺️ Address data type: {type(address_data)}, content preview: {str(address_data)[:200] if address_data else 'Empty'}")
            
            coordinates = self.extract_coordinates_from_address(address_data)
            
            if not coordinates:
                logger.warning(f"❌ Could not extract coordinates for property {property_data.get('building_name', 'Unknown')}")
                # Fallback: provide property address information instead
                property_name = property_data.get('building_name', 'Unknown Property')
                address_info = self._get_fallback_address_info(address_data, property_data)
                return {
                    "error": f"Could not extract coordinates from property address",
                    "property_name": property_name,
                    "fallback_info": address_info,
                    "has_fallback": True,
                    "property_context": {
                        "property_name": property_name,
                        "property_id": property_data.get('id'),
                        "query": query
                    }
                }
            
            lat, lng = coordinates
            location_string = f"{lat},{lng}"
            
            # Prepare API request
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.auth_token
            }
            
            payload = {
                "action": "findNearestPlace",
                "query": query,
                "location": location_string,
                "k": k
            }
            
            logger.info(f"🔍 Finding nearest places for query: '{query}' near property: {property_data.get('building_name', 'Unknown')}")
            logger.info(f"📍 Using coordinates: {location_string}")
            logger.info(f"🔧 API URL: {self.api_base_url}")
            logger.info(f"🔧 Payload: {json.dumps(payload, indent=2)}")
            
            # Make API request
            response = requests.post(
                self.api_base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            logger.info(f"🔄 API response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"🔄 API response body: {json.dumps(result, indent=2) if result else 'Empty'}")
                
                # Add property context to result
                result['property_context'] = {
                    'property_name': property_data.get('building_name', 'Unknown Property'),
                    'property_id': property_data.get('id'),
                    'coordinates': coordinates,
                    'query': query
                }
                
                nearest_places_count = len(result.get('nearestPlaces', []))
                logger.info(f"✅ Found {nearest_places_count} nearest places")
                
                if nearest_places_count == 0:
                    logger.warning(f"⚠️ API returned 0 results for query '{query}' near coordinates {location_string}")
                
                return result
                
            else:
                logger.error(f"❌ API request failed with status {response.status_code}")
                logger.error(f"❌ API response text: {response.text}")
                logger.error(f"❌ API response headers: {response.headers}")
                return {
                    "error": f"Failed to find nearest places (API error: {response.status_code})",
                    "property_name": property_data.get('building_name', 'Unknown Property'),
                    "api_error_details": {
                        "status_code": response.status_code,
                        "response_text": response.text,
                        "url": self.api_base_url,
                        "payload": payload
                    }
                }
                
        except Exception as e:
            logger.error(f"Error finding nearest places: {str(e)}")
            return {
                "error": f"Error finding nearest places: {str(e)}",
                "property_name": property_data.get('building_name', 'Unknown Property')
            }
    
    # Legacy method for backward compatibility
    async def find_nearest_place(self, property_data: Dict[str, Any], query: str, k: int = 3) -> Dict[str, Any]:
        """Legacy method - redirects to enhanced version"""
        return await self.find_nearest_place_enhanced(property_data, query, k)
    
    async def calculate_route(self, property_data: Dict[str, Any], destination: str, is_origin: bool = True) -> Dict[str, Any]:
        """
        Calculate route from/to a property
        
        Args:
            property_data: Property data containing address and building name
            destination: Destination name (if is_origin=True) or origin name (if is_origin=False) 
            is_origin: Whether property is origin (True) or destination (False)
        
        Returns:
            Dict containing route information or error message
        """
        try:
            # Get property location string (building_name + locality)
            property_location = self.get_property_location_string(property_data)
            
            # Prepare API request
            headers = {
                'Content-Type': 'application/json',
                'Authorization': self.auth_token
            }
            
            if is_origin:
                # Property is origin, user provided destination
                origin = property_location
                destination_final = destination
            else:
                # Property is destination, user provided origin
                origin = destination
                destination_final = property_location
            
            payload = {
                "action": "calculateRoute",
                "origin": origin,
                "destination": destination_final
            }
            
            logger.info(f"🗺️ Calculating route from '{origin}' to '{destination_final}'")
            logger.info(f"🏠 Property: {property_data.get('building_name', 'Unknown')}")
            
            # Make API request
            response = requests.post(
                self.api_base_url,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Add property context to result
                result['property_context'] = {
                    'property_name': property_data.get('building_name', 'Unknown Property'),
                    'property_id': property_data.get('id'),
                    'property_location': property_location,
                    'is_origin': is_origin,
                    'other_location': destination if is_origin else destination
                }
                
                logger.info(f"✅ Route calculated successfully")
                return result
                
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {
                    "error": f"Failed to calculate route (API error: {response.status_code})",
                    "property_name": property_data.get('building_name', 'Unknown Property')
                }
                
        except Exception as e:
            logger.error(f"Error calculating route: {str(e)}")
            return {
                "error": f"Error calculating route: {str(e)}",
                "property_name": property_data.get('building_name', 'Unknown Property')
            }
    
    def format_nearest_places_response(self, result: Dict[str, Any]) -> str:
        """
        Format the nearest places API response into a user-friendly message
        """
        try:
            if 'error' in result:
                # Check if we have fallback address information
                if result.get('has_fallback') and result.get('fallback_info'):
                    return self._format_fallback_address_response(result)
                return f"❌ {result['error']}"
            
            nearest_places = result.get('nearestPlaces', [])
            property_context = result.get('property_context', {})
            property_name = property_context.get('property_name', 'the property')
            query = property_context.get('query', 'places')
            
            if not nearest_places:
                return f"❌ No {query} found near {property_name}."
            
            response_lines = [f"🔍 **Nearest {query} to {property_name}:**\n"]
            
            for i, place in enumerate(nearest_places, 1):
                name = place.get('name', 'Unknown Place')
                address = place.get('address', 'No address available')
                rating = place.get('rating')
                types = place.get('types', [])
                
                # Format rating
                rating_str = f" ⭐ {rating}" if rating else ""
                
                # Format types (take first 2 relevant ones)
                relevant_types = [t for t in types if t not in ['point_of_interest', 'establishment']][:2]
                types_str = f" ({', '.join(relevant_types)})" if relevant_types else ""
                
                response_lines.append(f"{i}. **{name}**{rating_str}{types_str}")
                response_lines.append(f"   📍 {address}\n")
            
            return '\n'.join(response_lines)
            
        except Exception as e:
            logger.error(f"Error formatting nearest places response: {str(e)}")
            return f"❌ Error formatting response: {str(e)}"
    
    def format_route_response(self, result: Dict[str, Any]) -> str:
        """
        Format the route calculation API response into a user-friendly message
        """
        try:
            if 'error' in result:
                return f"❌ {result['error']}"
            
            property_context = result.get('property_context', {})
            property_name = property_context.get('property_name', 'the property')
            is_origin = property_context.get('is_origin', True)
            other_location = property_context.get('other_location', 'destination')
            
            # Extract route information from API response
            # Note: The actual response structure depends on the API implementation
            # Adjust these fields based on the actual API response format
            
            if is_origin:
                direction_text = f"🗺️ **Route from {property_name} to {other_location}:**\n"
            else:
                direction_text = f"🗺️ **Route from {other_location} to {property_name}:**\n"
            
            response_lines = [direction_text]
            
            # Check if we have route data (structure depends on actual API response)
            if 'route' in result:
                route_data = result['route']
                if 'duration' in route_data:
                    response_lines.append(f"⏱️ Duration: {route_data['duration']}")
                if 'distance' in route_data:
                    response_lines.append(f"📏 Distance: {route_data['distance']}")
                if 'steps' in route_data:
                    response_lines.append("\n📋 **Directions:**")
                    for i, step in enumerate(route_data['steps'][:5], 1):  # Show first 5 steps
                        instruction = step.get('instruction', step.get('html_instructions', 'Continue'))
                        response_lines.append(f"{i}. {instruction}")
            else:
                # If no detailed route data, provide basic response
                response_lines.append("Route information calculated successfully.")
                response_lines.append("Please use your preferred navigation app for detailed directions.")
            
            return '\n'.join(response_lines)
            
        except Exception as e:
            logger.error(f"Error formatting route response: {str(e)}")
            return f"❌ Error formatting response: {str(e)}"
    
    def _format_fallback_address_response(self, result: Dict[str, Any]) -> str:
        """
        Format fallback response when coordinates are not available
        """
        try:
            property_name = result.get('property_name', 'the property')
            fallback_info = result.get('fallback_info', {})
            
            # Get the query from property context if available
            property_context = result.get('property_context', {})
            query = property_context.get('query', 'places')
            
            building_name = fallback_info.get('building_name', '')
            locality = fallback_info.get('locality', '')
            city = fallback_info.get('city', 'Dubai')
            country = fallback_info.get('country', 'UAE')
            map_location = fallback_info.get('map_location', '')
            
            # Build location text
            location_parts = []
            if building_name:
                location_parts.append(building_name)
            if locality:
                location_parts.append(locality)
            if city:
                location_parts.append(city)
            if country:
                location_parts.append(country)
            
            location_text = ', '.join(location_parts) if location_parts else 'Dubai, UAE'
            
            response = f"""😔 Sorry, I couldn't find nearby {query} for *{property_name}* right now.

📍 *{property_name}* is located at:
{location_text}

🗺️ **What I can help you with:**
• Send you the property location map
• Provide general area information about {city}
• Help you with property details and viewing appointments

💡 **For nearby amenities:**
Ask me to "share location" for an interactive map with nearby {query} and other places!"""

            # Add map link if available
            if map_location:
                response += f"\n\n🔗 **Google Maps:** {map_location}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting fallback response: {str(e)}")
            return f"❌ I encountered an issue providing location information for {result.get('property_name', 'the property')}. Please try asking to share location instead."


    async def extract_place_type_with_ai(self, message: str) -> Dict[str, Any]:
        """
        Use AI to extract the type of place user is looking for
        
        Args:
            message: User's message asking about nearby places
            
        Returns:
            Dict with place type and confidence
        """
        try:
            prompt = f"""
Analyze the user's message and extract what type of place they're looking for.

User message: "{message}"

Common place categories:
- Medical: hospital, clinic, pharmacy, doctor
- Education: school, university, college, academy  
- Shopping: mall, supermarket, grocery, store
- Food: restaurant, cafe, bakery, dining
- Finance: bank, ATM
- Transport: metro, station, airport
- Recreation: beach, park, gym
- Accommodation: hotel
- Religious: mosque, church, temple

Respond in JSON format:
{{
    "place_type": "specific place type (singular)",
    "category": "general category",
    "confidence": 0.0-1.0,
    "search_terms": ["term1", "term2"] // alternative terms to search
}}

Examples:
- "nearby schools" -> {{"place_type": "school", "category": "education", "confidence": 0.9, "search_terms": ["school", "academy"]}}
- "closest hospital" -> {{"place_type": "hospital", "category": "medical", "confidence": 0.9, "search_terms": ["hospital", "clinic"]}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting place types from user queries. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            result_str = response.choices[0].message.content.strip()
            result = json.loads(result_str)
            
            logger.info(f"🧠 AI Place Type Analysis: {result}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error in AI place type extraction: {str(e)}")
            # Fallback to simple keyword matching
            message_lower = message.lower()
            
            for place_type in self.place_types:
                if place_type in message_lower:
                    return {
                        "place_type": place_type,
                        "category": "general",
                        "confidence": 0.7,
                        "search_terms": [place_type]
                    }
            
            return {
                "place_type": "place",
                "category": "general", 
                "confidence": 0.5,
                "search_terms": ["place"]
            }


# Create global instance for easy import
location_tools_handler = LocationToolsHandler()