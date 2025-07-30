"""
Simple Property Search Implementation
Quick search functionality for straightforward property queries
"""

import os
import json
import time
import re
from typing import Dict, Any, List, Optional, Union
from openai import OpenAI
from supabase import create_client, Client

from utils.logger import setup_logger

logger = setup_logger(__name__)


class SimplePropertySearchAgent:
    """
    Simplified property search agent for quick queries
    """
    
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
            print("Warning: Supabase credentials not found. Property search will be limited.")
            self.supabase = None
    
    def process_simple_query(self, query: str) -> Dict[str, Any]:
        """
        Process simple property search queries without advanced features
        """
        start_time = time.time()
        
        # Extract basic parameters
        params = self.extract_simple_params(query)
        
        # Execute search
        results = self.execute_simple_search(params)
        
        # Generate response
        response = self.generate_simple_response(results, query)
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            'answer': response,
            'results': results,
            'processing_time_ms': processing_time,
            'method': 'simple_search'
        }
    
    def extract_simple_params(self, query: str) -> Dict[str, Any]:
        """
        Extract basic search parameters using regex patterns
        """
        params = {}
        query_lower = query.lower()
        
        # Property type
        if 'apartment' in query_lower or 'flat' in query_lower:
            params['property_type'] = 'Apartment'
        elif 'villa' in query_lower:
            params['property_type'] = 'Villa'
        elif 'penthouse' in query_lower:
            params['property_type'] = 'Penthouse'
        
        # Bedrooms
        bedroom_match = re.search(r'(\d+)\s*(?:bed|br|bedroom)', query_lower)
        if bedroom_match:
            params['bedrooms'] = int(bedroom_match.group(1))
        
        # Location
        if 'marina' in query_lower:
            params['locality'] = 'Dubai Marina'
        elif 'downtown' in query_lower:
            params['locality'] = 'Downtown Dubai'
        elif 'jbr' in query_lower:
            params['locality'] = 'JBR'
        
        # Sale or rent
        if 'rent' in query_lower or 'rental' in query_lower:
            params['sale_or_rent'] = 'rent'
        elif 'buy' in query_lower or 'sale' in query_lower or 'purchase' in query_lower:
            params['sale_or_rent'] = 'sale'
        
        return params
    
    def execute_simple_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute simple search against Supabase
        """
        try:
            query = self.supabase.from_('property_vectorstore').select(
                'id, property_type, bedrooms, bathrooms, bua_sqft, '
                'sale_price_aed, rent_price_aed, sale_or_rent, address, building_name'
            )
            
            # Apply filters
            if params.get('property_type'):
                query = query.eq('property_type', params['property_type'])
            
            if params.get('bedrooms'):
                query = query.eq('bedrooms', params['bedrooms'])
            
            if params.get('sale_or_rent'):
                query = query.eq('sale_or_rent', params['sale_or_rent'])
            
            if params.get('locality'):
                query = query.ilike('address->locality', f"%{params['locality']}%")
            
            # Execute query
            response = query.limit(10).execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Simple search failed: {str(e)}")
            return []
    
    def generate_simple_response(self, results: List[Dict[str, Any]], query: str) -> str:
        """
        Generate simple text response
        """
        if not results:
            return "I couldn't find any properties matching your criteria. Try adjusting your search parameters."
        
        response = f"Found {len(results)} properties:\n\n"
        
        for i, prop in enumerate(results[:5], 1):
            price = "Price on request"
            if prop.get('sale_price_aed'):
                price = f"AED {prop['sale_price_aed']:,}"
            elif prop.get('rent_price_aed'):
                price = f"AED {prop['rent_price_aed']:,}/year"
            
            location = "Location not specified"
            if prop.get('address'):
                addr = prop['address']
                if addr.get('locality'):
                    location = addr['locality']
                elif addr.get('city'):
                    location = addr['city']
            
            response += f"{i}. {prop['property_type']} - {prop['bedrooms']}BR/{prop['bathrooms']}BA\n"
            response += f"   📍 {location}\n"
            response += f"   💰 {price}\n"
            response += f"   📐 {prop['bua_sqft']} sqft\n\n"
        
        if len(results) > 5:
            response += f"... and {len(results) - 5} more properties.\n"
        
        return response
    
    def calculate_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate basic statistics from results
        """
        if not results:
            return {}
        
        stats = {
            'count': len(results),
            'property_types': {},
            'avg_bedrooms': 0,
            'avg_size': 0
        }
        
        # Count property types
        for prop in results:
            prop_type = prop.get('property_type', 'Unknown')
            stats['property_types'][prop_type] = stats['property_types'].get(prop_type, 0) + 1
        
        # Calculate averages
        total_bedrooms = sum(prop.get('bedrooms', 0) for prop in results)
        total_size = sum(prop.get('bua_sqft', 0) for prop in results if prop.get('bua_sqft'))
        
        stats['avg_bedrooms'] = total_bedrooms / len(results) if results else 0
        stats['avg_size'] = total_size / len(results) if results else 0
        
        # Price statistics
        sale_prices = [prop['sale_price_aed'] for prop in results if prop.get('sale_price_aed')]
        rent_prices = [prop['rent_price_aed'] for prop in results if prop.get('rent_price_aed')]
        
        if sale_prices:
            stats['avg_sale_price'] = sum(sale_prices) / len(sale_prices)
            stats['min_sale_price'] = min(sale_prices)
            stats['max_sale_price'] = max(sale_prices)
        
        if rent_prices:
            stats['avg_rent_price'] = sum(rent_prices) / len(rent_prices)
            stats['min_rent_price'] = min(rent_prices)
            stats['max_rent_price'] = max(rent_prices)
        
        return stats 