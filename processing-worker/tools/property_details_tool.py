"""
Property Details Tool
Fetches detailed property information for Know More button clicks
"""

import os
import json
import requests
from typing import Dict, Any, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PropertyDetailsTool:
    """Tool for fetching detailed property information"""
    
    def __init__(self):
        self.supabase_url = "https://auth.propzing.com"
        self.api_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRzYWtlenZkaXdtb29idWdjaGd1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjUyOTI3ODYsImV4cCI6MjA0MDg2ODc4Nn0.11GJjOlgPf4RocdFjMnWGJpBqFVk1wmbW27OmV0YAzs")
    
    async def get_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed property information by property ID
        
        Args:
            property_id: The property UUID
            
        Returns:
            Dict with property details or None if not found
        """
        try:
            logger.info(f"🔍 Fetching property details for ID: {property_id}")
            
            # Query the property_vectorstore table
            url = f"{self.supabase_url}/rest/v1/property_vectorstore"
            headers = {
                'apikey': self.api_key,
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Try querying by original_property_id first
            params = {
                'original_property_id': f'eq.{property_id}',
                'select': '*'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            # If no results found, try querying by id
            if response.status_code == 200:
                data = response.json()
                if not data or len(data) == 0:
                    # Try by id field instead
                    params = {
                        'id': f'eq.{property_id}',
                        'select': '*'
                    }
                    response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    property_data = data[0]  # Get first result
                    logger.info(f"✅ Property details found for {property_id}")
                    return property_data
                else:
                    logger.warning(f"❌ No property found with ID: {property_id}")
                    return None
            else:
                logger.error(f"❌ API error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching property details: {str(e)}")
            return None
    
    def format_property_details(self, property_data: Dict[str, Any]) -> str:
        """
        Format property details into a comprehensive WhatsApp-friendly message
        
        Args:
            property_data: Property information from database
            
        Returns:
            Formatted message string with all available details
        """
        try:
            # Extract key information
            property_type = property_data.get('property_type', 'Property')
            title = property_data.get('title', '')
            bedrooms = property_data.get('bedrooms', 0)
            bathrooms = property_data.get('bathrooms', 0)
            bua_sqft = property_data.get('bua_sqft', 0)
            plot_sqft = property_data.get('plot_sqft', 0)
            
            # Price information
            sale_price = property_data.get('sale_price_aed')
            rent_price = property_data.get('rent_price_aed')
            rent_period = property_data.get('rent_period', 'year')
            
            # Location information
            address = property_data.get('address', {})
            if isinstance(address, str):
                try:
                    address = json.loads(address)
                except:
                    address = {}
            
            locality = address.get('locality', 'Dubai')
            building_name = property_data.get('building_name', '')
            
            # Additional room features
            number_of_balconies = property_data.get('number_of_balconies', 0)
            study = property_data.get('study', False)
            maid_room = property_data.get('maid_room', False)
            laundry_room = property_data.get('laundry_room', False)
            additional_reception_area = property_data.get('additional_reception_area', False)
            covered_parking_spaces = property_data.get('covered_parking_spaces', 0)
            
            # Premium features
            park_pool_view = property_data.get('park_pool_view', False)
            upgraded_ground_flooring = property_data.get('upgraded_ground_flooring', False)
            landscaped_garden = property_data.get('landscaped_garden', False)
            
            # Features and amenities
            features = property_data.get('features', [])
            if isinstance(features, str):
                try:
                    features = json.loads(features)
                except:
                    features = []
            
            amenities = property_data.get('amenities', [])
            if isinstance(amenities, str):
                try:
                    amenities = json.loads(amenities)
                except:
                    amenities = []
            
            # Build the comprehensive response
            response_parts = []
            
            # Header with title if available
            if title:
                response_parts.append(f"🏠 *{title}*")
            elif bedrooms > 0:
                response_parts.append(f"🏠 *{bedrooms}BR {property_type} Details*")
            else:
                response_parts.append(f"🏠 *{property_type} Details*")
            
            # Basic room configuration
            info_parts = []
            if bedrooms > 0:
                info_parts.append(f"{bedrooms} bed")
            if bathrooms > 0:
                info_parts.append(f"{bathrooms} bath")
            if bua_sqft > 0:
                info_parts.append(f"{bua_sqft:,.0f} sqft")
            if plot_sqft > 0:
                info_parts.append(f"{plot_sqft:,.0f} plot")
            
            if info_parts:
                response_parts.append(f"📐 {' • '.join(info_parts)}")
            
            # Location
            location_text = f"📍 {locality}"
            if building_name:
                location_text += f", {building_name}"
            response_parts.append(location_text)
            
            # Price information
            if sale_price and sale_price > 0:
                response_parts.append(f"💰 *Sale Price:* AED {sale_price:,}")
            elif rent_price and rent_price > 0:
                response_parts.append(f"💰 *Rent:* AED {rent_price:,}/{rent_period}")
            
            # Additional rooms and spaces
            additional_rooms = []
            if study:
                additional_rooms.append("📚 Study room")
            if maid_room:
                additional_rooms.append("👥 Maid room")
            if laundry_room:
                additional_rooms.append("🧺 Laundry room")
            if additional_reception_area:
                additional_rooms.append("🛋️ Reception area")
            if number_of_balconies > 0:
                additional_rooms.append(f"🌅 {number_of_balconies} balcony/ies")
            if covered_parking_spaces > 0:
                additional_rooms.append(f"🚗 {covered_parking_spaces} parking space(s)")
            
            if additional_rooms:
                response_parts.append("🏡 *Additional Spaces:*")
                for room in additional_rooms:
                    response_parts.append(f"  • {room}")
            
            # Premium features
            premium_features = []
            if park_pool_view:
                premium_features.append("🌊 Park/Pool view")
            if upgraded_ground_flooring:
                premium_features.append("✨ Upgraded flooring")
            if landscaped_garden:
                premium_features.append("🌺 Landscaped garden")
            
            if premium_features:
                response_parts.append("⭐ *Premium Features:*")
                for feature in premium_features:
                    response_parts.append(f"  • {feature}")
            
            # Key Features from JSON
            if features and len(features) > 0:
                response_parts.append("🔑 *Key Features:*")
                for feature in features[:6]:  # Show top 6 features
                    if isinstance(feature, str) and feature.strip():
                        response_parts.append(f"  • {feature}")
                    elif isinstance(feature, dict) and feature.get('name'):
                        response_parts.append(f"  • {feature['name']}")
            
            # Amenities
            if amenities and len(amenities) > 0:
                response_parts.append("🏢 *Building Amenities:*")
                for amenity in amenities[:6]:  # Show top 6 amenities
                    if isinstance(amenity, str) and amenity.strip():
                        response_parts.append(f"  • {amenity}")
                    elif isinstance(amenity, dict) and amenity.get('name'):
                        response_parts.append(f"  • {amenity['name']}")
            
            # Call to action
            response_parts.append(f"\n📞 *Interested in viewing this property?*")
            response_parts.append(f"• Tap 'Schedule Visit' to book a viewing")
            response_parts.append(f"• Ask me about nearby amenities")
            response_parts.append(f"• Need more details? Just ask!")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"❌ Error formatting property details: {str(e)}")
            return "I found the property but couldn't format the details properly. Please try again or let me know what specific information you need."


# Global instance
property_details_tool = PropertyDetailsTool()
