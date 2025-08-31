#!/usr/bin/env python3
"""
Test pagination fix for "shoe shoe more properties" issue
"""

import asyncio
import json
from unified_conversation_engine import UnifiedConversationEngine, ConversationSession, ConversationStage

async def test_pagination_intent_detection():
    """Test that typos in pagination requests are handled correctly"""
    
    engine = UnifiedConversationEngine()
    
    # Create session with pagination context
    session = ConversationSession(user_id="+919999999999")
    session.context = {
        'conversation_stage': ConversationStage.SHOWING_RESULTS,
        'all_available_properties': [{'id': f'prop_{i}'} for i in range(15)],  # 15 mock properties
        'properties_shown': 10,  # Already shown 10
        'properties_per_batch': 10,
        'active_properties': [{'id': f'prop_{i}'} for i in range(10)]
    }
    
    # Test various pagination messages (including typos)
    test_messages = [
        "show more properties",
        "shoe more properties", 
        "shoe shoe more properties",
        "more properties",
        "see more",
        "next batch",
        "load more"
    ]
    
    print("🧪 Testing pagination intent detection...")
    
    for message in test_messages:
        print(f"\n📝 Testing: '{message}'")
        
        try:
            # Test intent analysis
            intent = await engine._analyze_user_intent(message, session)
            
            is_pagination = intent.get('is_pagination_request', False)
            is_fresh_search = intent.get('is_fresh_search', False)
            intent_category = intent.get('intent_category', 'unknown')
            
            print(f"   🧠 Intent: pagination={is_pagination}, fresh_search={is_fresh_search}, category={intent_category}")
            
            if is_pagination and not is_fresh_search:
                print("   ✅ CORRECT: Detected as pagination request")
            elif is_fresh_search:
                print("   ❌ WRONG: Incorrectly detected as fresh search!")
            else:
                print("   ⚠️ UNCLEAR: Not detected as pagination or fresh search")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_pagination_intent_detection())
