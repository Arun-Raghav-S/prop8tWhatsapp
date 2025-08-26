"""
Configuration for the flow emulator tests
"""

# From the actual logs - use these exact values for realistic testing
TEST_CONFIG = {
    "business_account": "543107385407043",
    "user_phone": "918281840462",  # Without +
    "user_phone_full": "+918281840462",  # With +
    "bot_phone": "919345007934",  # The bot's phone number from logs
    
    # Property IDs from the actual logs for button testing
    "property_ids": [
        "f63420b4-4e1c-4f7f-8670-575934ab936b",  # Property 1 from logs
        "a839d7a9-4035-4c3f-accd-b71286ee0aad",  # Property 2 from logs
        "d947b216-9032-450b-8e67-658fd7956a9f",  # Property 3 from logs
        "4900fde3-eaf4-4bf5-ab3f-241248f512e5",  # Property 4 from logs (used in Know More)
        "ae7ce71f-0a64-4e55-86d9-3bb74e98bb96",  # Property 5 from logs
    ],
    
    # Server configuration
    "default_server_url": "http://localhost:8080",
    
    # Test timing
    "wait_times": {
        "short": 3,   # For simple responses
        "medium": 5,  # For AI processing
        "long": 8     # For property search
    }
}

# Conversation flows to test
CONVERSATION_FLOWS = {
    "basic_property_search": [
        {"type": "text", "content": "Hi"},
        {"type": "text", "content": "Show me some apartments anywhere and any price bro"},
        {"type": "text", "content": "Buy"},
    ],
    
    "rental_search": [
        {"type": "text", "content": "Hi"},
        {"type": "text", "content": "I want to rent a 2 bedroom apartment in Dubai Marina"},
        {"type": "text", "content": "My budget is 100k per year"},
    ],
    
    "button_interaction": [
        {"type": "text", "content": "Hi"},
        {"type": "text", "content": "Show me apartments for sale"},
        {"type": "text", "content": "Buy"},
        {"type": "button", "property_id": "4900fde3-eaf4-4bf5-ab3f-241248f512e5", "action": "knowMore", "text": "Know More"},
        {"type": "button", "property_id": "a839d7a9-4035-4c3f-accd-b71286ee0aad", "action": "scheduleVisit", "text": "Schedule Visit"},
        {"type": "text", "content": "Tomorrow at 3 PM"},
    ],
    
    "full_journey": [
        {"type": "text", "content": "Hi"},
        {"type": "text", "content": "Show me some apartments anywhere and any price bro"},
        {"type": "text", "content": "Buy"},
        {"type": "button", "property_id": "4900fde3-eaf4-4bf5-ab3f-241248f512e5", "action": "knowMore", "text": "Know More"},
        {"type": "button", "property_id": "a839d7a9-4035-4c3f-accd-b71286ee0aad", "action": "scheduleVisit", "text": "Schedule Visit"},
        {"type": "text", "content": "Tomorrow at 3 PM"},
    ]
}

# Expected responses (for validation)
EXPECTED_RESPONSES = {
    "greeting": [
        "find the perfect property",
        "looking to",
        "buy", 
        "rent",
        "area",
        "budget"
    ],
    "property_search": [
        "Found",
        "properties",
        "carousel",
        "cards",
        "Know More",
        "Schedule Visit"
    ],
    "know_more": [
        "Property",
        "Details",
        "bed",
        "bath",
        "sqft",
        "Price"
    ],
    "schedule_visit": [
        "Schedule",
        "visit",
        "date",
        "time",
        "when would you like"
    ]
}
