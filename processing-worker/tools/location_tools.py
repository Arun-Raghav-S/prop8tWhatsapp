"""
Location-based Tools for WhatsApp Agent System
Tools for finding nearest places and calculating routes using property coordinates
"""

import os
import json
import requests
from typing import Dict, Any, Optional, List
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LocationToolsHandler:
    """
    Handler for location-based tools like finding nearest places and calculating routes
    """
    
    def __init__(self):
        self.api_base_url = "https://auth.propzing.com/functions/v1/whatsapp_agency_tools"
        self.auth_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjUyOTI3ODYsImV4cCI6MjA0MDg2ODc4Nn0.11GJjOlgPf4RocdFjMnWGJpBqFVk1wmbW27OmV0YAzs"
    
    def extract_coordinates_from_address(self, address_data: Dict[str, Any]) -> Optional[tuple]:
        """
        Extract latitude and longitude from address JSON field
        Returns tuple (lat, lng) or None if not found
        Supports both old format (lat/lng) and new format (latitude/longitude)
        """
        try:
            if not address_data:
                return None
                
            # Handle if address is a string (JSON string)
            if isinstance(address_data, str):
                try:
                    address_data = json.loads(address_data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse address JSON: {address_data}")
                    return None
            
            # Try new format first (latitude/longitude)
            latitude = address_data.get('latitude')
            longitude = address_data.get('longitude')
            
            # If not found, try old format (lat/lng)
            if not (latitude and longitude):
                latitude = address_data.get('lat')
                longitude = address_data.get('lng')
            
            if latitude and longitude:
                try:
                    return (float(latitude), float(longitude))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid coordinate values: lat={latitude}, lng={longitude}")
                    return None
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting coordinates from address: {str(e)}")
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
    
    async def find_nearest_place(self, property_data: Dict[str, Any], query: str, k: int = 3) -> Dict[str, Any]:
        """
        Find nearest places to a property using its coordinates
        
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
            coordinates = self.extract_coordinates_from_address(address_data)
            
            if not coordinates:
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
            
            # Make API request
            response = requests.post(
                self.api_base_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Add property context to result
                result['property_context'] = {
                    'property_name': property_data.get('building_name', 'Unknown Property'),
                    'property_id': property_data.get('id'),
                    'coordinates': coordinates,
                    'query': query
                }
                
                logger.info(f"✅ Found {len(result.get('nearestPlaces', []))} nearest places")
                return result
                
            else:
                logger.error(f"API request failed with status {response.status_code}: {response.text}")
                return {
                    "error": f"Failed to find nearest places (API error: {response.status_code})",
                    "property_name": property_data.get('building_name', 'Unknown Property')
                }
                
        except Exception as e:
            logger.error(f"Error finding nearest places: {str(e)}")
            return {
                "error": f"Error finding nearest places: {str(e)}",
                "property_name": property_data.get('building_name', 'Unknown Property')
            }
    
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
• Send you the property location brochure with interactive map
• Provide general area information about {city}
• Help you with property details and viewing appointments

💡 **For nearby amenities:**
Ask me to "send location brochure" for an interactive map with nearby {query} and other places!"""

            # Add map link if available
            if map_location:
                response += f"\n\n🔗 **Google Maps:** {map_location}"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting fallback response: {str(e)}")
            return f"❌ I encountered an issue providing location information for {result.get('property_name', 'the property')}. Please try asking for the location brochure instead."


# Create global instance for easy import
location_tools_handler = LocationToolsHandler()