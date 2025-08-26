"""
Demo: AI-Native vs Pattern Matching Approach
Shows how the new AI system handles edge cases that pattern matching fails on
"""

import asyncio
import os
from tools.intelligent_conversation_manager import intelligent_conversation_manager, ConversationStage

# Mock OpenAI for demo purposes if no API key
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  No OpenAI API key found - using mock responses for demo")
    
    class MockResponse:
        def __init__(self, content):
            self.content = content
    
    class MockChoice:
        def __init__(self, content):
            self.message = MockResponse(content)
    
    class MockCompletion:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
    
    async def mock_create(**kwargs):
        # Mock AI response for demo
        return MockCompletion("""
        {
            "intent": "property_search",
            "stage": "collecting_basic_info", 
            "requirements": {
                "transaction_type": "rent",
                "location": "Dubai Marina",
                "budget_min": 80000,
                "budget_max": 100000,
                "budget_period": "yearly",
                "property_type": "apartment",
                "bedrooms": 2,
                "bathrooms": null,
                "special_features": [],
                "confidence_transaction_type": 0.9,
                "confidence_location": 0.8,
                "confidence_budget": 0.85,
                "confidence_property_type": 0.9
            },
            "confidence_score": 0.87,
            "needs_clarification": false,
            "clarification_question": null
        }
        """)
    
    intelligent_conversation_manager.openai.chat.completions.create = mock_create


async def demo_ai_vs_pattern():
    """Demo the difference between AI and pattern matching approaches"""
    
    print("🚀 AI-Native vs Pattern Matching Demo")
    print("=" * 50)
    
    # Test cases that would break pattern matching
    test_cases = [
        "I need an apartment somewhere near the marina, budget around 80-100k yearly for rent",
        "Looking for a 2BR flat to rent in Marina area, max 100k per year",  
        "Want to rent a place near JBR, 2 bedrooms, budget 80k-100k",
        "Need a rental property, 2 bed apartment, Marina vicinity, 100k budget",
        "Searching for rental flat, Marina location, two bedrooms, 80-100 thousand AED",
        "Apartment hunt - rent in Dubai Marina area, 2BR, yearly budget 80-100k"
    ]
    
    print("🧠 AI-Native Approach Results:")
    print("-" * 30)
    
    for i, message in enumerate(test_cases, 1):
        print(f"\n{i}. User: \"{message}\"")
        
        try:
            # Use AI to analyze message
            intent = await intelligent_conversation_manager.analyze_user_message(
                message, [], ConversationStage.INITIAL
            )
            
            req = intent.requirements
            print(f"   🎯 Intent: {intent.intent} (confidence: {intent.confidence_score:.2f})")
            print(f"   📋 Extracted:")
            print(f"      • Type: {req.transaction_type} (confidence: {req.confidence_transaction_type:.2f})")
            print(f"      • Location: {req.location} (confidence: {req.confidence_location:.2f})")
            print(f"      • Budget: {req.budget_min}-{req.budget_max} AED {req.budget_period}")
            print(f"      • Property: {req.bedrooms}BR {req.property_type}")
            print(f"   ✅ Ready for search: {intelligent_conversation_manager.is_ready_for_search(req)}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("🔧 Old Pattern Matching Would Have Failed Because:")
    print("=" * 50)
    print("❌ Hardcoded patterns like 'looking for apartments' miss variations")
    print("❌ Regex for budget extraction limited to specific formats") 
    print("❌ Location matching only works for exact area names")
    print("❌ Can't handle natural language variations")
    print("❌ Complex state management with boolean flags")
    print("❌ No confidence scoring")
    print("❌ Brittle and doesn't scale")
    
    print("\n✅ AI-Native Advantages:")
    print("=" * 30)
    print("🧠 Understands natural language variations")
    print("🎯 Extracts structured information with confidence scores")
    print("🔄 Handles complex conversational flows")
    print("📊 Provides intelligent clarification")
    print("🚀 Scales with more data and use cases")
    print("🛡️  Robust to edge cases and creative language")


if __name__ == "__main__":
    asyncio.run(demo_ai_vs_pattern())
