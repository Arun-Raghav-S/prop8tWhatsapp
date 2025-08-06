#!/usr/bin/env python3
"""
🚀 PERFORMANCE-OPTIMIZED PROPERTY SEARCH
Sub-second response times with intelligent caching and minimal API calls
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class FastPropertyResult:
    """Lightweight property result for fast responses"""
    id: str
    property_type: str
    sale_or_rent: str
    bedrooms: int
    bathrooms: int
    price: str
    location: str
    features: List[str]
    size: str

class PerformanceOptimizedSearch:
    """
    Ultra-fast property search with <1s response times
    """
    
    def __init__(self):
        # Initialize Supabase client with error handling
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if supabase_url and supabase_key:
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
            except Exception as e:
                print(f"Warning: Could not initialize Supabase client: {e}")
                self.supabase = None
        else:
            print("Warning: Supabase credentials not found. Search will be limited.")
            self.supabase = None
        
        # Pre-compiled response templates (NO AI GENERATION)
        self.templates = {
            'rental_properties': self._get_rental_template(),
            'sale_properties': self._get_sale_template(),
            'cheapest_properties': self._get_cheapest_template(),
            'luxury_properties': self._get_luxury_template()
        }
        
        # Response cache for ultra-fast repeated queries
        self.response_cache = {}
        
    def _get_rental_template(self) -> str:
        return """🎯 *Found {count} rental properties!*

{properties_list}

👉 Tell me about property 1
📅 Book visit for property 2
🔍 Show me cheaper options"""

    def _get_sale_template(self) -> str:
        return """🎯 *Found {count} properties for sale!*

{properties_list}

👉 Tell me about property 1
📅 Book visit for property 2
🔍 Show me cheaper options"""

    def _get_cheapest_template(self) -> str:
        return """🔥 *Most affordable properties found!*

{properties_list}

👉 Tell me about property 1
📅 Book visit for property 2
🔍 Show me different areas"""

    def _get_luxury_template(self) -> str:
        return """✨ *Luxury properties found!*

{properties_list}

👉 Tell me about property 1
📅 Book visit for property 2
🔍 Show me different areas"""

    async def fast_search(self, query: str, sale_or_rent: str = None, limit: int = 5) -> str:
        """
        Ultra-fast search with <1s response times
        """
        start_time = time.time()
        
        # 1. INSTANT CACHE CHECK (10ms)
        cache_key = f"{query}_{sale_or_rent}_{limit}"
        if cache_key in self.response_cache:
            cached_response = self.response_cache[cache_key]
            print(f"⚡ CACHE HIT: {(time.time() - start_time)*1000:.0f}ms")
            return cached_response

        # 2. SMART QUERY CLASSIFICATION (NO AI NEEDED)
        search_type = self._classify_query_fast(query)
        
        # 3. OPTIMIZED DATABASE QUERY (200-300ms)
        properties = await self._execute_fast_query(search_type, sale_or_rent, limit)
        
        # 4. TEMPLATE-BASED RESPONSE (50ms - NO AI!)
        response = self._generate_fast_response(properties, search_type)
        
        # 5. CACHE FOR FUTURE REQUESTS
        self.response_cache[cache_key] = response
        
        total_time = (time.time() - start_time) * 1000
        print(f"🚀 OPTIMIZED RESPONSE: {total_time:.0f}ms")
        
        return response

    def _classify_query_fast(self, query: str) -> str:
        """
        Lightning-fast query classification without AI
        """
        query_lower = query.lower()
        
        if 'cheap' in query_lower or 'affordable' in query_lower:
            return 'cheapest'
        elif 'luxury' in query_lower or 'premium' in query_lower or 'expensive' in query_lower:
            return 'luxury'
        elif 'rent' in query_lower:
            return 'rental'
        elif 'buy' in query_lower or 'sale' in query_lower:
            return 'sale'
        else:
            return 'general'

    async def _execute_fast_query_with_raw_data(self, search_type: str, sale_or_rent: str, limit: int) -> tuple[List[dict], List[FastPropertyResult]]:
        """
        Execute query and return both raw database data and processed objects
        Returns: (raw_db_data, processed_properties)
        """
        # Only select needed columns for fast transfer
        query = self.supabase.from_('property_vectorstore').select(
            'id, original_property_id, property_type, sale_or_rent, bedrooms, bathrooms, '
            'sale_price_aed, rent_price_aed, bua_sqft, address, building_name, '
            'study, maid_room, park_pool_view, landscaped_garden, covered_parking_spaces'
        )
        
        # Apply filters
        if sale_or_rent:
            query = query.eq('sale_or_rent', sale_or_rent)
            
        # Smart sorting based on search type
        if search_type == 'cheapest':
            if sale_or_rent == 'rent':
                query = query.order('rent_price_aed', desc=False)
            else:
                query = query.order('sale_price_aed', desc=False)
        elif search_type == 'luxury':
            if sale_or_rent == 'rent':
                query = query.order('rent_price_aed', desc=True)
            else:
                query = query.order('sale_price_aed', desc=True)
        else:
            query = query.order('created_at', desc=True)
            
        # Execute with limit
        response = query.limit(limit).execute()
        
        # Process raw data into FastPropertyResult objects
        processed_properties = []
        for prop in response.data:
            # Format price
            if prop.get('sale_price_aed'):
                price = f"AED {prop['sale_price_aed']:,}"
            elif prop.get('rent_price_aed'):
                price = f"AED {prop['rent_price_aed']:,}/year"
            else:
                price = "Price on request"
            
            # Extract location
            address = prop.get('address', {})
            if isinstance(address, str):
                location = "Dubai"  # Fallback
            else:
                location = address.get('locality') or address.get('city') or "Dubai"
            
            # Extract features
            features = []
            if prop.get('study'): features.append('Study')
            if prop.get('maid_room'): features.append('Maid room')
            if prop.get('park_pool_view'): features.append('Pool view')
            if prop.get('landscaped_garden'): features.append('Garden')
            if prop.get('covered_parking_spaces'): features.append(f"{prop['covered_parking_spaces']} parking")
            
            processed_properties.append(FastPropertyResult(
                id=prop['id'],
                property_type=prop['property_type'],
                sale_or_rent=prop['sale_or_rent'],
                bedrooms=prop['bedrooms'],
                bathrooms=prop['bathrooms'],
                price=price,
                location=location,
                features=features,
                size=f"{prop.get('bua_sqft', 0):,.0f} sqft"
            ))
            
        return response.data, processed_properties

    async def _execute_fast_query(self, search_type: str, sale_or_rent: str, limit: int) -> List[FastPropertyResult]:
        """
        Optimized database query with minimal data transfer
        """
        # Only select needed columns for fast transfer
        query = self.supabase.from_('property_vectorstore').select(
            'id, original_property_id, property_type, sale_or_rent, bedrooms, bathrooms, '
            'sale_price_aed, rent_price_aed, bua_sqft, address, building_name, '
            'study, maid_room, park_pool_view, landscaped_garden, covered_parking_spaces'
        )
        
        # Apply filters
        if sale_or_rent:
            query = query.eq('sale_or_rent', sale_or_rent)
            
        # Smart sorting based on search type
        if search_type == 'cheapest':
            if sale_or_rent == 'rent':
                query = query.order('rent_price_aed', desc=False)
            else:
                query = query.order('sale_price_aed', desc=False)
        elif search_type == 'luxury':
            if sale_or_rent == 'rent':
                query = query.order('rent_price_aed', desc=True)
            else:
                query = query.order('sale_price_aed', desc=True)
        else:
            query = query.order('created_at', desc=True)
            
        # Execute with limit
        response = query.limit(limit).execute()
        
        # Convert to lightweight objects
        properties = []
        for prop in response.data:
            # Format price
            if prop.get('sale_price_aed'):
                price = f"AED {prop['sale_price_aed']:,}"
            elif prop.get('rent_price_aed'):
                price = f"AED {prop['rent_price_aed']:,}/year"
            else:
                price = "Price on request"
            
            # Extract location
            address = prop.get('address', {})
            if isinstance(address, str):
                location = "Dubai"  # Fallback
            else:
                location = address.get('locality') or address.get('city') or "Dubai"
            
            # Extract features
            features = []
            if prop.get('study'): features.append('Study')
            if prop.get('maid_room'): features.append('Maid room')
            if prop.get('park_pool_view'): features.append('Pool view')
            if prop.get('landscaped_garden'): features.append('Garden')
            if prop.get('covered_parking_spaces'): features.append(f"{prop['covered_parking_spaces']} parking")
            
            properties.append(FastPropertyResult(
                id=prop['id'],
                property_type=prop['property_type'],
                sale_or_rent=prop['sale_or_rent'],
                bedrooms=prop['bedrooms'],
                bathrooms=prop['bathrooms'],
                price=price,
                location=location,
                features=features,
                size=f"{prop.get('bua_sqft', 0):,.0f} sqft"
            ))
            
        return properties

    def _generate_fast_response(self, properties: List[FastPropertyResult], search_type: str) -> str:
        """
        Template-based response generation (NO AI - INSTANT!)
        """
        if not properties:
            return "🔍 No properties found matching your criteria. Try adjusting your search!"
        
        # Format property list with correct WhatsApp formatting
        properties_list = ""
        for i, prop in enumerate(properties, 1):
            features_text = f" • {', '.join(prop.features)}" if prop.features else ""
            
            properties_list += f"""{i}. 🏠 *{prop.bedrooms}BR {prop.property_type}*
💰 {prop.price}
📍 {prop.location}
🚿 {prop.bathrooms} Bath • 📐 {prop.size}{features_text}

"""
        
        # Select appropriate template
        template_key = {
            'cheapest': 'cheapest_properties',
            'luxury': 'luxury_properties', 
            'rental': 'rental_properties',
            'sale': 'sale_properties'
        }.get(search_type, 'rental_properties')
        
        template = self.templates[template_key]
        
        return template.format(
            count=len(properties),
            properties_list=properties_list.strip()
        )

# Global instance for fast access
fast_search_engine = PerformanceOptimizedSearch()

async def ultra_fast_property_search(query: str, sale_or_rent: str = None, limit: int = 5) -> str:
    """
    Public interface for ultra-fast property search
    Target: <1s response time
    """
    return await fast_search_engine.fast_search(query, sale_or_rent, limit)

async def ultra_fast_property_search_with_context(query: str, sale_or_rent: str = None, limit: int = 5) -> tuple:
    """
    Ultra-fast search that also returns property objects for carousel logic
    Returns: (response_text, property_objects)
    """
    start_time = time.time()
    
    # Get raw database data and processed properties
    search_type = fast_search_engine._classify_query_fast(query)
    raw_db_data, properties = await fast_search_engine._execute_fast_query_with_raw_data(search_type, sale_or_rent, limit)
    
    # Generate response text
    response_text = fast_search_engine._generate_fast_response(properties, search_type)
    
    # Convert raw database data to property result objects for carousel compatibility
    # Import PropertyResult here to avoid circular imports
    from tools.property_search_advanced import PropertyResult
    
    property_objects = []
    for prop_data in raw_db_data:
        # Create proper PropertyResult object from raw database data
        prop_obj = PropertyResult(
            id=prop_data['id'],
            original_property_id=prop_data.get('original_property_id'),
            property_type=prop_data['property_type'],
            sale_or_rent=prop_data['sale_or_rent'],
            bedrooms=prop_data['bedrooms'],
            bathrooms=prop_data['bathrooms'],
            bua_sqft=float(prop_data.get('bua_sqft', 0)),
            sale_price_aed=prop_data.get('sale_price_aed'),
            rent_price_aed=prop_data.get('rent_price_aed'),
            address=prop_data.get('address'),
            building_name=prop_data.get('building_name'),
            study=prop_data.get('study'),
            maid_room=prop_data.get('maid_room'),
            park_pool_view=prop_data.get('park_pool_view'),
            landscaped_garden=prop_data.get('landscaped_garden'),
            covered_parking=prop_data.get('covered_parking_spaces')
        )
        property_objects.append(prop_obj)
    
    total_time = (time.time() - start_time) * 1000
    print(f"🚀 ULTRA-FAST WITH CONTEXT: {total_time:.0f}ms")
    
    return response_text, property_objects


if __name__ == "__main__":
    import asyncio
    
    async def test_performance():
        print("🚀 TESTING ULTRA-FAST SEARCH ENGINE")
        print("=" * 50)
        
        test_queries = [
            ("top 4 properties to rent", "rent"),
            ("cheapest properties", None),
            ("luxury properties to buy", "sale"),
            ("properties with pool", "rent")
        ]
        
        for query, sale_or_rent in test_queries:
            print(f"\n🧪 Testing: '{query}'")
            start = time.time()
            
            response = await ultra_fast_property_search(query, sale_or_rent, 4)
            
            duration = time.time() - start
            print(f"⏱️  Response time: {duration*1000:.0f}ms")
            print(f"📄 Response length: {len(response)} chars")
            
            if duration < 1.0:
                print("✅ SUB-SECOND PERFORMANCE!")
            else:
                print(f"❌ SLOW: {duration:.2f}s")
    
    asyncio.run(test_performance())