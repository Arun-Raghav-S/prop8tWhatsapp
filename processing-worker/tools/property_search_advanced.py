"""
Advanced Property Search Tools for WhatsApp Agent System
Full feature parity with TypeScript property-agent-backup.ts
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Union
from openai import AsyncOpenAI
from supabase import create_client, Client
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from utils.logger import setup_logger
from utils.text_processor import MessageProcessor
from utils.response_cache import response_cache
from tools.performance_optimized_search import ultra_fast_property_search

logger = setup_logger(__name__)

# Initialize required components
message_processor = MessageProcessor()


class QueryParams(BaseModel):
    """Property search query parameters - matches TypeScript interface"""
    query_text: Optional[str] = None
    property_type: Optional[Union[str, List[str]]] = None
    sale_or_rent: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    min_bua_sqft: Optional[float] = None
    max_bua_sqft: Optional[float] = None
    min_sale_price_aed: Optional[int] = None
    max_sale_price_aed: Optional[int] = None
    min_rent_price_aed: Optional[int] = None
    max_rent_price_aed: Optional[int] = None
    city: Optional[Union[str, List[str]]] = None
    locality: Optional[Union[str, List[str]]] = None
    address_search: Optional[str] = None
    study: Optional[bool] = None
    maid_room: Optional[bool] = None
    laundry_room: Optional[bool] = None
    additional_reception_area: Optional[bool] = None
    park_pool_view: Optional[bool] = None
    upgraded_ground_flooring: Optional[bool] = None
    landscaped_garden: Optional[bool] = None
    no_maid_room: Optional[bool] = None
    no_study: Optional[bool] = None
    no_laundry_room: Optional[bool] = None
    no_additional_reception_area: Optional[bool] = None
    no_park_pool_view: Optional[bool] = None
    no_upgraded_ground_flooring: Optional[bool] = None
    no_landscaped_garden: Optional[bool] = None
    min_balconies: Optional[int] = None
    max_balconies: Optional[int] = None
    min_covered_parking: Optional[int] = None
    max_covered_parking: Optional[int] = None
    sort_by: Optional[str] = None
    query_type: Optional[str] = None
    match_count: Optional[int] = None
    intelligent_limit: Optional[bool] = True


class PropertyResult(BaseModel):
    """Property search result - matches TypeScript interface"""
    id: str
    original_property_id: Optional[str] = None  # Added for carousel broadcast
    property_type: str
    sale_or_rent: str
    bedrooms: int
    bathrooms: int
    bua_sqft: float
    sale_price_aed: Optional[int] = None
    rent_price_aed: Optional[int] = None
    address: Optional[Union[Dict[str, Any], str]] = None
    building_name: Optional[str] = None
    study: Optional[bool] = None
    maid_room: Optional[bool] = None
    laundry_room: Optional[bool] = None
    additional_reception_area: Optional[bool] = None
    park_pool_view: Optional[bool] = None
    upgraded_ground_flooring: Optional[bool] = None
    landscaped_garden: Optional[bool] = None
    balconies: Optional[int] = None
    covered_parking: Optional[int] = None
    search_rank: Optional[float] = None
    semantic_rank: Optional[float] = None
    full_text_rank: Optional[float] = None


class AgentResponse(BaseModel):
    """Complete agent response - matches TypeScript interface"""
    answer: str
    context: List[PropertyResult]
    extracted_params: QueryParams
    execution_time: float
    debug: Optional[Dict[str, Any]] = None
    industrial_features: Optional[Dict[str, bool]] = None
    
    # Backwards compatibility
    @property
    def properties(self) -> List[PropertyResult]:
        """Alias for context to maintain compatibility"""
        return self.context


class PropertySearchAgent:
    """
    BACKWARDS COMPATIBILITY WRAPPER
    """
    
    def __init__(self):
        # Delegate to the advanced agent
        self._agent = AdvancedPropertySearchAgent()
    
    async def process_query(self, user_query: str, user_context: Dict = None) -> AgentResponse:
        """Backward compatible method"""
        return await self._agent.process_query(user_query, user_context)


class AdvancedPropertySearchAgent:
    """
    Advanced Property Search Agent with full TypeScript feature parity
    """
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("No OpenAI API key found - using mock client")
            # Create a mock client for testing
            from unittest.mock import MagicMock
            self.openai = MagicMock()
        else:
            self.openai = AsyncOpenAI(api_key=api_key)
            
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        # Initialize Supabase client with error handling
        if supabase_url and supabase_key:
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
            except Exception as e:
                print(f"Warning: Could not initialize Supabase client: {e}")
                self.supabase = None
        else:
            print("Warning: Supabase credentials not found. Advanced search will be limited.")
            self.supabase = None
        self.config = {
            "model": os.getenv("AGENT_MODEL", "gpt-4o-mini"),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
            "default_limit": int(os.getenv("DEFAULT_SEARCH_LIMIT", "10"))
        }
    
    async def process_query(self, user_query: str, user_context: Dict = None) -> AgentResponse:
        """
        Professional query processing with caching and optimization
        """
        start_time = time.time()
        
        # Handle case where user_context might be None
        if user_context is None:
            user_context = {}
        
        # STEP 1: Process and normalize the query
        try:
            processed_message = message_processor.process_message(user_query)
            normalized_query = processed_message['corrected']
        except Exception as e:
            logger.warning(f"Message processing failed, using original query: {e}")
            normalized_query = user_query
            processed_message = {'corrections_made': []}
        
        if processed_message['corrections_made']:
            logger.info(f"🔧 Query corrected: '{user_query}' → '{normalized_query}'")
        
        # STEP 2: Check cache first (with error handling)
        cache_key = None
        try:
            cache_key = response_cache._generate_cache_key(normalized_query, user_context)
            cached_response = response_cache.get(cache_key)
            
            if cached_response:
                logger.info(f"⚡ CACHED RESPONSE returned in {(time.time() - start_time) * 1000:.0f}ms")
                return AgentResponse(**cached_response)
        except Exception as e:
            logger.warning(f"Cache lookup failed, proceeding without cache: {e}")
            cache_key = None
        
        logger.info(f"🚀 Starting TAG Pipeline for: {normalized_query}")

        # STEP 3: ULTRA-FAST SEARCH ENGINE (NEW!)
        try:
            # Check if this is a simple property search that can use ultra-fast engine
            if self._should_use_fast_engine(normalized_query):
                logger.info("🚀 Using ULTRA-FAST search engine (no AI needed)")
                
                # Extract sale_or_rent from query
                sale_or_rent = None
                if 'rent' in normalized_query.lower():
                    sale_or_rent = 'rent'
                elif 'buy' in normalized_query.lower() or 'sale' in normalized_query.lower():
                    sale_or_rent = 'sale'
                
                # Get ultra-fast response
                fast_response = await ultra_fast_property_search(normalized_query, sale_or_rent, 5)
                
                # Return as AgentResponse
                return AgentResponse(
                    answer=fast_response,
                    context=[],  # No need for detailed context in fast mode
                    extracted_params=QueryParams(query_text=normalized_query),
                    execution_time=(time.time() - start_time),
                    industrial_features={'ultra_fast_engine': True, 'ai_free': True}
                )
        except Exception as e:
            logger.warning(f"Ultra-fast engine failed, falling back to full pipeline: {e}")

        # STEP 4: Check if we can use template response (with error handling)
        try:
            template_type = response_cache.can_use_template(normalized_query)
            if template_type:
                logger.info(f"📋 TEMPLATE_USED: {template_type} (bypassing carousel logic)")
                return await self._process_with_template(normalized_query, template_type, start_time)
            else:
                logger.info(f"🎠 TEMPLATE_SKIPPED: Using full pipeline for potential carousel")
        except Exception as e:
            logger.warning(f"Template check failed, using full pipeline: {e}")

        # STEP 5: Full pipeline for complex queries
        return await self._continue_full_pipeline(normalized_query, start_time)

    def _should_use_fast_engine(self, query: str) -> bool:
        """
        Determine if query can use ultra-fast engine (no AI needed)
        """
        query_lower = query.lower().strip()
        
        # Fast engine patterns (comprehensive list)
        fast_patterns = [
            'properties to rent', 'properties to buy', 'rental properties',
            'top properties', 'best properties', 'cheapest', 'affordable',
            'luxury', 'premium', 'properties with', 'show me properties',
            'find properties', 'give me properties', 'top 4 properties',
            'top 5 properties', 'your top', 'me your top', 'properteis',
            'property to rent', 'property to buy', 'rent properties'
        ]
        
        return any(pattern in query_lower for pattern in fast_patterns)

    async def _continue_full_pipeline(self, normalized_query: str, start_time: float) -> AgentResponse:
        """
        Continue with the full pipeline for complex queries
        """
        # STEP 5: Full pipeline for complex queries
        # Query Synthesis (optimized)
        synthesis_start = time.time()
        extracted_params = await self.synthesize_query(normalized_query)
        synthesis_time = (time.time() - synthesis_start) * 1000

        # Query Execution  
        search_start = time.time()
        search_results, industrial_features = await self.execute_query(extracted_params, normalized_query)
        search_time = (time.time() - search_start) * 1000

        # Check if clarification is needed
        if industrial_features.get('intelligent_question_handling'):
            return AgentResponse(
                answer="I'd be happy to help! Are you looking to **buy** or **rent** a property? This will help me show you the most relevant options. 🏠",
                context=[],
                extracted_params=extracted_params,
                execution_time=(time.time() - start_time),
                industrial_features=industrial_features
            )

        # Answer Generation (optimized)
        generation_start = time.time()
        answer = await self.generate_answer(normalized_query, extracted_params, search_results, industrial_features)
        generation_time = (time.time() - generation_start) * 1000

        total_time = (time.time() - start_time) * 1000

        response = AgentResponse(
            answer=answer,
            context=search_results,
            extracted_params=extracted_params,
            execution_time=total_time,
            debug={
                "synthesis_time": synthesis_time,
                "search_time": search_time,
                "generation_time": generation_time,
                "cache_miss": True
            },
            industrial_features=industrial_features
        )
        
        # STEP 5: Cache the response (with error handling)
        try:
            if cache_key:
                response_cache.set(cache_key, response.dict())
            else:
                logger.info("🎠 CACHE_SKIP: No cache key available (likely carousel query)")
        except Exception as e:
            logger.warning(f"Failed to cache response: {e}")
        
        return response

    async def _process_with_template(self, query: str, template_type: str, start_time: float) -> AgentResponse:
        """Process query using template response for speed"""
        # Quick database query for basic property data
        try:
            result = self.supabase.table('property_vectorstore').select('*').limit(5).execute()
            search_results = [PropertyResult(**row) for row in result.data]
            
            # Generate template context
            context = {
                'property_count': len(search_results),
                'property_listings': self._format_properties_simple(search_results)
            }
            
            answer = response_cache.generate_template_response(template_type, context)
            
            total_time = (time.time() - start_time) * 1000
            
            return AgentResponse(
                answer=answer,
                context=search_results,
                extracted_params={},
                execution_time=total_time,
                debug={"template_used": template_type, "fast_path": True},
                industrial_features={"template_response": True}
            )
            
        except Exception as e:
            logger.error(f"Template processing failed: {e}")
            # Fallback to regular processing
            return await self._fallback_processing(query, start_time)

    def _format_properties_simple(self, properties: List[PropertyResult]) -> str:
        """Simple property formatting for templates"""
        formatted = ""
        for i, prop in enumerate(properties[:3]):
            address = prop.address or {}
            locality = address.get('locality', 'Dubai') if isinstance(address, dict) else 'Dubai'
            
            price = "Contact for price"
            if prop.sale_price_aed:
                price = f"AED {prop.sale_price_aed:,}"
            elif prop.rent_price_aed:
                price = f"AED {prop.rent_price_aed:,}/year"
            
            formatted += f"**{i+1}. {prop.property_type or 'Property'} in {locality}**\n"
            formatted += f"📍 **Location:** {prop.building_name or 'Premium Location'}\n"
            formatted += f"💰 **Price:** {price}\n"
            formatted += f"📐 **Size:** {prop.bua_sqft or 0} sqft\n"
            formatted += f"🔍 **Reference:** {prop.id[:8]}...\n\n"
        
        return formatted

    async def _fallback_processing(self, query: str, start_time: float) -> AgentResponse:
        """Fallback to basic processing if template fails"""
        # Minimal processing for emergency cases
        try:
            result = self.supabase.table('property_vectorstore').select('*').limit(3).execute()
            search_results = [PropertyResult(**row) for row in result.data]
            
            answer = "🏠 I found some properties for you. Let me get more details..."
            
            return AgentResponse(
                answer=answer,
                context=search_results,
                extracted_params={},
                execution_time=(time.time() - start_time) * 1000,
                debug={"fallback_used": True},
                industrial_features={}
            )
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            return AgentResponse(
                answer="I'm experiencing some technical difficulties. Please try again.",
                context=[],
                extracted_params={},
                execution_time=(time.time() - start_time) * 1000,
                debug={"error": str(e)},
                industrial_features={}
            )

    async def synthesize_query(self, user_query: str) -> QueryParams:
        """
        Industrial-grade query synthesis - exact match to TypeScript
        """
        logger.info("🔍 Step 1: Industrial-Grade Query Synthesis")

        query_parsing_prompt = {
            "role": "system",
            "content": """You are an expert real estate query parser with INDUSTRIAL-GRADE capabilities. Extract structured search parameters from natural language property queries.

RETURN VALID JSON with the following ENHANCED schema:

CRITICAL SEMANTIC INTERPRETATION RULES:
- "quiet place to work from home" → study: true
- "barbecues" or "entertaining" or "friends over" or "outdoor" or "garden" → landscaped_garden: true
- "upgraded flooring" → upgraded_ground_flooring: true
- "NO maid room" or "without maid room" or "DO NOT have a maid" → no_maid_room: true
- "cheapest" or "absolute cheapest" → sort_by: "price_asc"
- "most expensive" → sort_by: "price_desc" 
- "largest" or "biggest" or "single largest" → sort_by: "size_desc"
- "smallest" → sort_by: "size_asc"
- "newest" → sort_by: "newest"
- "oldest" → sort_by: "oldest"
- "cheapest first then largest" → sort_by: "price_asc_then_size_desc"
- "largest first then cheapest" → sort_by: "size_desc_then_price_asc"
- "newest first then smallest" → sort_by: "newest_then_size_asc"
- "single largest" → sort_by: "size_desc", match_count: 1
- "top 5" or "your top 5" or "best 5" or "show me 5" → match_count: 5, sort_by: "price_desc"
- "top 10" or "best 10" or "show me 10" → match_count: 10, sort_by: "price_desc"
- "show me" or "give me" or "find me" without specific criteria → query_text: "properties", match_count: 5
- "average price" or "what's the average" or "mean price" → query_type: "statistical"
- "what is the cheapest" or "what's the cheapest" → query_type: "statistical", sort_by: "price_asc", match_count: 1
- "what is the most expensive" or "what's the most expensive" → query_type: "statistical", sort_by: "price_desc", match_count: 1
- "what is the largest" or "what's the largest" → query_type: "statistical", sort_by: "size_desc", match_count: 1
- Location areas like "Dubai Marina" → city or locality field
- Specific areas/communities → locality field
- Street addresses → address_search field

ENHANCED JSON Schema:
{
  "query_text": "string - Semantic search terms",
  "property_type": "string OR array - [Apartment, Villa, Penthouse, Plot, Townhouse]",
  "sale_or_rent": "string - 'sale' or 'rent'", 
  "bedrooms": "integer",
  "bathrooms": "integer",
  "min_bua_sqft": "number",
  "max_bua_sqft": "number", 
  "min_sale_price_aed": "integer",
  "max_sale_price_aed": "integer",
  "min_rent_price_aed": "integer",
  "max_rent_price_aed": "integer",
  "city": "string OR array",
  "locality": "string OR array",
  "address_search": "string",
  
  // POSITIVE BOOLEAN FILTERS
  "study": "boolean",
  "maid_room": "boolean", 
  "laundry_room": "boolean",
  "additional_reception_area": "boolean",
  "park_pool_view": "boolean",
  "upgraded_ground_flooring": "boolean",
  "landscaped_garden": "boolean",
  
  // REVOLUTIONARY: NEGATIVE BOOLEAN FILTERS
  "no_maid_room": "boolean",
  "no_study": "boolean",
  "no_laundry_room": "boolean",
  "no_additional_reception_area": "boolean",
  "no_park_pool_view": "boolean",
  "no_upgraded_ground_flooring": "boolean",
  "no_landscaped_garden": "boolean",
  
  // COUNTER FILTERS
  "min_balconies": "integer",
  "max_balconies": "integer",
  "min_covered_parking": "integer",
  "max_covered_parking": "integer",
  
  // INDUSTRIAL-GRADE SORTING
  "sort_by": "string - price_asc|price_desc|size_asc|size_desc|newest|oldest|bedrooms_asc|bedrooms_desc|price_asc_then_size_desc|size_desc_then_price_asc|newest_then_size_asc",
  "query_type": "string - standard|statistical|aggregation",
  "match_count": "integer - for 'single' queries",
  "intelligent_limit": "boolean - default true"
}

Return only the JSON object, no additional text."""
        }

        try:
            completion = await self.openai.chat.completions.create(
                model=self.config["model"],
                messages=[
                    query_parsing_prompt,
                    {"role": "user", "content": user_query}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )

            extracted_params = json.loads(completion.choices[0].message.content or '{}')
            logger.info(f"✅ Industrial-Grade Extracted Parameters: {json.dumps(extracted_params, indent=2)}")
            
            return QueryParams(**extracted_params)
            
        except Exception as e:
            logger.error(f"❌ Query synthesis failed: {str(e)}")
            return QueryParams(query_text=user_query)

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate OpenAI embedding for semantic search
        """
        try:
            response = await self.openai.embeddings.create(
                model=self.config["embedding_model"],
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {str(e)}")
            return None

    async def execute_query(self, extracted_params: QueryParams, normalized_query: str = "") -> tuple[List[PropertyResult], Dict[str, bool]]:
        """
        Industrial-grade query execution - optimized for speed
        """
        logger.info("⚡ Step 2: Industrial-Grade Query Execution")
        execution_start = time.time()
        
        try:
            # PERFORMANCE OPTIMIZATION: Skip embedding for simple queries
            query_text = extracted_params.query_text or ''
            query_embedding = None
            
            # Skip embedding generation for very generic queries to save time
            simple_queries = ['properties', 'property', 'show me', 'find me', '']
            if query_text.strip() and query_text.lower().strip() not in simple_queries:
                query_embedding = await self.generate_embedding(query_text)
                if query_text.strip():
                    logger.info(f"🧠 Generated embedding for: \"{query_text}\" ({int((time.time() - execution_start) * 1000)}ms)")
            else:
                logger.info(f"⚡ Skipping embedding for simple query: \"{query_text}\" - using direct search")
                # For simple queries, use empty query text to trigger filter_only_results path
                if query_text.lower().strip() in simple_queries:
                    query_text = ''
            
            # 🚨 INTELLIGENT QUESTION HANDLING: Ask for clarification only for very basic queries
            # BUT allow general queries like "cheapest properties", "top 10 properties" to proceed
            very_basic_queries = ['properties', 'property', 'show me properties']
            should_ask_clarification = (
                not extracted_params.sale_or_rent and 
                query_text.lower().strip() in very_basic_queries and
                not any(keyword in query_text.lower() for keyword in ['cheapest', 'top', 'best', 'all', 'available', 'tell me'])
            )
            
            if should_ask_clarification:
                # Return empty results but with clarification flag
                features_used = {'intelligent_question_handling': True}
                return [], features_used
            
            # Prepare search parameters with intelligent match count for general queries
            base_match_count = extracted_params.match_count or self.config["default_limit"]
            
            # Increase match count for general queries that could benefit from carousel
            general_query_keywords = [
                'properties', 'property', 'show me', 'list', 'all properties', 
                'what properties', 'available properties', 'cheapest', 'best', 
                'good properties', 'top', 'most affordable', 'tell me'
            ]
            
            # Check query_text, extracted_params.query_text AND original normalized_query for general keywords
            is_general_query = (
                any(keyword in query_text.lower() for keyword in general_query_keywords) or
                any(keyword in extracted_params.query_text.lower() if extracted_params.query_text else False for keyword in general_query_keywords) or
                any(keyword in normalized_query.lower() for keyword in general_query_keywords)
            )
            
            if is_general_query and base_match_count <= 15:
                match_count = 20  # Increase for general queries to enable carousel
                logger.info(f"🎠 CAROUSEL_LOGIC: General query detected, increasing match_count to {match_count}")
                
                # For general queries without sale_or_rent, search both to maximize results
                if not extracted_params.sale_or_rent:
                    logger.info(f"🎠 CAROUSEL_LOGIC: No sale_or_rent specified, will search both sale and rent for maximum results")
            else:
                match_count = base_match_count
                
            intelligent_limit = extracted_params.intelligent_limit if extracted_params.intelligent_limit is not None else True
            
            logger.info(f"📊 SEARCH_PARAMS: match_count={match_count}, intelligent_limit={intelligent_limit}, is_general={is_general_query}")
            logger.info(f"🔍 QUERY_DEBUG: query_text='{query_text}', extracted_query='{extracted_params.query_text}', normalized='{normalized_query}'")

            # Handle OR conditions for property_type and localities
            all_results = []
            
            property_types = (
                extracted_params.property_type if isinstance(extracted_params.property_type, list)
                else [extracted_params.property_type] if extracted_params.property_type
                else [None]
            )
            
            localities = (
                extracted_params.locality if isinstance(extracted_params.locality, list)
                else [extracted_params.locality] if extracted_params.locality
                else [None]
            )

            # For general queries without sale_or_rent, search both to maximize carousel results
            sale_or_rent_values = []
            if extracted_params.sale_or_rent:
                sale_or_rent_values = [extracted_params.sale_or_rent]
            elif is_general_query:
                # Search both sale and rent for general queries to get more results for carousel
                sale_or_rent_values = ['sale', 'rent']
                logger.info(f"🎠 CAROUSEL_LOGIC: Searching both sale and rent for general query")
            else:
                sale_or_rent_values = [None]  # Let database decide

            # Execute searches for all combinations
            for property_type in property_types:
                for locality in localities:
                    for sale_or_rent in sale_or_rent_values:
                        search_params = {
                            "user_query_text": query_text,
                            "user_query_embedding": query_embedding,
                            "match_count": match_count,
                            "full_text_weight": 1.0,
                            "semantic_weight": 1.0,
                            "rrf_k": 60,
                        }
                        
                        # Add all conditional parameters (matching NEW address schema)
                        if property_type:
                            search_params["p_property_type"] = property_type
                        if sale_or_rent:
                            search_params["p_sale_or_rent"] = sale_or_rent
                        if extracted_params.bedrooms:
                            search_params["p_bedrooms"] = extracted_params.bedrooms
                        if extracted_params.bathrooms:
                            search_params["p_bathrooms"] = extracted_params.bathrooms
                        if extracted_params.min_bua_sqft:
                            search_params["p_min_bua_sqft"] = extracted_params.min_bua_sqft
                        if extracted_params.max_bua_sqft:
                            search_params["p_max_bua_sqft"] = extracted_params.max_bua_sqft
                        if extracted_params.min_sale_price_aed:
                            search_params["p_min_sale_price_aed"] = extracted_params.min_sale_price_aed
                        if extracted_params.max_sale_price_aed:
                            search_params["p_max_sale_price_aed"] = extracted_params.max_sale_price_aed
                        if extracted_params.min_rent_price_aed:
                            search_params["p_min_rent_price_aed"] = extracted_params.min_rent_price_aed
                        if extracted_params.max_rent_price_aed:
                            search_params["p_max_rent_price_aed"] = extracted_params.max_rent_price_aed
                        
                        # NEW ADDRESS-BASED PARAMETERS (updated for new schema)
                        if extracted_params.city:
                            search_params["p_city"] = extracted_params.city
                        if locality:
                            search_params["p_locality"] = locality
                        if extracted_params.address_search:
                            search_params["p_address_search"] = extracted_params.address_search
                        
                        # Positive boolean filters
                        if extracted_params.study is not None:
                            search_params["p_study"] = extracted_params.study
                        if extracted_params.maid_room is not None:
                            search_params["p_maid_room"] = extracted_params.maid_room
                        if extracted_params.laundry_room is not None:
                            search_params["p_laundry_room"] = extracted_params.laundry_room
                        if extracted_params.additional_reception_area is not None:
                            search_params["p_additional_reception_area"] = extracted_params.additional_reception_area
                        if extracted_params.park_pool_view is not None:
                            search_params["p_park_pool_view"] = extracted_params.park_pool_view
                        if extracted_params.upgraded_ground_flooring is not None:
                            search_params["p_upgraded_ground_flooring"] = extracted_params.upgraded_ground_flooring
                        if extracted_params.landscaped_garden is not None:
                            search_params["p_landscaped_garden"] = extracted_params.landscaped_garden
                        
                        # REVOLUTIONARY: Negative boolean filters
                        if extracted_params.no_maid_room is not None:
                            search_params["p_no_maid_room"] = extracted_params.no_maid_room
                        if extracted_params.no_study is not None:
                            search_params["p_no_study"] = extracted_params.no_study
                        if extracted_params.no_laundry_room is not None:
                            search_params["p_no_laundry_room"] = extracted_params.no_laundry_room
                        if extracted_params.no_additional_reception_area is not None:
                            search_params["p_no_additional_reception_area"] = extracted_params.no_additional_reception_area
                        if extracted_params.no_park_pool_view is not None:
                            search_params["p_no_park_pool_view"] = extracted_params.no_park_pool_view
                        if extracted_params.no_upgraded_ground_flooring is not None:
                            search_params["p_no_upgraded_ground_flooring"] = extracted_params.no_upgraded_ground_flooring
                        if extracted_params.no_landscaped_garden is not None:
                            search_params["p_no_landscaped_garden"] = extracted_params.no_landscaped_garden
                        
                        # Counter filters
                        if extracted_params.min_covered_parking:
                            search_params["p_min_covered_parking"] = extracted_params.min_covered_parking
                        if extracted_params.max_covered_parking:
                            search_params["p_max_covered_parking"] = extracted_params.max_covered_parking
                        if extracted_params.min_balconies:
                            search_params["p_min_balconies"] = extracted_params.min_balconies
                        if extracted_params.max_balconies:
                            search_params["p_max_balconies"] = extracted_params.max_balconies
                        
                        # INDUSTRIAL-GRADE: Advanced sorting and query type
                        if extracted_params.sort_by:
                            search_params["p_sort_by"] = extracted_params.sort_by
                        if extracted_params.query_type:
                            search_params["p_query_type"] = extracted_params.query_type
                        if intelligent_limit:
                            search_params["p_intelligent_limit"] = intelligent_limit

                        # Search parameters configured

                        # Execute the search with proper error handling
                        try:
                            response = self.supabase.rpc('hybrid_property_search', search_params).execute()
                            
                            if response.data and isinstance(response.data, list) and len(response.data) > 0:
                                all_results.extend(response.data)
                                logger.info(f"🔍 SEARCH_RESULT: Found {len(response.data)} properties for {property_type or 'Any'}/{sale_or_rent or 'Any'}")
                        except Exception as search_error:
                            logger.warning(f"⚠️ Search failed: {str(search_error)}")
                            continue

            # Remove duplicates based on ID (exact match to TypeScript)
            unique_results = []
            seen_ids = set()
            for result in all_results:
                if result.get('id') not in seen_ids:
                    # Handle the address field properly
                    result_data = result.copy()
                    if 'number_of_balconies' in result_data:
                        result_data['balconies'] = result_data.get('number_of_balconies')
                    if 'covered_parking_spaces' in result_data:
                        result_data['covered_parking'] = result_data.get('covered_parking_spaces')
                    if 'rrf_score' in result_data:
                        result_data['search_rank'] = result_data.get('rrf_score')
                    
                    # Ensure original_property_id is included for carousel broadcast
                    # The database should already return this field from the hybrid_property_search function
                    
                    # FIX: Parse address field if it's a string
                    if 'address' in result_data and result_data['address']:
                        address_value = result_data['address']
                        if isinstance(address_value, str):
                            try:
                                # Parse the string representation of JSON into actual dict
                                result_data['address'] = json.loads(address_value)
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.warning(f"Failed to parse address JSON for property {result.get('id', 'unknown')}: {str(e)}")
                                # Try to parse it as a Python literal (eval is dangerous but controlled here)
                                try:
                                    import ast
                                    result_data['address'] = ast.literal_eval(address_value)
                                except (ValueError, SyntaxError) as e2:
                                    logger.warning(f"Failed to parse address literal for property {result.get('id', 'unknown')}: {str(e2)}")
                                    # Set to None if all parsing fails
                                    result_data['address'] = None
                    
                    try:
                        unique_results.append(PropertyResult(**result_data))
                        seen_ids.add(result.get('id'))
                    except Exception as validation_error:
                        logger.error(f"Failed to create PropertyResult for {result.get('id', 'unknown')}: {str(validation_error)}")
                        # Log the problematic data for debugging
                        logger.debug(f"Problematic result data: {json.dumps(result_data, indent=2, default=str)}")
                        continue

            query_execution_time = (time.time() - execution_start) * 1000
            logger.info(f"🔍 SEARCH_RESULTS: {len(unique_results)} properties found ({query_execution_time:.0f}ms)")
            
            # PERFORMANCE MONITORING - only log if slow
            if query_execution_time > 8000:
                logger.warning(f"⚠️ SLOW_QUERY: {query_execution_time:.0f}ms (target: <5000ms)")

            # Log results summary for tracking
            if unique_results and len(unique_results) > 0:
                # Just log count and basic info for flow tracking
                sample_prop = unique_results[0]
                locality = sample_prop.address.get('locality') if sample_prop.address else None
                logger.info(f"🏠 RESULTS_PREVIEW: {sample_prop.property_type} in {locality or 'Unknown'} (+ {len(unique_results)-1} more)")

            # Calculate industrial features used
            industrial_features = {
                "negative_filtering": any(getattr(extracted_params, k, None) for k in dir(extracted_params) if k.startswith('no_')),
                "sorting": bool(extracted_params.sort_by),
                "statistical_query": extracted_params.query_type == "statistical",
                "intelligent_limits": intelligent_limit,
                "multi_criteria_sorting": bool(extracted_params.sort_by and "_then_" in extracted_params.sort_by)
            }

            return unique_results, industrial_features
            
        except Exception as e:
            logger.error(f"❌ Industrial query execution failed: {str(e)}")
            return [], {
                "negative_filtering": False,
                "sorting": False,
                "statistical_query": False,
                "intelligent_limits": False,
                "multi_criteria_sorting": False
            }

    async def generate_answer(self, user_query: str, extracted_params: QueryParams, search_results: List[PropertyResult], industrial_features: Dict[str, bool]) -> str:
        """
        Industrial-grade answer generation - exact match to TypeScript
        """
        logger.info("💬 Step 3: Industrial-Grade Answer Generation")
        
        if not search_results:
            return self.generate_no_results_response(extracted_params, user_query, industrial_features)

        system_prompt = f"""You are an expert Dubai real estate consultant with INDUSTRIAL-GRADE capabilities. Generate a beautifully formatted, conversational response about the property search results.

🏭 INDUSTRIAL FEATURES USED:
- Negative Filtering: {'✅' if industrial_features['negative_filtering'] else '❌'}
- Advanced Sorting: {'✅' if industrial_features['sorting'] else '❌'}  
- Statistical Query: {'✅' if industrial_features['statistical_query'] else '❌'}
- Intelligent Limits: {'✅' if industrial_features['intelligent_limits'] else '❌'}
- Multi-Criteria Sorting: {'✅' if industrial_features['multi_criteria_sorting'] else '❌'}

📊 RESPONSE FORMATTING REQUIREMENTS:
- Start with an engaging summary (e.g., "🏠 **Found {len(search_results)} amazing properties for you!**")
- Use emojis for visual appeal (🏠 🏢 🏖️ 💰 📍 ✨ 🔍)
- Format prices clearly: "AED 2.5M" for sales, "AED 85,000/year" for rentals
- Group similar properties when showing multiple results
- Use bullet points or numbered lists for easy reading
- Add line breaks for better WhatsApp readability
- End with helpful next steps

📈 STATISTICAL QUERY HANDLING:
- For "average price" queries: Show clear statistics with context
- For "cheapest/most expensive" queries: Highlight the standout property
- For "largest/smallest" queries: Emphasize size and value proposition
- Always provide market insights and comparisons

🎯 FORMATTING GUIDELINES:
- Use **bold** for important information
- Keep lines short for mobile WhatsApp viewing
- Add spacing between property listings
- Mention industrial features used subtly
- Include practical next steps
- Be enthusiastic but professional
- Suggest refined searches when appropriate

User's original query: "{user_query}"
Search parameters: {json.dumps(extracted_params.dict(), indent=2)}
Found {len(search_results)} total properties."""

        results_text = ""
        for index, prop in enumerate(search_results[:10]):
            price = (f"AED {(prop.sale_price_aed / 1000000):.1f}M" if prop.sale_price_aed 
                    else f"AED {prop.rent_price_aed:,}/year" if prop.rent_price_aed
                    else "Price on request")
            
            features = []
            if prop.study:
                features.append('Study')
            if prop.maid_room:
                features.append('Maid room')
            if prop.park_pool_view:
                features.append('Pool/Park view')
            if prop.landscaped_garden:
                features.append('Garden')
            if prop.covered_parking:
                features.append(f'{prop.covered_parking} parking')
            
            locality = prop.address.get('locality') if prop.address else None
            city = prop.address.get('city') if prop.address else None
            location = locality or city or 'Location not specified'
            building = f" ({prop.building_name})" if prop.building_name else ""
            
            results_text += f"""**{index + 1}. {prop.property_type}** | {prop.bedrooms}BR • {prop.bathrooms}BA
📍 {location}{building}
💰 {price}
📐 {prop.bua_sqft} sqft{chr(10) + '✨ ' + ', '.join(features) if features else ''}
🔍 Ref: {prop.id[:8]}...

"""

        try:
            completion = await self.openai.chat.completions.create(
                model=self.config["model"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here are the search results:\n\n{results_text}\n\nPlease provide a helpful response highlighting the industrial features used."}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            answer = completion.choices[0].message.content or "I found some properties but encountered an issue generating the response."
            logger.info("✅ Industrial-grade answer generated")
            return answer
            
        except Exception as e:
            logger.error(f"❌ Answer generation failed: {str(e)}")
            return self.generate_fallback_response(search_results, industrial_features)

    def generate_no_results_response(self, search_params: QueryParams, original_query: str, industrial_features: Dict[str, bool]) -> str:
        """
        Generate no results response - exact match to TypeScript
        """
        criteria = []
        if search_params.property_type:
            prop_type = search_params.property_type
            if isinstance(prop_type, list):
                criteria.append(' or '.join(prop_type).lower())
            else:
                criteria.append(prop_type.lower())
        if search_params.bedrooms:
            criteria.append(f"{search_params.bedrooms} bedroom{'s' if search_params.bedrooms > 1 else ''}")
        if search_params.sale_or_rent:
            criteria.append(f"for {search_params.sale_or_rent}")
        if search_params.locality:
            locality = search_params.locality
            if isinstance(locality, list):
                criteria.append(f"in {' or '.join(locality)}")
            else:
                criteria.append(f"in {locality}")
        
        # Add negative criteria
        negative_criteria = []
        if search_params.no_maid_room:
            negative_criteria.append('WITHOUT maid room')
        if search_params.no_study:
            negative_criteria.append('WITHOUT study')
        if search_params.no_landscaped_garden:
            negative_criteria.append('WITHOUT garden')

        criteria_text = f" matching \"{', '.join(criteria)}\"" if criteria else ''
        negative_text = f" ({', '.join(negative_criteria)})" if negative_criteria else ''

        return f"""I couldn't find any properties{criteria_text}{negative_text} in our database. 

🏭 **Industrial Search Used:**
- Negative Filtering: {'✅ Active' if industrial_features['negative_filtering'] else '❌ Not used'}
- Advanced Sorting: {'✅ ' + search_params.sort_by if industrial_features['sorting'] and search_params.sort_by else '❌ Not used'}
- Multi-Criteria Sorting: {'✅ Active' if industrial_features['multi_criteria_sorting'] else '❌ Not used'}
- Statistical Query: {'✅ Active' if industrial_features['statistical_query'] else '❌ Not used'}

**Suggestions:**
• Try broadening your search criteria
• Remove specific negative filters (e.g., allow maid rooms)
• Check location spelling
• Consider nearby communities

Would you like me to search with different criteria?"""

    def generate_fallback_response(self, search_results: List[PropertyResult], industrial_features: Dict[str, bool]) -> str:
        """
        Generate fallback response - exact match to TypeScript
        """
        if not search_results:
            return f"I found {len(search_results)} properties but encountered an issue generating the full response. The search results are available in the context section."

        top_property = search_results[0]
        
        features = []
        if top_property.study:
            features.append('Study')
        if top_property.maid_room:
            features.append('Maid room')
        if top_property.park_pool_view:
            features.append('Pool/Park view')
        if top_property.landscaped_garden:
            features.append('Garden')
        
        price = (f"AED {(top_property.sale_price_aed / 1000000):.1f}M" if top_property.sale_price_aed
                else f"AED {top_property.rent_price_aed:,}/year" if top_property.rent_price_aed
                else "Price on request")
        
        locality = top_property.address.get('locality') if top_property.address else None
        city = top_property.address.get('city') if top_property.address else None
        location = locality or city or 'Location not specified'
        
        return f"""🏭 **Industrial Search Complete!** Found {len(search_results)} properties.

**🔧 Features Used:**
- Negative Filtering: {'✅' if industrial_features['negative_filtering'] else '❌'}
- Advanced Sorting: {'✅' if industrial_features['sorting'] else '❌'}
- Multi-Criteria Sorting: {'✅' if industrial_features['multi_criteria_sorting'] else '❌'}
- Intelligent Limits: {'✅' if industrial_features['intelligent_limits'] else '❌'}

**🏆 Top Result:**
📍 {top_property.property_type} - {top_property.bedrooms}BR/{top_property.bathrooms}BA
🏠 {location}
💰 {price}
📐 {top_property.bua_sqft} sqft
{f'✨ Features: {", ".join(features)}' if features else ''}

{f'Plus {len(search_results) - 1} more properties that match your criteria.' if len(search_results) > 1 else ''}

Would you like more details or shall I refine the search?""" 