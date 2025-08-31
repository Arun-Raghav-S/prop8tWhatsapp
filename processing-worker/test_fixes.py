#!/usr/bin/env python3
"""
🧪 TEST SCRIPT: Budget & Pagination Fixes
Quick test to verify the fixes work correctly
"""

import asyncio
import sys
import os
import time

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.sophisticated_search_pipeline import SearchCriteria, search_with_sophisticated_intelligence
from tools.sophisticated_response_generator import generate_sophisticated_response
from unified_conversation_engine import unified_engine
from utils.session_manager import ConversationSession


async def test_budget_parsing():
    """Test 1: Budget parsing should treat '1.5M' as 'up to 1.5M', not exact match"""
    print("🧪 TEST 1: Budget Parsing")
    print("-" * 50)
    
    # Create test session
    session = ConversationSession("test-user")
    
    # Test message with budget
    message = "i want to buy apartment in Marina budget is 1.5M"
    
    # Process through conversation engine
    conv_response = await unified_engine.process_message(message, session)
    
    print(f"Message: {message}")
    print(f"Response stage: {conv_response.stage}")
    print(f"Should search: {conv_response.should_search_properties}")
    
    if conv_response.sophisticated_search_criteria:
        criteria = conv_response.sophisticated_search_criteria
        print(f"Search criteria: {criteria}")
        
        # Check budget parsing
        budget_min = criteria.get('budget_min')
        budget_max = criteria.get('budget_max') 
        
        print(f"Budget min: {budget_min}")
        print(f"Budget max: {budget_max}")
        
        # Verify fix: should be budget_max: 1500000, budget_min: None or lower
        if budget_max == 1500000 and (budget_min is None or budget_min < budget_max):
            print("✅ BUDGET PARSING: FIXED - Correctly parsed '1.5M' as max budget")
        else:
            print(f"❌ BUDGET PARSING: STILL BROKEN - Expected max=1500000, got min={budget_min}, max={budget_max}")
    
    print()


async def test_sophisticated_search():
    """Test 2: Sophisticated search should provide alternatives when exact match fails"""
    print("🧪 TEST 2: Sophisticated Search with Alternatives")
    print("-" * 50)
    
    # Test with criteria that likely won't have exact matches
    criteria = SearchCriteria(
        transaction_type='buy',
        location='Dubai Marina',
        budget_min=None,
        budget_max=50000,  # Very low budget for Marina
        property_type='Apartment',
        bedrooms=2
    )
    
    print(f"Test criteria: {criteria.to_dict()}")
    
    start_time = time.time()
    result = await search_with_sophisticated_intelligence(**criteria.to_dict())
    execution_time = (time.time() - start_time) * 1000
    
    print(f"Search tier: {result.tier.value}")
    print(f"Strategy used: {result.strategy_used}")
    print(f"Properties found: {result.count}")
    print(f"Execution time: {execution_time:.0f}ms")
    print(f"Suggestions provided: {len(result.suggestions)}")
    
    if result.suggestions:
        print("Suggestions:")
        for i, suggestion in enumerate(result.suggestions[:3], 1):
            print(f"  {i}. {suggestion}")
    
    # Generate intelligent response
    response = generate_sophisticated_response(result, criteria)
    print(f"\nIntelligent response preview:")
    print(response[:300] + "..." if len(response) > 300 else response)
    
    if result.tier.value != 'exact_match' and result.suggestions:
        print("✅ SOPHISTICATED SEARCH: Working - Provides alternatives when exact match fails")
    else:
        print("❌ SOPHISTICATED SEARCH: May need verification - Check if alternatives are appropriate")
    
    print()


async def test_conversation_integration():
    """Test 3: Full conversation integration"""
    print("🧪 TEST 3: Full Conversation Integration")
    print("-" * 50)
    
    session = ConversationSession("test-user-integration")
    
    # Simulate full conversation flow
    messages = [
        "hi",
        "i want to buy apartment in Marina budget is 1.5M"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"User message {i}: {message}")
        
        conv_response = await unified_engine.process_message(message, session)
        
        print(f"  Stage: {conv_response.stage}")
        print(f"  Should search: {conv_response.should_search_properties}")
        print(f"  Use sophisticated: {conv_response.use_sophisticated_search}")
        
        if conv_response.sophisticated_search_criteria:
            print(f"  Search criteria: {conv_response.sophisticated_search_criteria}")
        
        print(f"  Response: {conv_response.message[:100]}...")
        print()
    
    # Check if session has proper context
    if session.context.get('conversation_stage'):
        print(f"Session conversation stage: {session.context['conversation_stage']}")
        print("✅ CONVERSATION INTEGRATION: Working - Proper stage management")
    else:
        print("❌ CONVERSATION INTEGRATION: Issue - No conversation stage in session")


async def test_budget_expansion_fallback():
    """Test 4: Budget expansion in fallback logic"""
    print("🧪 TEST 4: Budget Expansion Fallback")
    print("-" * 50)
    
    from optimized_property_search import optimized_search
    
    # Test the budget expansion method
    original_params = {
        'sale_or_rent': 'sale',
        'property_type': 'Apartment',
        'locality': 'Marina',
        'min_sale_price_aed': 1000000,
        'max_sale_price_aed': 1500000
    }
    
    expanded_params = optimized_search._create_expanded_budget_params(original_params, 1.5)
    
    print(f"Original max budget: {original_params['max_sale_price_aed']:,}")
    print(f"Expanded max budget: {expanded_params['max_sale_price_aed']:,}")
    
    expected_max = int(1500000 * 1.5)  # 2,250,000
    if expanded_params['max_sale_price_aed'] == expected_max:
        print("✅ BUDGET EXPANSION: Working - Correctly expands budget by multiplier")
    else:
        print(f"❌ BUDGET EXPANSION: Issue - Expected {expected_max:,}, got {expanded_params['max_sale_price_aed']:,}")
    
    print()


async def main():
    """Run all tests"""
    print("🚀 TESTING BUDGET & PAGINATION FIXES")
    print("=" * 80)
    
    try:
        await test_budget_parsing()
        await test_sophisticated_search() 
        await test_conversation_integration()
        await test_budget_expansion_fallback()
        
        print("=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("📋 Review the results above to verify fixes are working")
        print("🔍 Check logs in your actual system for detailed behavior")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
