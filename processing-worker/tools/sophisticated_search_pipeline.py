"""
🚀 SOPHISTICATED SEARCH PIPELINE
Industrial-grade search system with intelligent fallback strategies
Provides actionable alternatives when exact criteria don't match

Author: AI Assistant
Purpose: Transform dead-end "no results" into intelligent suggestions
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from supabase import create_client, Client
from dotenv import load_dotenv

from utils.logger import setup_logger

load_dotenv()
logger = setup_logger(__name__)


class SearchTier(Enum):
    """Search tier levels for fallback strategy"""
    EXACT_MATCH = "exact_match"
    SINGLE_CONSTRAINT_RELAXATION = "single_constraint_relaxation"
    MULTI_CONSTRAINT_RELAXATION = "multi_constraint_relaxation"
    MARKET_INTELLIGENCE = "market_intelligence"


@dataclass
class SearchCriteria:
    """Structured search criteria"""
    transaction_type: Optional[str] = None  # 'buy' or 'rent'
    location: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database queries"""
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass 
class SearchResult:
    """Search result with metadata"""
    properties: List[Dict[str, Any]]
    count: int
    tier: SearchTier
    strategy_used: str
    alternatives_found: Dict[str, Any]
    suggestions: List[str]
    execution_time_ms: float


@dataclass
class AlternativeAnalysis:
    """Analysis of alternative options available"""
    budget_alternatives: List[Dict[str, Any]]
    location_alternatives: List[Dict[str, Any]]  
    property_type_alternatives: List[Dict[str, Any]]
    bedroom_alternatives: List[Dict[str, Any]]
    market_insights: Dict[str, Any]


class SophisticatedSearchPipeline:
    """
    🎯 Industrial-grade search pipeline with intelligent fallback strategies
    
    Search Strategy:
    1. TIER 1: Exact match search
    2. TIER 2: Single constraint relaxation (budget, location, type, bedrooms)
    3. TIER 3: Multi-constraint relaxation 
    4. TIER 4: Market intelligence (what's actually available)
    """
    
    def __init__(self):
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if supabase_url and supabase_key:
            try:
                self.supabase: Client = create_client(supabase_url, supabase_key)
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.supabase = None
        else:
            logger.error("Supabase credentials not found")
            self.supabase = None
        
        # Location proximity mapping for intelligent location alternatives
        self.location_proximity = {
            'Dubai Marina': ['JBR', 'Dubai Marina', 'Marina', 'Emaar Beachfront', 'Al Sufouh'],
            'JBR': ['Dubai Marina', 'JBR', 'Marina', 'Emaar Beachfront'],
            'Downtown Dubai': ['Business Bay', 'DIFC', 'Downtown', 'Dubai Mall Area'],
            'Business Bay': ['Downtown Dubai', 'DIFC', 'Downtown', 'Business Bay'],
            'DIFC': ['Business Bay', 'Downtown Dubai', 'Trade Centre'],
            'Jumeirah Village Circle': ['JVC', 'Dubai Sports City', 'Motor City'],
            'Dubai Sports City': ['Motor City', 'JVC', 'Jumeirah Village Circle'],
            'Motor City': ['Dubai Sports City', 'JVC', 'Jumeirah Village Circle'],
            'Palm Jumeirah': ['Dubai Marina', 'JBR', 'Al Sufouh'],
            'City Walk': ['Downtown Dubai', 'Business Bay', 'Al Safa'],
            'Jumeirah Beach Residence': ['Dubai Marina', 'JBR', 'Marina'],
            'Al Barsha': ['Dubai Marina', 'JBR', 'Al Sufouh', 'Motor City'],
            # Add more mappings as needed
        }
        
        # Property type alternatives
        self.property_type_alternatives = {
            'Apartment': ['Apartment', 'Penthouse', 'Studio'],
            'Villa': ['Villa', 'Townhouse', 'Villa village'],
            'Penthouse': ['Penthouse', 'Apartment'],
            'Townhouse': ['Townhouse', 'Villa'],
            'Studio': ['Studio', 'Apartment'],
        }
        
        # Budget expansion ratios
        self.budget_expansion_steps = [1.15, 1.3, 1.5, 2.0]  # 15%, 30%, 50%, 100% increases
        
    async def search_with_intelligence(self, criteria: SearchCriteria, limit: int = 15) -> SearchResult:
        """
        🧠 Main intelligent search method with multi-tier fallback strategy
        """
        start_time = time.time()
        
        logger.info(f"🔍 Starting sophisticated search with criteria: {criteria.to_dict()}")
        
        # TIER 1: Exact Match Search
        exact_results = await self._execute_exact_search(criteria, limit)
        if exact_results.count > 0:
            execution_time = (time.time() - start_time) * 1000
            exact_results.execution_time_ms = execution_time
            logger.info(f"✅ TIER 1 SUCCESS: Found {exact_results.count} exact matches in {execution_time:.0f}ms")
            return exact_results
        
        logger.info("🎯 TIER 1 FAILED: No exact matches, proceeding to intelligent alternatives...")
        
        # TIER 2: Single Constraint Relaxation
        alternative_results = await self._execute_alternative_search(criteria, limit)
        if alternative_results.count > 0:
            execution_time = (time.time() - start_time) * 1000
            alternative_results.execution_time_ms = execution_time
            logger.info(f"✅ TIER 2 SUCCESS: Found alternatives in {execution_time:.0f}ms")
            return alternative_results
        
        # TIER 3: Multi-Constraint Relaxation  
        logger.info("🎯 TIER 2 FAILED: Proceeding to multi-constraint relaxation...")
        multi_results = await self._execute_multi_constraint_search(criteria, limit)
        if multi_results.count > 0:
            execution_time = (time.time() - start_time) * 1000
            multi_results.execution_time_ms = execution_time
            logger.info(f"✅ TIER 3 SUCCESS: Found multi-constraint alternatives in {execution_time:.0f}ms")
            return multi_results
        
        # TIER 4: Market Intelligence (Always returns something)
        logger.info("🎯 TIER 3 FAILED: Providing market intelligence...")
        market_results = await self._execute_market_intelligence(criteria, limit)
        execution_time = (time.time() - start_time) * 1000
        market_results.execution_time_ms = execution_time
        logger.info(f"✅ TIER 4 COMPLETE: Market intelligence provided in {execution_time:.0f}ms")
        
        return market_results
    
    async def _execute_exact_search(self, criteria: SearchCriteria, limit: int) -> SearchResult:
        """Execute exact match search"""
        try:
            query = self.supabase.from_('property_vectorstore').select(
                'id, original_property_id, property_type, sale_or_rent, bedrooms, bathrooms, '
                'sale_price_aed, rent_price_aed, bua_sqft, address, building_name, '
                'study, maid_room, park_pool_view, landscaped_garden, covered_parking_spaces'
            )
            
            # Apply all criteria filters
            query = self._apply_criteria_filters(query, criteria)
            
            response = query.limit(limit).execute()
            properties = response.data if response.data else []
            
            return SearchResult(
                properties=properties,
                count=len(properties),
                tier=SearchTier.EXACT_MATCH,
                strategy_used="exact_match",
                alternatives_found={},
                suggestions=[],
                execution_time_ms=0
            )
            
        except Exception as e:
            logger.error(f"❌ Exact search failed: {e}")
            return SearchResult([], 0, SearchTier.EXACT_MATCH, "exact_match_failed", {}, [], 0)
    
    async def _execute_alternative_search(self, criteria: SearchCriteria, limit: int) -> SearchResult:
        """
        🔄 Execute single-constraint relaxation search
        Try relaxing one constraint at a time to find alternatives
        """
        alternatives_found = {}
        all_suggestions = []
        best_alternative = None
        best_count = 0
        
        # Strategy 1: Budget Expansion
        if criteria.budget_min or criteria.budget_max:
            budget_alternatives = await self._find_budget_alternatives(criteria, limit)
            if budget_alternatives['properties']:
                alternatives_found['budget'] = budget_alternatives
                if len(budget_alternatives['properties']) > best_count:
                    best_alternative = budget_alternatives
                    best_count = len(budget_alternatives['properties'])
                all_suggestions.extend(budget_alternatives['suggestions'])
        
        # Strategy 2: Location Alternatives  
        if criteria.location:
            location_alternatives = await self._find_location_alternatives(criteria, limit)
            if location_alternatives['properties']:
                alternatives_found['location'] = location_alternatives
                if len(location_alternatives['properties']) > best_count:
                    best_alternative = location_alternatives
                    best_count = len(location_alternatives['properties'])
                all_suggestions.extend(location_alternatives['suggestions'])
        
        # Strategy 3: Property Type Alternatives
        if criteria.property_type:
            type_alternatives = await self._find_property_type_alternatives(criteria, limit)
            if type_alternatives['properties']:
                alternatives_found['property_type'] = type_alternatives
                if len(type_alternatives['properties']) > best_count:
                    best_alternative = type_alternatives
                    best_count = len(type_alternatives['properties'])
                all_suggestions.extend(type_alternatives['suggestions'])
        
        # Strategy 4: Bedroom Alternatives
        if criteria.bedrooms is not None:
            bedroom_alternatives = await self._find_bedroom_alternatives(criteria, limit)
            if bedroom_alternatives['properties']:
                alternatives_found['bedrooms'] = bedroom_alternatives
                if len(bedroom_alternatives['properties']) > best_count:
                    best_alternative = bedroom_alternatives
                    best_count = len(bedroom_alternatives['properties'])
                all_suggestions.extend(bedroom_alternatives['suggestions'])
        
        # Return best alternative if found
        if best_alternative:
            return SearchResult(
                properties=best_alternative['properties'],
                count=len(best_alternative['properties']),
                tier=SearchTier.SINGLE_CONSTRAINT_RELAXATION,
                strategy_used=best_alternative['strategy'],
                alternatives_found=alternatives_found,
                suggestions=all_suggestions,
                execution_time_ms=0
            )
        
        return SearchResult([], 0, SearchTier.SINGLE_CONSTRAINT_RELAXATION, "no_alternatives", alternatives_found, all_suggestions, 0)
    
    async def _execute_multi_constraint_search(self, criteria: SearchCriteria, limit: int) -> SearchResult:
        """
        🔄🔄 Execute multi-constraint relaxation
        Try relaxing multiple constraints together
        """
        multi_alternatives = {}
        suggestions = []
        
        # Strategy 1: Budget + Location relaxation
        if (criteria.budget_min or criteria.budget_max) and criteria.location:
            relaxed_criteria = SearchCriteria(
                transaction_type=criteria.transaction_type,
                property_type=criteria.property_type,
                bedrooms=criteria.bedrooms
                # Removed budget and location constraints
            )
            
            properties = await self._execute_exact_search(relaxed_criteria, limit * 2)
            if properties.count > 0:
                # Analyze what locations and budgets are available
                analysis = self._analyze_available_options(properties.properties, criteria)
                multi_alternatives['budget_location'] = {
                    'properties': properties.properties[:limit],
                    'analysis': analysis,
                    'strategy': 'budget_location_relaxation'
                }
                suggestions.append(f"Found {properties.count} properties when removing location and budget restrictions")
        
        # Strategy 2: Type + Budget relaxation  
        if criteria.property_type and (criteria.budget_min or criteria.budget_max):
            relaxed_criteria = SearchCriteria(
                transaction_type=criteria.transaction_type,
                location=criteria.location,
                bedrooms=criteria.bedrooms
                # Removed property_type and budget constraints
            )
            
            properties = await self._execute_exact_search(relaxed_criteria, limit * 2)
            if properties.count > 0:
                analysis = self._analyze_available_options(properties.properties, criteria)
                multi_alternatives['type_budget'] = {
                    'properties': properties.properties[:limit],
                    'analysis': analysis,
                    'strategy': 'type_budget_relaxation'
                }
                suggestions.append(f"Found {properties.count} properties when removing property type and budget restrictions")
        
        # Return best multi-constraint alternative
        if multi_alternatives:
            best_key = max(multi_alternatives.keys(), key=lambda k: len(multi_alternatives[k]['properties']))
            best_alternative = multi_alternatives[best_key]
            
            return SearchResult(
                properties=best_alternative['properties'],
                count=len(best_alternative['properties']),
                tier=SearchTier.MULTI_CONSTRAINT_RELAXATION,
                strategy_used=best_alternative['strategy'],
                alternatives_found=multi_alternatives,
                suggestions=suggestions,
                execution_time_ms=0
            )
        
        return SearchResult([], 0, SearchTier.MULTI_CONSTRAINT_RELAXATION, "no_multi_alternatives", {}, [], 0)
    
    async def _execute_market_intelligence(self, criteria: SearchCriteria, limit: int) -> SearchResult:
        """
        📊 Execute market intelligence analysis
        Provide insights about what's actually available in the market
        """
        market_insights = {}
        suggestions = []
        sample_properties = []
        
        try:
            # Get overall market data
            base_query = self.supabase.from_('property_vectorstore').select(
                'id, property_type, sale_or_rent, bedrooms, bathrooms, '
                'sale_price_aed, rent_price_aed, address, building_name'
            )
            
            # Apply only transaction type filter to get market overview
            if criteria.transaction_type:
                sale_or_rent = 'sale' if criteria.transaction_type == 'buy' else 'rent'
                base_query = base_query.eq('sale_or_rent', sale_or_rent)
            
            market_data = base_query.limit(1000).execute()  # Get larger sample for analysis
            
            if market_data.data:
                # Analyze market by location
                if criteria.location:
                    market_insights['location_analysis'] = self._analyze_location_market(market_data.data, criteria.location)
                
                # Analyze market by budget
                if criteria.budget_min or criteria.budget_max:
                    market_insights['budget_analysis'] = self._analyze_budget_market(market_data.data, criteria)
                
                # Analyze market by property type
                if criteria.property_type:
                    market_insights['property_type_analysis'] = self._analyze_property_type_market(market_data.data, criteria.property_type)
                
                # Generate actionable suggestions
                suggestions = self._generate_market_suggestions(market_insights, criteria)
                
                # Get sample properties to show (best available options)
                sample_properties = market_data.data[:limit]
                
            return SearchResult(
                properties=sample_properties,
                count=len(sample_properties),
                tier=SearchTier.MARKET_INTELLIGENCE,
                strategy_used="market_intelligence",
                alternatives_found=market_insights,
                suggestions=suggestions,
                execution_time_ms=0
            )
            
        except Exception as e:
            logger.error(f"❌ Market intelligence failed: {e}")
            return SearchResult(
                properties=[],
                count=0,
                tier=SearchTier.MARKET_INTELLIGENCE,
                strategy_used="market_intelligence_failed",
                alternatives_found={},
                suggestions=["Unable to analyze market data. Please try a broader search."],
                execution_time_ms=0
            )
    
    async def _find_budget_alternatives(self, criteria: SearchCriteria, limit: int) -> Dict[str, Any]:
        """Find properties with expanded budget range"""
        alternatives = []
        suggestions = []
        
        for expansion_ratio in self.budget_expansion_steps:
            expanded_criteria = SearchCriteria(
                transaction_type=criteria.transaction_type,
                location=criteria.location,
                property_type=criteria.property_type,
                bedrooms=criteria.bedrooms,
                budget_min=criteria.budget_min,
                budget_max=int(criteria.budget_max * expansion_ratio) if criteria.budget_max else None
            )
            
            results = await self._execute_exact_search(expanded_criteria, limit)
            if results.count > 0:
                original_max = criteria.budget_max or criteria.budget_min
                new_max = expanded_criteria.budget_max
                price_diff = new_max - original_max
                
                suggestions.append(
                    f"Found {results.count} properties if you increase budget by {price_diff:,} AED "
                    f"(to {new_max:,} AED total)"
                )
                alternatives.extend(results.properties)
                break  # Return first successful expansion
        
        return {
            'properties': alternatives[:limit],
            'suggestions': suggestions,
            'strategy': 'budget_expansion'
        }
    
    async def _find_location_alternatives(self, criteria: SearchCriteria, limit: int) -> Dict[str, Any]:
        """Find properties in alternative locations"""
        alternatives = []
        suggestions = []
        
        # Get nearby locations
        nearby_locations = self.location_proximity.get(criteria.location, [])
        
        for location in nearby_locations:
            if location == criteria.location:
                continue  # Skip original location
                
            alt_criteria = SearchCriteria(
                transaction_type=criteria.transaction_type,
                location=location,
                budget_min=criteria.budget_min,
                budget_max=criteria.budget_max,
                property_type=criteria.property_type,
                bedrooms=criteria.bedrooms
            )
            
            results = await self._execute_exact_search(alt_criteria, limit)
            if results.count > 0:
                suggestions.append(f"Found {results.count} properties in {location} (near {criteria.location})")
                alternatives.extend(results.properties)
        
        return {
            'properties': alternatives[:limit],
            'suggestions': suggestions,
            'strategy': 'location_alternatives'
        }
    
    async def _find_property_type_alternatives(self, criteria: SearchCriteria, limit: int) -> Dict[str, Any]:
        """Find properties with alternative property types"""
        alternatives = []
        suggestions = []
        
        alt_types = self.property_type_alternatives.get(criteria.property_type, [])
        
        for prop_type in alt_types:
            if prop_type == criteria.property_type:
                continue
                
            alt_criteria = SearchCriteria(
                transaction_type=criteria.transaction_type,
                location=criteria.location,
                budget_min=criteria.budget_min,
                budget_max=criteria.budget_max,
                property_type=prop_type,
                bedrooms=criteria.bedrooms
            )
            
            results = await self._execute_exact_search(alt_criteria, limit)
            if results.count > 0:
                suggestions.append(f"Found {results.count} {prop_type}s (instead of {criteria.property_type})")
                alternatives.extend(results.properties)
        
        return {
            'properties': alternatives[:limit],
            'suggestions': suggestions,
            'strategy': 'property_type_alternatives'
        }
    
    async def _find_bedroom_alternatives(self, criteria: SearchCriteria, limit: int) -> Dict[str, Any]:
        """Find properties with alternative bedroom counts"""
        alternatives = []
        suggestions = []
        
        # Try +/- 1 bedroom
        bedroom_alternatives = [criteria.bedrooms - 1, criteria.bedrooms + 1]
        
        for bedroom_count in bedroom_alternatives:
            if bedroom_count < 0:
                continue
                
            alt_criteria = SearchCriteria(
                transaction_type=criteria.transaction_type,
                location=criteria.location,
                budget_min=criteria.budget_min,
                budget_max=criteria.budget_max,
                property_type=criteria.property_type,
                bedrooms=bedroom_count
            )
            
            results = await self._execute_exact_search(alt_criteria, limit)
            if results.count > 0:
                suggestions.append(f"Found {results.count} properties with {bedroom_count} bedrooms (instead of {criteria.bedrooms})")
                alternatives.extend(results.properties)
        
        return {
            'properties': alternatives[:limit],
            'suggestions': suggestions,
            'strategy': 'bedroom_alternatives'
        }
    
    def _apply_criteria_filters(self, query, criteria: SearchCriteria):
        """Apply search criteria filters to Supabase query"""
        if criteria.transaction_type:
            sale_or_rent = 'sale' if criteria.transaction_type == 'buy' else 'rent'
            query = query.eq('sale_or_rent', sale_or_rent)
        
        if criteria.location:
            # Handle location search - try exact match and partial match
            query = query.or_(
                f"address->>locality.ilike.%{criteria.location}%,"
                f"building_name.ilike.%{criteria.location}%"
            )
        
        if criteria.property_type:
            query = query.eq('property_type', criteria.property_type)
        
        if criteria.bedrooms is not None:
            query = query.eq('bedrooms', criteria.bedrooms)
        
        if criteria.budget_min:
            if criteria.transaction_type == 'rent':
                query = query.gte('rent_price_aed', criteria.budget_min)
            else:
                query = query.gte('sale_price_aed', criteria.budget_min)
        
        if criteria.budget_max:
            if criteria.transaction_type == 'rent':
                query = query.lte('rent_price_aed', criteria.budget_max)
            else:
                query = query.lte('sale_price_aed', criteria.budget_max)
        
        return query
    
    def _analyze_available_options(self, properties: List[Dict], original_criteria: SearchCriteria) -> Dict[str, Any]:
        """Analyze what options are actually available in the results"""
        analysis = {
            'locations': {},
            'price_ranges': {},
            'property_types': {},
            'bedroom_counts': {}
        }
        
        for prop in properties:
            # Analyze locations
            address = prop.get('address', {})
            if isinstance(address, str):
                try:
                    address = json.loads(address)
                except:
                    address = {}
            
            locality = address.get('locality', 'Unknown')
            analysis['locations'][locality] = analysis['locations'].get(locality, 0) + 1
            
            # Analyze property types
            prop_type = prop.get('property_type', 'Unknown')
            analysis['property_types'][prop_type] = analysis['property_types'].get(prop_type, 0) + 1
            
            # Analyze bedroom counts
            bedrooms = prop.get('bedrooms', 0)
            analysis['bedroom_counts'][bedrooms] = analysis['bedroom_counts'].get(bedrooms, 0) + 1
            
            # Analyze price ranges
            price = prop.get('sale_price_aed') or prop.get('rent_price_aed', 0)
            if price:
                price_range = self._get_price_range(price)
                analysis['price_ranges'][price_range] = analysis['price_ranges'].get(price_range, 0) + 1
        
        return analysis
    
    def _analyze_location_market(self, market_data: List[Dict], target_location: str) -> Dict[str, Any]:
        """Analyze market data for specific location"""
        location_count = 0
        total_properties = len(market_data)
        available_locations = {}
        
        for prop in market_data:
            address = prop.get('address', {})
            if isinstance(address, str):
                try:
                    address = json.loads(address)
                except:
                    address = {}
            
            locality = address.get('locality', 'Unknown')
            available_locations[locality] = available_locations.get(locality, 0) + 1
            
            if target_location.lower() in locality.lower():
                location_count += 1
        
        return {
            'target_location_count': location_count,
            'total_properties': total_properties,
            'available_locations': dict(sorted(available_locations.items(), key=lambda x: x[1], reverse=True)[:10]),
            'location_availability_percentage': (location_count / total_properties * 100) if total_properties > 0 else 0
        }
    
    def _analyze_budget_market(self, market_data: List[Dict], criteria: SearchCriteria) -> Dict[str, Any]:
        """Analyze market data for budget ranges"""
        price_field = 'rent_price_aed' if criteria.transaction_type == 'rent' else 'sale_price_aed'
        target_min = criteria.budget_min or 0
        target_max = criteria.budget_max or float('inf')
        
        in_budget_count = 0
        total_with_prices = 0
        price_distribution = {}
        
        for prop in market_data:
            price = prop.get(price_field)
            if price:
                total_with_prices += 1
                if target_min <= price <= target_max:
                    in_budget_count += 1
                
                price_range = self._get_price_range(price)
                price_distribution[price_range] = price_distribution.get(price_range, 0) + 1
        
        return {
            'in_budget_count': in_budget_count,
            'total_with_prices': total_with_prices,
            'budget_availability_percentage': (in_budget_count / total_with_prices * 100) if total_with_prices > 0 else 0,
            'price_distribution': dict(sorted(price_distribution.items())),
            'target_budget_range': f"{target_min:,} - {target_max:,}" if target_max != float('inf') else f"{target_min:,}+"
        }
    
    def _analyze_property_type_market(self, market_data: List[Dict], target_type: str) -> Dict[str, Any]:
        """Analyze market data for property types"""
        type_count = 0
        total_properties = len(market_data)
        type_distribution = {}
        
        for prop in market_data:
            prop_type = prop.get('property_type', 'Unknown')
            type_distribution[prop_type] = type_distribution.get(prop_type, 0) + 1
            
            if target_type.lower() in prop_type.lower():
                type_count += 1
        
        return {
            'target_type_count': type_count,
            'total_properties': total_properties,
            'type_distribution': dict(sorted(type_distribution.items(), key=lambda x: x[1], reverse=True)),
            'type_availability_percentage': (type_count / total_properties * 100) if total_properties > 0 else 0
        }
    
    def _get_price_range(self, price: int) -> str:
        """Get price range bucket for analysis"""
        if price < 50000:
            return "Under 50k"
        elif price < 100000:
            return "50k-100k"
        elif price < 200000:
            return "100k-200k"
        elif price < 500000:
            return "200k-500k"
        elif price < 1000000:
            return "500k-1M"
        elif price < 2000000:
            return "1M-2M"
        elif price < 5000000:
            return "2M-5M"
        else:
            return "5M+"
    
    def _generate_market_suggestions(self, market_insights: Dict[str, Any], criteria: SearchCriteria) -> List[str]:
        """Generate actionable suggestions based on market analysis"""
        suggestions = []
        
        # Location suggestions
        if 'location_analysis' in market_insights:
            analysis = market_insights['location_analysis']
            if analysis['target_location_count'] == 0:
                top_locations = list(analysis['available_locations'].keys())[:3]
                suggestions.append(f"No properties found in {criteria.location}. Try searching in: {', '.join(top_locations)}")
            elif analysis['location_availability_percentage'] < 5:
                suggestions.append(f"Very limited options in {criteria.location} ({analysis['target_location_count']} properties). Consider nearby areas.")
        
        # Budget suggestions
        if 'budget_analysis' in market_insights:
            analysis = market_insights['budget_analysis']
            if analysis['in_budget_count'] == 0:
                suggestions.append(f"No properties found in your budget range. Consider adjusting your budget based on available price ranges.")
            elif analysis['budget_availability_percentage'] < 10:
                suggestions.append(f"Limited options in your budget ({analysis['in_budget_count']} properties). Consider expanding your budget slightly.")
        
        # Property type suggestions
        if 'property_type_analysis' in market_insights:
            analysis = market_insights['property_type_analysis']
            if analysis['target_type_count'] == 0:
                top_types = list(analysis['type_distribution'].keys())[:3]
                suggestions.append(f"No {criteria.property_type}s found. Available types: {', '.join(top_types)}")
        
        if not suggestions:
            suggestions.append("Try adjusting your search criteria for more options.")
        
        return suggestions


# Global instance for easy import
sophisticated_search_pipeline = SophisticatedSearchPipeline()


async def search_with_sophisticated_intelligence(
    transaction_type: str = None,
    location: str = None,
    budget_min: int = None,
    budget_max: int = None,
    property_type: str = None,
    bedrooms: int = None,
    limit: int = 15
) -> SearchResult:
    """
    🚀 Public interface for sophisticated search
    
    Args:
        transaction_type: 'buy' or 'rent'
        location: Location name (e.g., 'Dubai Marina')
        budget_min: Minimum budget in AED
        budget_max: Maximum budget in AED
        property_type: Property type (e.g., 'Apartment', 'Villa')
        bedrooms: Number of bedrooms
        limit: Maximum number of results to return
    
    Returns:
        SearchResult with properties and intelligent suggestions
    """
    criteria = SearchCriteria(
        transaction_type=transaction_type,
        location=location,
        budget_min=budget_min,
        budget_max=budget_max,
        property_type=property_type,
        bedrooms=bedrooms
    )
    
    return await sophisticated_search_pipeline.search_with_intelligence(criteria, limit)


# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test_sophisticated_search():
        print("🧪 TESTING SOPHISTICATED SEARCH PIPELINE")
        print("=" * 60)
        
        # Test case: Specific search that likely won't have exact matches
        result = await search_with_sophisticated_intelligence(
            transaction_type='rent',
            location='Dubai Marina',
            budget_min=50000,
            budget_max=80000,
            property_type='Apartment',
            bedrooms=2,
            limit=5
        )
        
        print(f"🎯 Search Tier: {result.tier.value}")
        print(f"📊 Strategy Used: {result.strategy_used}")
        print(f"🏠 Properties Found: {result.count}")
        print(f"⏱️ Execution Time: {result.execution_time_ms:.0f}ms")
        print(f"💡 Suggestions:")
        for suggestion in result.suggestions:
            print(f"   • {suggestion}")
        
        if result.alternatives_found:
            print(f"🔍 Alternatives Analysis:")
            for key, value in result.alternatives_found.items():
                print(f"   {key}: {len(value.get('properties', []))} properties")
    
    asyncio.run(test_sophisticated_search())
