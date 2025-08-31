"""
🧪 COMPREHENSIVE TEST SUITE FOR SOPHISTICATED SEARCH PIPELINE
Tests all search tiers, fallback strategies, and edge cases

Author: AI Assistant
Purpose: Ensure sophisticated search works correctly in all scenarios
"""

import asyncio
import pytest
import time
from typing import Dict, Any, List

from tools.sophisticated_search_pipeline import (
    SophisticatedSearchPipeline,
    SearchCriteria,
    SearchTier,
    search_with_sophisticated_intelligence
)
from tools.sophisticated_response_generator import generate_sophisticated_response
from unified_conversation_engine import unified_engine


class TestSophisticatedSearchPipeline:
    """Test suite for sophisticated search pipeline"""
    
    @pytest.fixture
    def search_pipeline(self):
        """Create search pipeline instance for testing"""
        return SophisticatedSearchPipeline()
    
    async def test_exact_match_scenario(self, search_pipeline):
        """Test when exact matches are found"""
        print("\n🧪 TEST 1: Exact Match Scenario")
        
        # Create criteria that should have exact matches
        criteria = SearchCriteria(
            transaction_type='rent',
            location='Dubai Marina',
            budget_min=50000,
            budget_max=150000,
            property_type='Apartment',
            bedrooms=1
        )
        
        result = await search_pipeline.search_with_intelligence(criteria)
        
        print(f"   ✅ Tier: {result.tier.value}")
        print(f"   ✅ Properties found: {result.count}")
        print(f"   ✅ Strategy: {result.strategy_used}")
        print(f"   ✅ Execution time: {result.execution_time_ms:.0f}ms")
        
        assert result.tier == SearchTier.EXACT_MATCH or result.count > 0
        assert result.execution_time_ms < 5000  # Should be under 5 seconds
    
    async def test_budget_expansion_scenario(self):
        """Test budget expansion fallback"""
        print("\n🧪 TEST 2: Budget Expansion Scenario")
        
        # Create criteria with very tight budget that likely won't have exact matches
        criteria = SearchCriteria(
            transaction_type='rent',
            location='Dubai Marina',
            budget_min=10000,
            budget_max=15000,  # Very low budget
            property_type='Apartment',
            bedrooms=2
        )
        
        result = await search_with_sophisticated_intelligence(
            transaction_type='rent',
            location='Dubai Marina',
            budget_min=10000,
            budget_max=15000,
            property_type='Apartment',
            bedrooms=2
        )
        
        print(f"   ✅ Tier: {result.tier.value}")
        print(f"   ✅ Properties found: {result.count}")
        print(f"   ✅ Strategy: {result.strategy_used}")
        print(f"   ✅ Alternatives found: {list(result.alternatives_found.keys())}")
        print(f"   ✅ Suggestions: {len(result.suggestions)}")
        
        # Should find budget alternatives or market intelligence
        assert result.tier in [SearchTier.SINGLE_CONSTRAINT_RELAXATION, SearchTier.MARKET_INTELLIGENCE]
        assert len(result.suggestions) > 0
    
    async def test_location_alternatives_scenario(self):
        """Test location alternatives fallback"""
        print("\n🧪 TEST 3: Location Alternatives Scenario")
        
        # Search in very specific/rare location
        criteria = SearchCriteria(
            transaction_type='buy',
            location='Rare Location Dubai',  # Non-existent location
            budget_min=1000000,
            budget_max=3000000,
            property_type='Villa'
        )
        
        result = await search_with_sophisticated_intelligence(
            transaction_type='buy',
            location='Rare Location Dubai',
            budget_min=1000000,
            budget_max=3000000,
            property_type='Villa'
        )
        
        print(f"   ✅ Tier: {result.tier.value}")
        print(f"   ✅ Properties found: {result.count}")
        print(f"   ✅ Strategy: {result.strategy_used}")
        print(f"   ✅ Alternatives found: {list(result.alternatives_found.keys())}")
        
        # Should provide alternatives or market intelligence
        assert result.tier != SearchTier.EXACT_MATCH
        assert len(result.suggestions) > 0
    
    async def test_property_type_alternatives_scenario(self):
        """Test property type alternatives"""
        print("\n🧪 TEST 4: Property Type Alternatives Scenario")
        
        # Search for very specific property type
        criteria = SearchCriteria(
            transaction_type='rent',
            location='Downtown Dubai',
            budget_min=100000,
            budget_max=200000,
            property_type='Castle',  # Non-existent property type
            bedrooms=3
        )
        
        result = await search_with_sophisticated_intelligence(
            transaction_type='rent',
            location='Downtown Dubai',
            budget_min=100000,
            budget_max=200000,
            property_type='Castle',
            bedrooms=3
        )
        
        print(f"   ✅ Tier: {result.tier.value}")
        print(f"   ✅ Strategy: {result.strategy_used}")
        print(f"   ✅ Suggestions count: {len(result.suggestions)}")
        
        # Should provide intelligent fallback
        assert result.tier in [SearchTier.SINGLE_CONSTRAINT_RELAXATION, SearchTier.MULTI_CONSTRAINT_RELAXATION, SearchTier.MARKET_INTELLIGENCE]
        assert len(result.suggestions) > 0
    
    async def test_market_intelligence_scenario(self):
        """Test market intelligence when nothing matches"""
        print("\n🧪 TEST 5: Market Intelligence Scenario")
        
        # Create impossible criteria
        criteria = SearchCriteria(
            transaction_type='buy',
            location='Impossible Location',
            budget_min=1,
            budget_max=10,  # Impossibly low budget
            property_type='Spaceship',
            bedrooms=100
        )
        
        result = await search_with_sophisticated_intelligence(
            transaction_type='buy',
            location='Impossible Location',
            budget_min=1,
            budget_max=10,
            property_type='Spaceship',
            bedrooms=100
        )
        
        print(f"   ✅ Tier: {result.tier.value}")
        print(f"   ✅ Strategy: {result.strategy_used}")
        print(f"   ✅ Market insights: {list(result.alternatives_found.keys())}")
        print(f"   ✅ Suggestions: {len(result.suggestions)}")
        
        # Should provide market intelligence
        assert result.tier == SearchTier.MARKET_INTELLIGENCE
        assert len(result.suggestions) > 0
    
    async def test_response_generation(self):
        """Test sophisticated response generation"""
        print("\n🧪 TEST 6: Response Generation")
        
        criteria = SearchCriteria(
            transaction_type='rent',
            location='Dubai Marina',
            budget_min=80000,
            budget_max=120000,
            property_type='Apartment',
            bedrooms=2
        )
        
        search_result = await search_with_sophisticated_intelligence(
            transaction_type='rent',
            location='Dubai Marina',
            budget_min=80000,
            budget_max=120000,
            property_type='Apartment',
            bedrooms=2
        )
        
        # Generate response
        response = generate_sophisticated_response(search_result, criteria)
        
        print(f"   ✅ Response generated: {len(response)} characters")
        print(f"   ✅ Contains search summary: {'looking to rent' in response}")
        print(f"   ✅ Contains actionable prompts: {'Tell me about property' in response or 'Book viewing' in response}")
        
        assert len(response) > 100  # Should be substantial
        assert 'rent' in response.lower()
        assert 'marina' in response.lower()
        assert '2BR' in response or '2br' in response.lower()
    
    async def test_conversation_engine_integration(self):
        """Test integration with unified conversation engine"""
        print("\n🧪 TEST 7: Conversation Engine Integration")
        
        criteria_dict = {
            'transaction_type': 'rent',
            'location': 'JBR',
            'budget_min': 70000,
            'budget_max': 100000,
            'property_type': 'Apartment',
            'bedrooms': 1
        }
        
        # Test the integration method
        response, properties = await unified_engine.execute_sophisticated_search_and_respond(criteria_dict)
        
        print(f"   ✅ Response generated: {len(response)} characters")
        print(f"   ✅ Properties returned: {len(properties)}")
        print(f"   ✅ Response contains criteria: {'rent' in response.lower() and 'jbr' in response.lower()}")
        
        assert len(response) > 50
        assert isinstance(properties, list)
    
    async def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        print("\n🧪 TEST 8: Performance Benchmarks")
        
        test_scenarios = [
            # Scenario 1: Exact match (should be fastest)
            {
                'name': 'Exact Match',
                'criteria': SearchCriteria(
                    transaction_type='rent',
                    property_type='Apartment',
                    bedrooms=1
                )
            },
            # Scenario 2: Single constraint relaxation
            {
                'name': 'Budget Expansion',
                'criteria': SearchCriteria(
                    transaction_type='rent',
                    location='Dubai Marina',
                    budget_min=5000,
                    budget_max=8000,
                    property_type='Apartment'
                )
            },
            # Scenario 3: Market intelligence
            {
                'name': 'Market Intelligence',
                'criteria': SearchCriteria(
                    transaction_type='buy',
                    location='Nonexistent Location',
                    budget_min=1,
                    budget_max=5,
                    property_type='Impossible Type'
                )
            }
        ]
        
        for scenario in test_scenarios:
            start_time = time.time()
            result = await search_with_sophisticated_intelligence(**scenario['criteria'].to_dict())
            execution_time = (time.time() - start_time) * 1000
            
            print(f"   ✅ {scenario['name']}: {execution_time:.0f}ms (DB: {result.execution_time_ms:.0f}ms)")
            
            # Performance assertions
            assert execution_time < 10000  # Should complete within 10 seconds
            assert result.execution_time_ms < 8000  # Database operations should be under 8 seconds


async def run_comprehensive_tests():
    """Run all comprehensive tests"""
    print("🚀 RUNNING COMPREHENSIVE SOPHISTICATED SEARCH TESTS")
    print("=" * 80)
    
    test_suite = TestSophisticatedSearchPipeline()
    
    # Run all tests
    await test_suite.test_exact_match_scenario(SophisticatedSearchPipeline())
    await test_suite.test_budget_expansion_scenario()
    await test_suite.test_location_alternatives_scenario()
    await test_suite.test_property_type_alternatives_scenario()
    await test_suite.test_market_intelligence_scenario()
    await test_suite.test_response_generation()
    await test_suite.test_conversation_engine_integration()
    await test_suite.test_performance_benchmarks()
    
    print("\n" + "=" * 80)
    print("✅ ALL SOPHISTICATED SEARCH TESTS COMPLETED SUCCESSFULLY!")
    print("🎯 System ready for production use")


# Demo scenarios for manual testing
async def demo_sophisticated_search():
    """Demo scenarios showing sophisticated search in action"""
    print("🎬 SOPHISTICATED SEARCH DEMO SCENARIOS")
    print("=" * 60)
    
    demo_scenarios = [
        {
            'name': 'Perfect Match Found',
            'description': 'User wants 1BR apartment in Marina for rent, exact matches available',
            'criteria': {
                'transaction_type': 'rent',
                'location': 'Dubai Marina',
                'property_type': 'Apartment',
                'bedrooms': 1,
                'budget_min': 50000,
                'budget_max': 150000
            }
        },
        {
            'name': 'Budget Too Low - Expansion Suggested',
            'description': 'User wants apartment in Marina but budget too low',
            'criteria': {
                'transaction_type': 'rent',
                'location': 'Dubai Marina',
                'property_type': 'Apartment',
                'bedrooms': 2,
                'budget_min': 20000,
                'budget_max': 30000
            }
        },
        {
            'name': 'Location Unavailable - Alternatives Offered',
            'description': 'User wants property in rare location, nearby options suggested',
            'criteria': {
                'transaction_type': 'buy',
                'location': 'Rare Beach Area',
                'property_type': 'Villa',
                'budget_min': 2000000,
                'budget_max': 5000000
            }
        },
        {
            'name': 'No Properties Match - Market Intelligence',
            'description': 'Impossible criteria, market analysis provided',
            'criteria': {
                'transaction_type': 'rent',
                'location': 'Fantasy Island',
                'property_type': 'Castle',
                'bedrooms': 50,
                'budget_min': 100,
                'budget_max': 200
            }
        }
    ]
    
    for i, scenario in enumerate(demo_scenarios, 1):
        print(f"\n🎬 DEMO {i}: {scenario['name']}")
        print(f"📝 {scenario['description']}")
        print("-" * 60)
        
        # Execute search
        start_time = time.time()
        result = await search_with_sophisticated_intelligence(**scenario['criteria'])
        execution_time = (time.time() - start_time) * 1000
        
        # Generate response
        criteria = SearchCriteria(**scenario['criteria'])
        response = generate_sophisticated_response(result, criteria)
        
        print(f"🎯 Search Tier: {result.tier.value}")
        print(f"📊 Strategy: {result.strategy_used}")
        print(f"🏠 Properties Found: {result.count}")
        print(f"⏱️ Execution Time: {execution_time:.0f}ms")
        print(f"💡 Suggestions: {len(result.suggestions)}")
        
        print(f"\n📱 WhatsApp Response:")
        print("-" * 40)
        print(response[:500] + "..." if len(response) > 500 else response)
        print("-" * 40)


if __name__ == "__main__":
    # Run comprehensive tests
    print("Choose test mode:")
    print("1. Comprehensive Tests")
    print("2. Demo Scenarios")
    print("3. Both")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice in ['1', '3']:
        asyncio.run(run_comprehensive_tests())
    
    if choice in ['2', '3']:
        asyncio.run(demo_sophisticated_search())
