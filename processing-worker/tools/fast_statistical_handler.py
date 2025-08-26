"""
Ultra-Fast Statistical Query Handler with AI Intent Classification
Professional intent detection instead of amateur regex patterns
"""

import os
import time
import asyncio
from typing import Dict, Any, List, Optional
from supabase import create_client, Client
from openai import AsyncOpenAI
from utils.logger import setup_logger

logger = setup_logger(__name__)

class FastStatisticalQueryHandler:
    """
    Lightning-fast handler for statistical queries with AI-powered intent classification
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
            print("Warning: Supabase credentials not found. Statistical queries will be limited.")
            self.supabase = None
        
        # AI-powered intent classification
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Simple in-memory cache for repeated queries
        self.query_cache = {}
        self.intent_cache = {}  # Cache intent classifications
        self.cache_ttl = 300  # 5 minutes TTL for statistical queries
        
        # Statistical query types that can be fast-tracked
        self.statistical_operations = {
            # BASIC PRICE QUERIES
            'cheapest': {'sort': 'price_asc', 'limit': 5},
            'most_expensive': {'sort': 'price_desc', 'limit': 1},
            
            # SIZE QUERIES
            'largest': {'sort': 'size_desc', 'limit': 1},
            'smallest': {'sort': 'size_asc', 'limit': 1},
            
            # BEDROOM-SPECIFIC QUERIES
            'cheapest_1br': {'sort': 'price_asc', 'limit': 5, 'bedrooms': 1},
            'cheapest_2br': {'sort': 'price_asc', 'limit': 5, 'bedrooms': 2},
            'cheapest_3br': {'sort': 'price_asc', 'limit': 5, 'bedrooms': 3},
            'cheapest_4br': {'sort': 'price_asc', 'limit': 5, 'bedrooms': 4},
            
            # PROPERTY TYPE SPECIFIC
            'cheapest_apartment': {'sort': 'price_asc', 'limit': 10, 'property_type': 'Apartment'},
            'cheapest_villa': {'sort': 'price_asc', 'limit': 5, 'property_type': 'Villa'},
            'cheapest_townhouse': {'sort': 'price_asc', 'limit': 5, 'property_type': 'Townhouse'},
            'cheapest_penthouse': {'sort': 'price_asc', 'limit': 5, 'property_type': 'Penthouse'},
            
            # AREA-SPECIFIC QUERIES
            'cheapest_in_area': {'sort': 'price_asc', 'limit': 1, 'location_filter': True},
            'largest_in_area': {'sort': 'size_desc', 'limit': 1, 'location_filter': True},
            
            # MARKET STATISTICS
            'average_price': {'aggregation': 'AVG', 'field': 'price'},
            'average_price_1br': {'aggregation': 'AVG', 'field': 'price', 'bedrooms': 1},
            'average_price_2br': {'aggregation': 'AVG', 'field': 'price', 'bedrooms': 2},
            'average_price_3br': {'aggregation': 'AVG', 'field': 'price', 'bedrooms': 3},
            'average_size': {'aggregation': 'AVG', 'field': 'size'},
            'total_properties': {'aggregation': 'COUNT', 'field': '*'},
            
            # PRICE RANGE QUERIES
            'properties_under_1m': {'filter': 'price_range', 'max_price': 1000000},
            'properties_under_500k': {'filter': 'price_range', 'max_price': 500000},
            'properties_over_5m': {'filter': 'price_range', 'min_price': 5000000},
            
            # SIZE RANGE QUERIES
            'properties_over_2000sqft': {'filter': 'size_range', 'min_size': 2000},
            'properties_under_1000sqft': {'filter': 'size_range', 'max_size': 1000},
            
            # PREMIUM FEATURES
            'properties_with_study': {'filter': 'feature', 'feature': 'study'},
            'properties_with_maid_room': {'filter': 'feature', 'feature': 'maid_room'},
            'properties_with_garden': {'filter': 'feature', 'feature': 'landscaped_garden'},
            'properties_with_pool_view': {'filter': 'feature', 'feature': 'park_pool_view'},
            'properties_with_parking': {'filter': 'feature', 'feature': 'covered_parking_spaces'},
            
            # PRICE PER SQFT ANALYSIS
            'best_value': {'sort': 'price_per_sqft_asc', 'limit': 1},
            'worst_value': {'sort': 'price_per_sqft_desc', 'limit': 1},
            'average_price_per_sqft': {'aggregation': 'AVG', 'field': 'price_per_sqft'},
        }

    async def classify_intent(self, query: str) -> Optional[str]:
        """
        Use AI to classify user intent - much more robust than regex
        Handles typos, different languages, various phrasings
        """
        
        # Check intent cache first
        cache_key = f"intent_{query.lower().strip()}"
        cached_intent = self._get_intent_from_cache(cache_key)
        if cached_intent:
            return cached_intent
        
        try:
            classification_prompt = f"""
You are a real estate query classifier. Analyze this query and return the EXACT classification name if it matches.

Query: "{query}"

**EXACT MATCHES ONLY:**

cheapest - "cheapest property", "lowest price property"
most_expensive - "most expensive property", "highest price property" 
largest - "largest property", "biggest property"
smallest - "smallest property", "tiniest property"

cheapest_apartment - "cheapest apartment", "cheapest flat"
cheapest_villa - "cheapest villa", "cheapest house"
cheapest_townhouse - "cheapest townhouse"

cheapest_1br - "cheapest 1 bedroom", "cheapest one bedroom", "cheapest studio"
cheapest_2br - "cheapest 2 bedroom", "cheapest two bedroom"
cheapest_3br - "cheapest 3 bedroom", "cheapest three bedroom"

average_price - "average price", "mean price", "typical price"

Respond with the EXACT classification name, or "complex" if no match.

Response:"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": classification_prompt}],
                max_tokens=20,
                temperature=0.1
            )
            
            intent = response.choices[0].message.content.strip().lower()
            
            # Validate the response
            valid_intents = list(self.statistical_operations.keys()) + ['complex']
            if intent in valid_intents and intent != 'complex':
                # Cache the intent classification
                self._cache_intent(cache_key, intent)
                logger.info(f"🧠 AI classified '{query}' as: {intent}")
                return intent
            else:
                logger.info(f"🧠 AI classified '{query}' as complex query")
                return None
                
        except Exception as e:
            logger.warning(f"Intent classification failed: {str(e)}")
            return None

    async def detect_sale_or_rent_intent(self, query: str) -> str:
        """
        TRULY AGENTIC: AI-powered detection of sale vs rent intent
        This makes the system intelligent instead of hardcoded
        """
        try:
            classification_prompt = f"""
Analyze this real estate query and determine if the user is asking about properties for SALE or for RENT.

Query: "{query}"

Look for keywords and context clues:
- SALE indicators: "buy", "purchase", "cheapest to buy", "property for sale", "apartment to buy"
- RENT indicators: "rent", "rental", "cheapest to rent", "property for rent", "apartment to rent"
- If no clear indication, default to "sale" as most property searches are for buying

Examples:
- "cheapest property" → "sale" (default)
- "cheapest property to rent" → "rent"
- "what is the cheapest apartment for rent" → "rent"
- "most expensive villa to buy" → "sale"
- "largest rental property" → "rent"

Respond with ONLY one word:
- sale
- rent

Response:"""

            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": classification_prompt}],
                max_tokens=5,
                temperature=0.1
            )
            
            intent = response.choices[0].message.content.strip().lower()
            
            if intent in ['sale', 'rent']:
                logger.info(f"🏡 AI detected {intent} intent for: '{query}'")
                return intent
            else:
                logger.info(f"🏡 Defaulting to 'sale' for: '{query}'")
                return 'sale'
                
        except Exception as e:
            logger.warning(f"Sale/rent detection failed: {str(e)}, defaulting to 'sale'")
            return 'sale'

    def _get_intent_from_cache(self, cache_key: str) -> Optional[str]:
        """Get intent from cache if still valid"""
        if cache_key in self.intent_cache:
            cached_item = self.intent_cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                return cached_item['intent']
            else:
                del self.intent_cache[cache_key]
        return None
    
    def _cache_intent(self, cache_key: str, intent: str):
        """Cache intent classification"""
        self.intent_cache[cache_key] = {
            'intent': intent,
            'timestamp': time.time()
        }
        
        # Simple cache management
        if len(self.intent_cache) > 200:
            oldest_key = min(self.intent_cache.keys(), 
                           key=lambda k: self.intent_cache[k]['timestamp'])
            del self.intent_cache[oldest_key]
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache if still valid"""
        if cache_key in self.query_cache:
            cached_item = self.query_cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                return cached_item['data']
            else:
                # Remove expired cache entry
                del self.query_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]):
        """Cache result with timestamp"""
        self.query_cache[cache_key] = {
            'data': result.copy(),
            'timestamp': time.time()
        }
        
        # Simple cache size management - keep last 100 queries
        if len(self.query_cache) > 100:
            oldest_key = min(self.query_cache.keys(), 
                           key=lambda k: self.query_cache[k]['timestamp'])
            del self.query_cache[oldest_key]

    async def can_handle_fast(self, query: str) -> Optional[str]:
        """
        Professional AI-powered intent detection
        Returns intent type if can be fast-tracked, None otherwise
        """
        return await self.classify_intent(query)
    
    async def execute_fast_query(self, query_type: str, original_query: str) -> Dict[str, Any]:
        """
        Execute ultra-fast statistical query with AI intent classification and caching
        NOW TRULY AGENTIC - detects sale vs rent automatically
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = f"{query_type}_{original_query.lower().strip()}"
        cached_result = self._get_from_cache(cache_key)
        
        if cached_result:
            logger.info(f"⚡⚡ CACHE HIT for {query_type} - returning instantly")
            cached_result['execution_time_ms'] = (time.time() - start_time) * 1000  # Update timing
            cached_result['cache_hit'] = True
            return cached_result
        
        # AGENTIC: AI-powered detection of sale vs rent intent
        sale_or_rent = await self.detect_sale_or_rent_intent(original_query)
        
        config = self.statistical_operations[query_type].copy()
        config['sale_or_rent'] = sale_or_rent  # Add detected intent to config
        
        # Build optimized SQL query
        if config.get('aggregation'):
            # Aggregation queries (average, sum, etc.)
            response = await self._execute_aggregation_query(config)
        elif config.get('filter'):
            # Filter-based queries (price ranges, features, etc.)
            response = await self._execute_filter_query(config)
        else:
            # Sorting queries (cheapest, largest, etc.)
            response = await self._execute_sorting_query(config)
        
        execution_time = (time.time() - start_time) * 1000
        
        result = {
            'results': response.data if response.data else [],
            'query_type': query_type,
            'execution_time_ms': execution_time,
            'method': 'AI_AGENTIC_PATH',  # Updated to reflect truly agentic behavior
            'original_query': original_query,
            'sale_or_rent': sale_or_rent,
            'cache_hit': False
        }
        
        # Cache the result for future queries
        self._cache_result(cache_key, result)
        
        return result

    async def _execute_sorting_query(self, config: Dict[str, Any]) -> Any:
        """Execute optimized sorting query using new database function"""
        
        sort_by = config['sort']
        limit = config.get('limit', 10)
        
        # Use the new optimized function for better performance
        try:
            # Map sort types to stat types
            stat_type_map = {
                'price_asc': 'cheapest',
                'price_desc': 'most_expensive', 
                'size_desc': 'largest',
                'size_asc': 'smallest'
            }
            
            stat_type = stat_type_map.get(sort_by)
            
            if stat_type:
                # Use the optimized SQL function
                response = self.supabase.rpc('get_property_statistics', {
                    'p_stat_type': stat_type
                }).execute()
                
                if response.data:
                    return response
            
            # Fallback to original method if function not available
            return await self._execute_sorting_query_fallback(config)
            
        except Exception as e:
            logger.warning(f"Optimized function failed, using fallback: {str(e)}")
            return await self._execute_sorting_query_fallback(config)
    
    async def _execute_sorting_query_fallback(self, config: Dict[str, Any]) -> Any:
        """
        TRULY AGENTIC: Handles sophisticated real estate queries
        Supports bedrooms, property types, areas, features, and value analysis
        """
        
        sort_by = config['sort']
        limit = config.get('limit', 10)
        sale_or_rent = config.get('sale_or_rent', 'sale')
        
        # Build the base query
        base_select = ('id, original_property_id, property_type, bedrooms, bathrooms, bua_sqft, '
                      'sale_price_aed, rent_price_aed, sale_or_rent, address, building_name, '
                      'study, maid_room, landscaped_garden, park_pool_view, covered_parking_spaces')
        
        # Start building the query
        query = self.supabase.from_('property_vectorstore').select(base_select)
        
        # Apply sale_or_rent filter
        query = query.eq('sale_or_rent', sale_or_rent)
        
        # Apply bedroom filter if specified
        if config.get('bedrooms'):
            query = query.eq('bedrooms', config['bedrooms'])
            
        # Apply property type filter if specified
        if config.get('property_type'):
            query = query.eq('property_type', config['property_type'])
            
        # Apply location filter if specified (will be enhanced with AI location extraction)
        if config.get('location_filter'):
            # For now, we'll handle this in a future enhancement
            pass
        
        # Apply sorting and price/size filters
        if sort_by == 'price_asc':
            # Cheapest property queries
            if sale_or_rent == 'rent':
                query = query.not_.is_('rent_price_aed', 'null').order('rent_price_aed', desc=False)
            else:
                query = query.not_.is_('sale_price_aed', 'null').order('sale_price_aed', desc=False)
                
        elif sort_by == 'price_desc':
            # Most expensive property queries
            if sale_or_rent == 'rent':
                query = query.not_.is_('rent_price_aed', 'null').order('rent_price_aed', desc=True)
            else:
                query = query.not_.is_('sale_price_aed', 'null').order('sale_price_aed', desc=True)
                
        elif sort_by == 'size_desc':
            # Largest property queries
            query = query.not_.is_('bua_sqft', 'null').gt('bua_sqft', 0).order('bua_sqft', desc=True)
            
        elif sort_by == 'size_asc':
            # Smallest property queries
            query = query.not_.is_('bua_sqft', 'null').gt('bua_sqft', 0).order('bua_sqft', desc=False)
            
        elif sort_by == 'price_per_sqft_asc':
            # Best value properties - calculate price per sqft on the fly
            if sale_or_rent == 'rent':
                # For rent, we'll order by rent_price_aed/bua_sqft
                query = query.not_.is_('rent_price_aed', 'null').not_.is_('bua_sqft', 'null').gt('bua_sqft', 0)
                # Note: PostgREST doesn't support computed columns in ORDER BY easily
                # We'll need to use RPC for this or calculate in Python
                query = query.order('rent_price_aed', desc=False).limit(50)  # Get top 50 and calculate
            else:
                query = query.not_.is_('sale_price_aed', 'null').not_.is_('bua_sqft', 'null').gt('bua_sqft', 0)
                query = query.order('sale_price_aed', desc=False).limit(50)  # Get top 50 and calculate
                
        elif sort_by == 'price_per_sqft_desc':
            # Worst value properties
            if sale_or_rent == 'rent':
                query = query.not_.is_('rent_price_aed', 'null').not_.is_('bua_sqft', 'null').gt('bua_sqft', 0)
                query = query.order('rent_price_aed', desc=True).limit(50)
            else:
                query = query.not_.is_('sale_price_aed', 'null').not_.is_('bua_sqft', 'null').gt('bua_sqft', 0)
                query = query.order('sale_price_aed', desc=True).limit(50)
        
        # Apply final limit
        query = query.limit(limit)
        
        # Build description for logging
        filters = []
        if config.get('bedrooms'):
            filters.append(f"{config['bedrooms']}BR")
        if config.get('property_type'):
            filters.append(config['property_type'])
        filter_desc = f" ({', '.join(filters)})" if filters else ""
        
        logger.info(f"🧠 AGENTIC QUERY: {sort_by} for {sale_or_rent}{filter_desc}")
        
        response = query.execute()
        
        # Post-process for price per sqft calculations
        if 'price_per_sqft' in sort_by and response.data:
            # Calculate price per sqft and sort in Python
            price_col = 'rent_price_aed' if sale_or_rent == 'rent' else 'sale_price_aed'
            
            for item in response.data:
                if item.get(price_col) and item.get('bua_sqft') and item['bua_sqft'] > 0:
                    item['price_per_sqft'] = item[price_col] / item['bua_sqft']
                else:
                    item['price_per_sqft'] = float('inf')
            
            # Sort by price per sqft
            reverse_sort = 'desc' in sort_by
            response.data = sorted(response.data, 
                                 key=lambda x: x.get('price_per_sqft', float('inf')), 
                                 reverse=reverse_sort)[:limit]
        
        return response
    
    async def _execute_aggregation_query(self, config: Dict[str, Any]) -> Any:
        """Execute sophisticated aggregation queries with filters"""
        
        sale_or_rent = config.get('sale_or_rent', 'sale')
        aggregation = config.get('aggregation')
        field = config.get('field')
        
        # Choose the right price column
        price_column = 'rent_price_aed' if sale_or_rent == 'rent' else 'sale_price_aed'
        
        # Start building query
        if aggregation == 'COUNT':
            # Count queries
            query = self.supabase.from_('property_vectorstore').select(
                'id', count='exact'
            ).eq('sale_or_rent', sale_or_rent)
            
        elif aggregation == 'AVG' and field == 'price':
            # Average price queries
            query = self.supabase.from_('property_vectorstore').select(
                price_column
            ).eq('sale_or_rent', sale_or_rent).not_.is_(price_column, 'null')
            
        elif aggregation == 'AVG' and field == 'size':
            # Average size queries
            query = self.supabase.from_('property_vectorstore').select(
                'bua_sqft'
            ).eq('sale_or_rent', sale_or_rent).not_.is_('bua_sqft', 'null').gt('bua_sqft', 0)
            
        elif aggregation == 'AVG' and field == 'price_per_sqft':
            # Average price per sqft
            query = self.supabase.from_('property_vectorstore').select(
                f'{price_column}, bua_sqft'
            ).eq('sale_or_rent', sale_or_rent).not_.is_(price_column, 'null').not_.is_('bua_sqft', 'null').gt('bua_sqft', 0)
        
        # Apply bedroom filter if specified
        if config.get('bedrooms'):
            query = query.eq('bedrooms', config['bedrooms'])
            
        # Apply property type filter if specified
        if config.get('property_type'):
            query = query.eq('property_type', config['property_type'])
        
        response = query.execute()
        
        # Post-process aggregations that can't be done in PostgREST
        if aggregation == 'AVG' and response.data:
            if field == 'price':
                prices = [item[price_column] for item in response.data if item.get(price_column)]
                avg_price = sum(prices) / len(prices) if prices else 0
                # Return in the format expected by the response generator
                response.data = [{'average_price': avg_price, 'count': len(prices)}]
                
            elif field == 'size':
                sizes = [item['bua_sqft'] for item in response.data if item.get('bua_sqft')]
                avg_size = sum(sizes) / len(sizes) if sizes else 0
                response.data = [{'average_size': avg_size, 'count': len(sizes)}]
                
            elif field == 'price_per_sqft':
                price_per_sqfts = []
                for item in response.data:
                    if item.get(price_column) and item.get('bua_sqft') and item['bua_sqft'] > 0:
                        price_per_sqfts.append(item[price_column] / item['bua_sqft'])
                
                avg_price_per_sqft = sum(price_per_sqfts) / len(price_per_sqfts) if price_per_sqfts else 0
                response.data = [{'average_price_per_sqft': avg_price_per_sqft, 'count': len(price_per_sqfts)}]
        
        return response

    async def _execute_filter_query(self, config: Dict[str, Any]) -> Any:
        """Execute filter-based queries (price ranges, features, etc.)"""
        
        filter_type = config.get('filter')
        filter_value = config.get('max_price') if filter_type == 'price_range' else config.get('min_price')
        
        if filter_type == 'price_range':
            query = self.supabase.from_('property_vectorstore').select(
                'sale_price_aed, rent_price_aed, bua_sqft'
            ).not_.is_('sale_price_aed', 'null').not_.is_('rent_price_aed', 'null')
            
            if filter_value:
                query = query.lt('sale_price_aed', filter_value)
            
            query = query.order('sale_price_aed', desc=False)
            
        elif filter_type == 'size_range':
            query = self.supabase.from_('property_vectorstore').select(
                'bua_sqft'
            ).not_.is_('bua_sqft', 'null')
            
            if filter_value:
                query = query.lt('bua_sqft', filter_value)
            
            query = query.order('bua_sqft', desc=False)
            
        elif filter_type == 'feature':
            query = self.supabase.from_('property_vectorstore').select(
                'sale_price_aed, rent_price_aed, bua_sqft'
            ).not_.is_('sale_price_aed', 'null').not_.is_('rent_price_aed', 'null')
            
            if filter_value == 'study':
                query = query.eq('study', True)
            elif filter_value == 'maid_room':
                query = query.eq('maid_room', True)
            elif filter_value == 'landscaped_garden':
                query = query.eq('landscaped_garden', True)
            elif filter_value == 'park_pool_view':
                query = query.eq('park_pool_view', True)
            elif filter_value == 'covered_parking_spaces':
                query = query.eq('covered_parking_spaces', True)
            
            query = query.order('sale_price_aed', desc=False)
            
        query = query.limit(config.get('limit', 10))
        
        return query.execute()

    def generate_fast_response(self, results: List[Dict], query_type: str, execution_time: float, sale_or_rent: str = 'sale') -> str:
        """
        Generate WhatsApp-optimized response for statistical queries
        """
        # Import here to avoid circular imports
        from utils.whatsapp_formatter import whatsapp_formatter
        
        if not results:
            return whatsapp_formatter.format_no_results(f"{query_type} properties {sale_or_rent}")
        
        property_data = results[0]
        return whatsapp_formatter.format_statistical_result(query_type, property_data, execution_time)
    
    def _format_location(self, address: Optional[Dict]) -> str:
        """Format address for display"""
        if not address:
            return "Location not specified"
        
        parts = []
        if address.get('locality'):
            parts.append(address['locality'])
        if address.get('city'):
            parts.append(address['city'])
        
        return ', '.join(parts) if parts else "Location not specified"