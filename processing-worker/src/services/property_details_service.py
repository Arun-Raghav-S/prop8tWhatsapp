"""
Property Details Service
Fetches comprehensive property information from the vectorstore for detailed responses
"""

import os
import logging
from typing import Dict, Any, Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class PropertyDetailsService:
    """Service for fetching detailed property information from vectorstore"""
    
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv("NEXT_PUBLIC_SUPABASE_URL") or os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if supabase_url and supabase_key:
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
                logger.info("Property Details Service initialized with Supabase")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.supabase = None
        else:
            logger.error("Missing Supabase credentials for Property Details Service")
            self.supabase = None
    
    async def get_property_details(self, property_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch comprehensive property details by ID from vectorstore
        
        Args:
            property_id: UUID of the property in vectorstore
            
        Returns:
            Complete property details or None if not found
        """
        if not self.supabase:
            logger.error("Supabase client not available")
            return None
            
        try:
            logger.info(f"🔍 Fetching detailed property info for ID: {property_id}")
            
            # Fetch complete property record
            response = self.supabase.table('property_vectorstore').select(
                """
                id,
                original_property_id,
                title,
                property_type,
                sale_or_rent,
                building_name,
                bedrooms,
                bathrooms,
                number_of_balconies,
                bua_sqft,
                plot_sqft,
                study,
                maid_room,
                laundry_room,
                additional_reception_area,
                covered_parking_spaces,
                park_pool_view,
                upgraded_ground_flooring,
                landscaped_garden,
                sale_price_aed,
                rent_price_aed,
                rent_period,
                amenities,
                features,
                address,
                created_at,
                updated_at
                """
            ).eq('id', property_id).execute()
            
            if response.data and len(response.data) > 0:
                property_data = response.data[0]
                logger.info(f"✅ Retrieved detailed property data: {property_data.get('title', 'Untitled')}")
                return property_data
            else:
                logger.warning(f"❌ No property found with ID: {property_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching property details: {str(e)}")
            return None
    
    def format_detailed_property_response(self, property_data: Dict[str, Any], user_question: str = "") -> str:
        """
        Format comprehensive property details into a WhatsApp-friendly response
        
        Args:
            property_data: Complete property record from vectorstore
            user_question: Original user question for context
            
        Returns:
            Formatted detailed response
        """
        try:
            # Extract basic information
            title = property_data.get('title', 'Property')
            property_type = property_data.get('property_type', 'Property')
            bedrooms = property_data.get('bedrooms', 'N/A')
            bathrooms = property_data.get('bathrooms', 'N/A')
            bua_sqft = property_data.get('bua_sqft')
            building_name = property_data.get('building_name', '')
            
            # Extract pricing
            sale_price = property_data.get('sale_price_aed')
            rent_price = property_data.get('rent_price_aed')
            rent_period = property_data.get('rent_period', 'year')
            
            # Extract location from address JSON
            address = property_data.get('address', {})
            if isinstance(address, str):
                import json
                try:
                    address = json.loads(address)
                except:
                    address = {}
            
            locality = address.get('locality', '')
            city = address.get('city', 'Dubai')
            building_from_address = address.get('building_name', '')
            
            # Use building name from either field
            display_building = building_name or building_from_address
            
            # Start building response
            response_parts = []
            
            # Header with title and basic info
            if title and title != 'Property':
                response_parts.append(f"🏠 **{title}**\n")
            else:
                response_parts.append(f"🏠 **{bedrooms}BR {property_type}**\n")
            
            # Location
            location_parts = []
            if display_building:
                location_parts.append(display_building)
            if locality:
                location_parts.append(locality)
            if city:
                location_parts.append(city)
            
            if location_parts:
                response_parts.append(f"📍 {', '.join(location_parts)}\n")
            
            # Pricing
            if sale_price:
                response_parts.append(f"💰 **AED {sale_price:,}** (Sale)\n")
            elif rent_price:
                response_parts.append(f"💰 **AED {rent_price:,}/{rent_period}** (Rent)\n")
            
            # Size and layout
            response_parts.append("\n**📐 Size & Layout:**\n")
            if bua_sqft:
                response_parts.append(f"• Built-up Area: {bua_sqft:,} sqft\n")
            
            plot_sqft = property_data.get('plot_sqft')
            if plot_sqft:
                response_parts.append(f"• Plot Area: {plot_sqft:,} sqft\n")
            
            response_parts.append(f"• Bedrooms: {bedrooms}\n")
            response_parts.append(f"• Bathrooms: {bathrooms}\n")
            
            balconies = property_data.get('number_of_balconies')
            if balconies:
                response_parts.append(f"• Balconies: {balconies}\n")
            
            # Features and amenities
            features_list = []
            
            # Boolean features
            if property_data.get('study'):
                features_list.append("Study Room")
            if property_data.get('maid_room'):
                features_list.append("Maid Room")
            if property_data.get('laundry_room'):
                features_list.append("Laundry Room")
            if property_data.get('additional_reception_area'):
                features_list.append("Additional Reception")
            if property_data.get('park_pool_view'):
                features_list.append("Park/Pool View")
            if property_data.get('upgraded_ground_flooring'):
                features_list.append("Upgraded Flooring")
            if property_data.get('landscaped_garden'):
                features_list.append("Landscaped Garden")
            
            # Parking
            parking = property_data.get('covered_parking_spaces')
            if parking:
                features_list.append(f"{parking} Parking Space{'s' if parking > 1 else ''}")
            
            if features_list:
                response_parts.append(f"\n**✨ Features:**\n")
                for feature in features_list:
                    response_parts.append(f"• {feature}\n")
            
            # Additional amenities from JSONB
            amenities_json = property_data.get('amenities', {})
            if isinstance(amenities_json, str):
                try:
                    import json
                    amenities_json = json.loads(amenities_json)
                except:
                    amenities_json = {}
            
            if amenities_json and len(amenities_json) > 0:
                response_parts.append(f"\n**🏢 Building Amenities:**\n")
                for amenity, value in amenities_json.items():
                    if value:  # Only show amenities that are true/present
                        amenity_display = amenity.replace('_', ' ').title()
                        response_parts.append(f"• {amenity_display}\n")
            
            # Additional features from JSONB
            features_json = property_data.get('features', {})
            if isinstance(features_json, str):
                try:
                    import json
                    features_json = json.loads(features_json)
                except:
                    features_json = {}
            
            if features_json and len(features_json) > 0:
                response_parts.append(f"\n**🎯 Additional Features:**\n")
                for feature, value in features_json.items():
                    if value:  # Only show features that are true/present
                        feature_display = feature.replace('_', ' ').title()
                        response_parts.append(f"• {feature_display}\n")
            
            # Call to action
            response_parts.append(f"\n📅 **Interested?** I can help you schedule a visit!")
            response_parts.append(f"\n🗺️ Want to know about nearby amenities or directions?")
            
            return "".join(response_parts)
            
        except Exception as e:
            logger.error(f"Error formatting property response: {str(e)}")
            return f"I have detailed information about this property, but encountered an error formatting it. The property ID is {property_data.get('id', 'unknown')}."


# Global instance
property_details_service = PropertyDetailsService()
