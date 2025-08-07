"""
WhatsApp Response Formatter
Optimized formatting for mobile WhatsApp with consistent tone and style
"""

from typing import Dict, List, Optional, Any
import re

class WhatsAppFormatter:
    """
    WhatsApp-optimized response formatter with casual-friendly tone
    Mobile-first design with proper formatting
    """
    
    def __init__(self):
        # WhatsApp formatting symbols
        self.bold = lambda text: f"*{text}*"
        self.italic = lambda text: f"_{text}_"
        self.code = lambda text: f"`{text}`"
        
        # Emoji library for consistency
        self.emojis = {
            'property': '🏠',
            'apartment': '🏢', 
            'villa': '🏡',
            'penthouse': '🏙️',
            'townhouse': '🏘️',
            'price': '💰',
            'location': '📍',
            'size': '📐',
            'bedrooms': '🛏️',
            'bathrooms': '🚿',
            'features': '✨',
            'search': '🔍',
            'found': '🎯',
            'calendar': '📅',
            'phone': '📱',
            'checkmark': '✅',
            'fire': '🔥',
            'sparkles': '💫',
            'arrow': '👉',
            'info': 'ℹ️'
        }
    
    def format_price(self, price: Optional[int], sale_or_rent: str = 'sale') -> str:
        """Format price for WhatsApp display"""
        if not price or price == 0:
            return "Price on request"
        
        if price >= 1_000_000:
            formatted = f"{price / 1_000_000:.1f}M"
        elif price >= 1_000:
            formatted = f"{price / 1_000:.0f}K"
        else:
            formatted = f"{price:,}"
        
        suffix = "/year" if sale_or_rent == 'rent' else ""
        return f"AED {formatted}{suffix}"
    
    def format_property_card(self, property_data: Dict, index: Optional[int] = None) -> str:
        """Format a single property as a WhatsApp card"""
        
        # Price formatting
        sale_price = property_data.get('sale_price_aed', 0)
        rent_price = property_data.get('rent_price_aed', 0)
        
        if sale_price:
            price_text = self.format_price(sale_price, 'sale')
        elif rent_price:
            price_text = self.format_price(rent_price, 'rent')
        else:
            price_text = "Price on request"
        
        # Property type emoji
        prop_type = property_data.get('property_type', 'Property').lower()
        type_emoji = self.emojis.get(prop_type, self.emojis['property'])
        
        # Location
        address = property_data.get('address', {})
        if isinstance(address, dict):
            location = address.get('locality') or address.get('city') or 'Dubai'
        else:
            location = 'Dubai'
        
        # Index prefix
        index_prefix = f"{index}. " if index else ""
        
        # Property title - using correct WhatsApp formatting
        bedrooms = property_data.get('bedrooms', 'N/A')
        prop_type_display = property_data.get('property_type', 'Property')
        title = f"{index_prefix}{type_emoji} *{bedrooms}BR {prop_type_display}*"
        
        # Details
        bathrooms = property_data.get('bathrooms', 'N/A')
        size = property_data.get('bua_sqft', 'N/A')
        
        details = [
            f"{self.emojis['price']} {price_text}",
            f"{self.emojis['location']} {location}"
        ]
        
        # Add size and bathrooms on same line
        size_bath = []
        if bathrooms and bathrooms != 'N/A':
            size_bath.append(f"{self.emojis['bathrooms']} {bathrooms} Bath")
        if size and size != 'N/A':
            size_bath.append(f"{self.emojis['size']} {size:,} sqft")
        
        if size_bath:
            details.append(" • ".join(size_bath))
        
        return f"{title}\n" + "\n".join(details)
    
    def format_property_list(self, properties: List[Dict], query: str, total_count: int) -> str:
        """Format multiple properties for WhatsApp"""
        
        if not properties:
            return self.format_no_results(query)
        
        # Header
        count_text = f"{len(properties)}" if total_count <= len(properties) else f"{len(properties)} of {total_count}"
        header = f"{self.emojis['found']} *Found {count_text} properties!*"
        
        # Property cards
        property_cards = []
        for i, prop in enumerate(properties, 1):
            card = self.format_property_card(prop, i)
            property_cards.append(card)
        
        # Join with spacing
        properties_text = "\n\n".join(property_cards)
        
        # Footer with actions
        footer_actions = [
            f"{self.emojis['arrow']} Tell me about property 1",
            f"{self.emojis['calendar']} Book visit for property 2", 
            f"{self.emojis['search']} Show me cheaper options"
        ]
        
        footer = f"\n\n*Quick actions:*\n" + "\n".join(footer_actions)
        
        return f"{header}\n\n{properties_text}{footer}"
    
    def format_single_property(self, property_data: Dict, context: str = "") -> str:
        """Format single property with more details"""
        
        # Property type emoji
        prop_type = property_data.get('property_type', 'Property').lower()
        type_emoji = self.emojis.get(prop_type, self.emojis['property'])
        
        # Building name or title
        building = property_data.get('building_name', 'Premium Property')
        bedrooms = property_data.get('bedrooms', 'N/A')
        title = f"{type_emoji} {self.bold(f'{bedrooms}BR in {building}')}"
        
        # Price
        sale_price = property_data.get('sale_price_aed', 0)
        rent_price = property_data.get('rent_price_aed', 0)
        
        if sale_price:
            price_text = self.format_price(sale_price, 'sale')
        elif rent_price:
            price_text = self.format_price(rent_price, 'rent')
        else:
            price_text = "Price on request"
        
        # Basic details
        bathrooms = property_data.get('bathrooms', 'N/A')
        size = property_data.get('bua_sqft', 'N/A')
        address = property_data.get('address', {})
        location = address.get('locality') or address.get('city') or 'Dubai'
        
        details = [
            f"{self.emojis['price']} {self.bold(price_text)}",
            f"{self.emojis['location']} {location}",
            f"{self.emojis['bathrooms']} {bathrooms} Bath"
        ]
        
        if size and size != 'N/A':
            details.append(f"{self.emojis['size']} {size:,} sqft")
        
        # Features
        features = []
        if property_data.get('study'):
            features.append('Study room')
        if property_data.get('maid_room'):
            features.append('Maid room')
        if property_data.get('landscaped_garden'):
            features.append('Garden')
        if property_data.get('park_pool_view'):
            features.append('Pool view')
        
        features_text = ""
        if features:
            features_text = f"\n{self.emojis['features']} {', '.join(features)}"
        
        # Actions
        actions = [
            f"{self.emojis['calendar']} Book a visit",
            f"{self.emojis['info']} Tell me about location",
            f"{self.emojis['search']} Show similar properties"
        ]
        
        actions_text = f"\n\n{self.bold('Next steps:')}\n" + "\n".join(actions)
        
        return f"{title}\n\n" + "\n".join(details) + features_text + actions_text
    
    def format_statistical_result(self, query_type: str, property_data: Dict, execution_time: float = 0) -> str:
        """Format statistical query results"""
        
        # Determine transaction type
        sale_price = property_data.get('sale_price_aed', 0)
        rent_price = property_data.get('rent_price_aed', 0)
        
        if rent_price and not sale_price:
            price_text = self.format_price(rent_price, 'rent')
            transaction = "to rent"
        else:
            price_text = self.format_price(sale_price, 'sale')
            transaction = "for sale"
        
        # Headers by query type
        headers = {
            'cheapest': f"{self.emojis['fire']} {self.bold('Cheapest property ' + transaction)}",
            'most_expensive': f"{self.emojis['sparkles']} {self.bold('Most expensive property ' + transaction)}",
            'largest': f"{self.emojis['property']} {self.bold('Largest property ' + transaction)}",
            'smallest': f"{self.emojis['property']} {self.bold('Smallest property ' + transaction)}"
        }
        
        header = headers.get(query_type, f"{self.emojis['checkmark']} {self.bold('Property found')}")
        
        # Property details
        prop_type = property_data.get('property_type', 'Property')
        bedrooms = property_data.get('bedrooms', 'N/A')
        size = property_data.get('bua_sqft', 0)
        address = property_data.get('address', {})
        location = address.get('locality') or address.get('city') or 'Dubai'
        
        details = [
            f"{self.emojis['price']} {self.bold(price_text)}",
            f"{self.emojis['property']} {bedrooms}BR {prop_type}",
            f"{self.emojis['location']} {location}"
        ]
        
        if size and size > 0:
            details.append(f"{self.emojis['size']} {size:,} sqft")
        
        # Quick actions
        actions = [
            f"{self.emojis['calendar']} Book visit",
            f"{self.emojis['search']} Show similar properties"
        ]
        
        actions_text = f"\n\n" + " • ".join(actions)
        
        return f"{header}\n\n" + "\n".join(details) + actions_text
    
    def format_no_results(self, query: str) -> str:
        """Format no results response"""
        
        suggestions = [
            "Try different areas (Marina, Downtown, JBR)",
            "Adjust your budget range", 
            "Consider different property types",
            "Check nearby neighborhoods"
        ]
        
        return f"{self.emojis['search']} {self.bold('No properties found')}\n\n" \
               f"Let me help you find something!\n\n" \
               f"{self.bold('Try:')}\n" + "\n".join([f"• {s}" for s in suggestions]) + \
               f"\n\nJust tell me what you're looking for! {self.emojis['property']}"
    
    def format_greeting(self, user_name: Optional[str] = None) -> str:
        """Format greeting message with optional personalization"""
        
        # Personalized greeting if we know the user's name
        if user_name and user_name.strip():
            greeting = f"Hey {user_name}! {self.emojis['property']} I'm your Dubai property assistant."
        else:
            greeting = f"Hey there! {self.emojis['property']} I'm your Dubai property assistant."
        
        return f"{greeting}\n\n" \
               f"{self.bold('I can help you:')}\n" \
               f"• Find apartments, villas, penthouses\n" \
               f"• Get market prices and stats\n" \
               f"• Schedule property visits\n" \
               f"• Compare different areas\n\n" \
               f"What are you looking for? {self.emojis['search']}"
    
    def format_help(self) -> str:
        """Format help message"""
        
        examples = [
            "\"Show me 2BR apartments in Marina\"",
            "\"What's the cheapest villa?\"",
            "\"Find penthouses under 3M\"",
            "\"Book visit for the first one\""
        ]
        
        header = f"{self.emojis['info']} {self.bold('Here' + chr(39) + 's what I can do:')}\n\n"
        body = f"{self.bold('Try asking:')}\n" + "\n".join([f"• {ex}" for ex in examples])
        footer = f"\n\nJust type naturally - I'll understand! {self.emojis['sparkles']}"
        return header + body + footer
    
    def format_error(self, context: str = "") -> str:
        """Format error message"""
        
        return f"Oops! Something went wrong {self.emojis['info']}\n\n" \
               f"Please try again or ask me something else.\n\n" \
               f"Need help? Just type \"help\" {self.emojis['property']}"
    
    def format_followup_booking(self, property_ref: str, booking_ref: str) -> str:
        """Format booking confirmation"""
        
        return f"{self.emojis['checkmark']} {self.bold('Visit scheduled!')}\n\n" \
               f"{self.emojis['calendar']} Booking ref: {self.bold(booking_ref)}\n\n" \
               f"Our team will call you within 2 hours to confirm details.\n\n" \
               f"Questions? Just message me! {self.emojis['phone']}"
    
    def format_location_info(self, property_data: Dict) -> str:
        """Format location information"""
        
        address = property_data.get('address', {})
        building = property_data.get('building_name', 'Property')
        locality = address.get('locality', 'Dubai')
        
        # Mock nearby places (in real implementation, fetch from API)
        nearby_places = {
            'marina': ['Dubai Mall', 'JBR Beach', 'Marina Walk'],
            'downtown': ['Burj Khalifa', 'Dubai Mall', 'DIFC'],
            'jbr': ['The Beach', 'Marina Walk', 'JBR Beach']
        }
        
        locality_lower = locality.lower()
        nearby = []
        for area, places in nearby_places.items():
            if area in locality_lower:
                nearby = places[:3]
                break
        
        nearby_text = ""
        if nearby:
            nearby_text = f"\n\n{self.bold('Nearby:')}\n" + "\n".join([f"• {place}" for place in nearby])
        
        return f"{self.emojis['location']} {self.bold(f'{building}')}\n" \
               f"{locality}{nearby_text}\n\n" \
               f"Want to visit? Just say \"book visit\" {self.emojis['calendar']}"
    
    def should_use_carousel(self, properties: List[Dict], query: str) -> bool:
        """Determine if should send carousel instead of text"""
        
        # Use carousel for 7+ properties with general queries
        if len(properties) < 7:
            return False
        
        general_keywords = [
            'properties', 'show me', 'find', 'search', 'available',
            'cheapest', 'all', 'list', 'what do you have', 'looking for',
            'apartments', 'villas', 'to rent', 'for rent'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in general_keywords)
    
    def format_carousel_sent_response(self, property_count: int) -> str:
        """Format simple response when carousel is sent"""
        return f"{self.emojis['property']} Here are {property_count} properties that match your search! I've sent you property cards with all the details."

# Global formatter instance
whatsapp_formatter = WhatsAppFormatter()