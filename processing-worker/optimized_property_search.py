"""
Optimized Property Search System
Efficient, cached property search that integrates with unified conversation engine
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, List, Optional
from supabase import create_client, Client

from utils.logger import setup_logger

logger = setup_logger(__name__)


class PropertySearchCache:
    """Simple in-memory cache for property search results"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minute cache
        self.cache = {}
        self.ttl = ttl_seconds
    
    def _generate_key(self, params: Dict[str, Any]) -> str:
        """Generate cache key from search parameters"""
        # Sort params for consistent key generation
        sorted_params = json.dumps(params, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()
    
    def get(self, params: Dict[str, Any]) -> Optional[List[Dict]]:
        """Get cached results if available and not expired"""
        key = self._generate_key(params)
        
        if key in self.cache:
            cached_data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.info(f"🚀 Cache HIT for search params")
                return cached_data
            else:
                # Expired, remove from cache
                del self.cache[key]
        
        return None
    
    def set(self, params: Dict[str, Any], results: List[Dict]):
        """Cache search results"""
        key = self._generate_key(params)
        self.cache[key] = (results, time.time())
        logger.info(f"💾 Cached {len(results)} search results")
    
    def clear(self):
        """Clear all cached results"""
        self.cache.clear()


class OptimizedPropertySearch:
    """
    Optimized property search that chooses the right query complexity based on requirements
    """
    
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if supabase_url and supabase_key:
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
                logger.info("✅ Supabase client initialized for optimized search")
            except Exception as e:
                logger.error(f"❌ Supabase initialization failed: {e}")
                self.supabase = None
        else:
            logger.error("❌ Missing Supabase credentials")
            self.supabase = None
        
        # Initialize cache
        self.cache = PropertySearchCache()
        
        # Query complexity thresholds
        self.simple_query_limit = 20  # Use simple query for <= 20 results
        self.complex_query_limit = 100  # Use complex hybrid search for more
        
    async def search_properties(self, search_params: Dict[str, Any], user_message: str = "") -> Dict[str, Any]:
        """
        Main search method that chooses optimal query strategy
        """
        start_time = time.time()
        
        try:
            # Check cache first
            cached_results = self.cache.get(search_params)
            if cached_results:
                return {
                    "properties": cached_results,
                    "total_count": len(cached_results),
                    "execution_time_ms": (time.time() - start_time) * 1000,
                    "cache_hit": True,
                    "query_type": "cached"
                }
            
            # Determine query strategy based on complexity
            query_strategy = self._determine_query_strategy(search_params, user_message)
            
            if query_strategy == "simple":
                results = await self._execute_simple_query(search_params)
            elif query_strategy == "hybrid":
                results = await self._execute_hybrid_query(search_params, user_message)
            else:
                # Fallback to simple query
                results = await self._execute_simple_query(search_params)
            
            # Cache results
            if results:
                self.cache.set(search_params, results)
            
            execution_time = (time.time() - start_time) * 1000
            
            logger.info(f"🔍 Search completed: {len(results)} results in {execution_time:.0f}ms using {query_strategy} query")
            
            return {
                "properties": results,
                "total_count": len(results),
                "execution_time_ms": execution_time,
                "cache_hit": False,
                "query_type": query_strategy
            }
            
        except Exception as e:
            logger.error(f"❌ Property search failed: {str(e)}")
            return {
                "properties": [],
                "total_count": 0,
                "execution_time_ms": (time.time() - start_time) * 1000,
                "cache_hit": False,
                "query_type": "error",
                "error": str(e)
            }
    
    def _determine_query_strategy(self, search_params: Dict[str, Any], user_message: str) -> str:
        """
        Determine whether to use simple or complex hybrid search
        """
        # Count number of filters
        filter_count = len([v for v in search_params.values() if v is not None])
        
        # Check if user message indicates complex requirements
        complex_indicators = [
            'cheapest', 'most expensive', 'largest', 'smallest',
            'best', 'luxury', 'affordable', 'garden', 'view',
            'parking', 'study', 'maid room'
        ]
        
        has_complex_requirements = any(indicator in user_message.lower() for indicator in complex_indicators)
        
        # Simple strategy for basic filters
        if filter_count <= 3 and not has_complex_requirements:
            return "simple"
        
        # Hybrid strategy for complex requirements
        return "hybrid"
    
    async def _execute_simple_query(self, search_params: Dict[str, Any]) -> List[Dict]:
        """
        Execute simple query using hybrid_property_search function for consistency
        """
        if not self.supabase:
            return []
        
        try:
            # Convert search_params to proper RPC parameters
            rpc_params = {
                'user_query_text': '',  # Empty for filter-only search
                'match_count': self.simple_query_limit,
                'full_text_weight': 0.0,  # No text search
                'semantic_weight': 0.0    # No semantic search
            }
            
            # Map parameters correctly for hybrid function
            if search_params.get('property_type'):
                rpc_params['p_property_type'] = search_params['property_type']
            
            if search_params.get('sale_or_rent'):
                rpc_params['p_sale_or_rent'] = search_params['sale_or_rent']
            
            if search_params.get('bedrooms') is not None:
                rpc_params['p_bedrooms'] = search_params['bedrooms']
            
            # Fix locality filtering - use p_locality parameter
            if search_params.get('locality'):
                rpc_params['p_locality'] = search_params['locality']
            
            # Price parameters
            if search_params.get('min_rent_price_aed'):
                rpc_params['p_min_rent_price_aed'] = search_params['min_rent_price_aed']
            if search_params.get('max_rent_price_aed'):
                rpc_params['p_max_rent_price_aed'] = search_params['max_rent_price_aed']
            if search_params.get('min_sale_price_aed'):
                rpc_params['p_min_sale_price_aed'] = search_params['min_sale_price_aed']
            if search_params.get('max_sale_price_aed'):
                rpc_params['p_max_sale_price_aed'] = search_params['max_sale_price_aed']
            
            logger.info(f"🔍 [SIMPLE_SEARCH] Using hybrid function with params: {rpc_params}")
            
            # Execute using hybrid search function for consistency
            response = self.supabase.rpc('hybrid_property_search', rpc_params).execute()
            
            if response.data:
                logger.info(f"✅ [SIMPLE_SEARCH] Found {len(response.data)} results")
                return response.data
            else:
                logger.warning(f"⚠️ [SIMPLE_SEARCH] No results found")
                return []
                
        except Exception as e:
            logger.error(f"❌ Simple query failed: {str(e)}")
            return []
    
    async def _execute_hybrid_query(self, search_params: Dict[str, Any], user_message: str) -> List[Dict]:
        """
        Execute complex hybrid search for advanced requirements
        """
        if not self.supabase:
            return []
        
        try:
            # Prepare parameters for hybrid search function
            rpc_params = {
                'user_query_text': user_message,
                'match_count': 20,
                'full_text_weight': 1.0,
                'semantic_weight': 1.0,
                'rrf_k': 60
            }
            
            # Map search params to RPC parameters  
            if search_params.get('property_type'):
                rpc_params['p_property_type'] = search_params['property_type']
            
            if search_params.get('sale_or_rent'):
                rpc_params['p_sale_or_rent'] = search_params['sale_or_rent']
            
            if search_params.get('bedrooms') is not None:
                rpc_params['p_bedrooms'] = search_params['bedrooms']
            
            # Fix locality parameter mapping
            if search_params.get('locality'):
                rpc_params['p_locality'] = search_params['locality']
            
            # Price parameters
            if search_params.get('min_rent_price_aed'):
                rpc_params['p_min_rent_price_aed'] = search_params['min_rent_price_aed']
            if search_params.get('max_rent_price_aed'):
                rpc_params['p_max_rent_price_aed'] = search_params['max_rent_price_aed']
            if search_params.get('min_sale_price_aed'):
                rpc_params['p_min_sale_price_aed'] = search_params['min_sale_price_aed']
            if search_params.get('max_sale_price_aed'):
                rpc_params['p_max_sale_price_aed'] = search_params['max_sale_price_aed']
            
            # Feature parameters
            if search_params.get('study') is not None:
                rpc_params['p_study'] = search_params['study']
            if search_params.get('maid_room') is not None:
                rpc_params['p_maid_room'] = search_params['maid_room']
            if search_params.get('landscaped_garden') is not None:
                rpc_params['p_landscaped_garden'] = search_params['landscaped_garden']
            if search_params.get('park_pool_view') is not None:
                rpc_params['p_park_pool_view'] = search_params['park_pool_view']
            
            # Execute hybrid search
            logger.info(f"🔍 [HYBRID_SEARCH] Executing with params: {rpc_params}")
            response = self.supabase.rpc('hybrid_property_search', rpc_params).execute()
            
            if response.data:
                logger.info(f"✅ [HYBRID_SEARCH] Found {len(response.data)} results")
                return response.data
            else:
                logger.warning(f"⚠️ [HYBRID_SEARCH] No results found, trying fallback searches...")
                
                # Try fallback searches with relaxed criteria
                fallback_results = await self._try_fallback_searches(search_params, user_message)
                if fallback_results:
                    logger.info(f"✅ [FALLBACK] Found {len(fallback_results)} results with relaxed criteria")
                    return fallback_results
                
                return []
                
        except Exception as e:
            logger.error(f"❌ Hybrid query failed: {str(e)}")
            # Fallback to simple query
            return await self._execute_simple_query(search_params)
    
    async def _try_fallback_searches(self, original_params: Dict[str, Any], user_message: str) -> List[Dict]:
        """
        Try various fallback searches when main search returns no results
        """
        fallback_attempts = [
            # 1. Try direct table query (bypasses is_trained=true requirement)
            "direct_table_query",
            
            # 2. Remove location restriction  
            {k: v for k, v in original_params.items() if k != 'locality'},
            
            # 3. Remove budget restrictions
            {k: v for k, v in original_params.items() if not k.endswith('_price_aed')},
            
            # 4. Try different property types
            {**{k: v for k, v in original_params.items() if k != 'property_type'}, 'property_type': 'Apartment'},
            
            # 5. Very broad search - just transaction type
            {'sale_or_rent': original_params.get('sale_or_rent', 'sale')},
        ]
        
        for i, fallback_params in enumerate(fallback_attempts):
            try:
                logger.info(f"🔄 [FALLBACK_{i+1}] Trying: {fallback_params}")
                
                # Special handling for direct table query
                if fallback_params == "direct_table_query":
                    results = await self._execute_direct_table_query(original_params)
                else:
                    # Use simple query for other fallbacks
                    results = await self._execute_simple_query(fallback_params)
                
                if results:
                    logger.info(f"✅ [FALLBACK_{i+1}] Found {len(results)} results")
                    return results[:5]  # Return top 5 results
                    
            except Exception as e:
                logger.warning(f"⚠️ [FALLBACK_{i+1}] Failed: {e}")
                continue
        
        logger.warning("❌ [FALLBACK] All fallback searches failed")
        return []
    
    async def _execute_direct_table_query(self, search_params: Dict[str, Any]) -> List[Dict]:
        """
        Direct table query that bypasses is_trained requirement for development/testing
        """
        if not self.supabase:
            return []
        
        try:
            logger.info("🔍 [DIRECT_QUERY] Bypassing is_trained requirement for testing")
            
            # Build direct table query (no is_trained filter)
            query = self.supabase.table('property_vectorstore').select(
                'id, original_property_id, property_type, sale_or_rent, bedrooms, '
                'bathrooms, sale_price_aed, rent_price_aed, bua_sqft, address, '
                'building_name, study, maid_room, park_pool_view, landscaped_garden, '
                'covered_parking_spaces'
            )
            
            # Apply basic filters
            if search_params.get('sale_or_rent'):
                query = query.eq('sale_or_rent', search_params['sale_or_rent'])
            
            if search_params.get('property_type'):
                query = query.eq('property_type', search_params['property_type'])
            
            if search_params.get('bedrooms') is not None:
                query = query.eq('bedrooms', search_params['bedrooms'])
            
            # Locality filtering with ILIKE for partial matches
            if search_params.get('locality'):
                # Use textSearch for JSON field
                query = query.textSearch('address', f"'{search_params['locality']}'", config='english')
            
            # Price filters
            if search_params.get('min_rent_price_aed'):
                query = query.gte('rent_price_aed', search_params['min_rent_price_aed'])
            if search_params.get('max_rent_price_aed'):
                query = query.lte('rent_price_aed', search_params['max_rent_price_aed'])
            if search_params.get('min_sale_price_aed'):
                query = query.gte('sale_price_aed', search_params['min_sale_price_aed'])
            if search_params.get('max_sale_price_aed'):
                query = query.lte('sale_price_aed', search_params['max_sale_price_aed'])
            
            # Order and limit
            query = query.order('created_at', desc=True)
            query = query.limit(20)
            
            # Execute query
            response = query.execute()
            
            if response.data:
                logger.info(f"✅ [DIRECT_QUERY] Found {len(response.data)} results")
                return response.data
            else:
                logger.warning(f"⚠️ [DIRECT_QUERY] No results found")
                return []
                
        except Exception as e:
            logger.error(f"❌ Direct table query failed: {str(e)}")
            return []
    
    def format_properties_for_whatsapp(self, properties: List[Dict], user_requirements: Dict[str, Any]) -> str:
        """
        Format property list for WhatsApp with smart truncation
        """
        if not properties:
            return "I couldn't find any properties matching your criteria. Would you like to try different requirements?"
        
        # Limit to 10 properties for WhatsApp
        display_properties = properties[:10]
        
        response_parts = [f"🏠 **Found {len(properties)} properties!**\n"]
        
        for i, prop in enumerate(display_properties, 1):
            # Format property entry
            prop_type = prop.get('property_type', 'Property')
            bedrooms = prop.get('bedrooms', 0)
            
            # Price formatting
            price_str = ""
            if prop.get('sale_price_aed'):
                price_str = f"AED {prop['sale_price_aed']:,}"
            elif prop.get('rent_price_aed'):
                price_str = f"AED {prop['rent_price_aed']:,}/year"
            else:
                price_str = "Price on request"
            
            # Location
            address = prop.get('address', {})
            if isinstance(address, str):
                try:
                    import json
                    address = json.loads(address)
                except:
                    address = {}
            
            locality = address.get('locality', 'Dubai') if isinstance(address, dict) else 'Dubai'
            
            # Features
            features = []
            if prop.get('bua_sqft'):
                features.append(f"{prop['bua_sqft']} sqft")
            if prop.get('bathrooms'):
                features.append(f"{prop['bathrooms']} bath")
            if prop.get('study'):
                features.append("study")
            if prop.get('maid_room'):
                features.append("maid room")
            if prop.get('landscaped_garden'):
                features.append("garden")
            if prop.get('covered_parking_spaces'):
                features.append(f"{prop['covered_parking_spaces']} parking")
            
            feature_str = " • ".join(features) if features else ""
            
            property_line = f"{i}. 🏠 *{bedrooms}BR {prop_type}*\n"
            property_line += f"💰 {price_str}\n"
            property_line += f"📍 {locality}\n"
            if feature_str:
                property_line += f"✨ {feature_str}\n"
            
            response_parts.append(property_line)
        
        # Add action buttons
        response_parts.append("\n👉 Tell me about property 1")
        response_parts.append("📅 Book visit for property 2")
        response_parts.append("🔍 Show me different options")
        
        return "\n".join(response_parts)


# Global optimized search instance
optimized_search = OptimizedPropertySearch()
