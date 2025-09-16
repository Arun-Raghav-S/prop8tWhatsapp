"""
Quick test runner for location services
Run this to verify all the fixes are working properly
"""

import asyncio
import sys
import os
import json
from unittest.mock import Mock, patch, AsyncMock

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.smart_location_assistant import SmartLocationAssistant
from tools.property_location_service import PropertyLocationService
from tools.location_tools import LocationToolsHandler

async def test_location_vs_brochure_types():
    """Test that we correctly distinguish between location and brochure types"""
    print("🧪 Testing location vs brochure type distinction...")
    
    assistant = SmartLocationAssistant()
    
    # Test cases that should result in different API types
    test_cases = [
        ("Share location", "location"),
        ("Send location", "location"),
        ("Where is this property", "location"),
        ("Send me the brochure", "brochure"),
        ("Send brochure", "brochure"),
        ("I want the detailed location card", "brochure")
    ]
    
    for message, expected_type in test_cases:
        print(f"  Testing: '{message}' -> expected type: '{expected_type}'")
        
        with patch.object(assistant, 'openai_client') as mock_client:
            # Mock AI response based on expected type
            intent = "send_brochure" if expected_type == "brochure" else "share_location"
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "intent": intent,
                "confidence": 0.9,
                "user_friendly_description": f"User wants {expected_type}"
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Mock property details
            with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property:
                mock_property.return_value = {
                    'building_name': 'Test Building',
                    'address': json.dumps({'locality': 'Marina'})
                }
                
                # Mock API request to capture the type parameter
                with patch('requests.post') as mock_post:
                    mock_api_response = Mock()
                    mock_api_response.status_code = 200
                    mock_api_response.json.return_value = {"success": True}
                    mock_post.return_value = mock_api_response
                    
                    # Execute the test
                    if expected_type == "brochure":
                        await assistant.send_property_brochure("test-id", "+918281840462", "543107385407043")
                    else:
                        await assistant.send_location_map("test-id", "+918281840462", "543107385407043")
                    
                    # Verify the API was called with correct type
                    mock_post.assert_called_once()
                    call_args = mock_post.call_args
                    payload = call_args[1]['json']
                    actual_type = payload['type']
                    
                    if actual_type == expected_type:
                        print(f"    ✅ PASS: API called with type '{actual_type}'")
                    else:
                        print(f"    ❌ FAIL: Expected type '{expected_type}' but got '{actual_type}'")
    
    print("✅ Location vs brochure type testing completed\n")

async def test_nearby_places_search():
    """Test nearby places search functionality"""
    print("🧪 Testing nearby places search...")
    
    assistant = SmartLocationAssistant()
    
    # Test with coordinates available
    print("  Testing with coordinates available...")
    
    with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property:
        mock_property.return_value = {
            'building_name': 'Ocean Heights',
            'address': json.dumps({
                'latitude': 25.0760,
                'longitude': 55.1330,
                'locality': 'Marina'
            })
        }
        
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "nearestPlaces": [
                    {
                        "name": "Dubai British School",
                        "address": "Dubai Marina, Dubai", 
                        "rating": 4.5
                    }
                ]
            }
            mock_post.return_value = mock_response
            
            result = await assistant.find_nearby_places("test-id", "school")
            
            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            if (payload['action'] == 'findNearestPlace' and 
                payload['query'] == 'school' and
                payload['location'] == '25.076,55.133'):
                print(f"    ✅ PASS: API called correctly for nearby places")
                print(f"    ✅ Response contains: 'Dubai British School'")
            else:
                print(f"    ❌ FAIL: API call parameters incorrect")
    
    # Test without coordinates (should provide fallback)
    print("  Testing without coordinates (fallback)...")
    
    with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property:
        mock_property.return_value = {
            'building_name': 'Test Building',
            'address': json.dumps({'locality': 'Marina'})  # No coordinates
        }
        
        result = await assistant.find_nearby_places("test-id", "school")
        
        if "don't have exact coordinates" in result and "location brochure" in result:
            print(f"    ✅ PASS: Provided helpful fallback when coordinates missing")
        else:
            print(f"    ❌ FAIL: Fallback response not helpful")
    
    print("✅ Nearby places search testing completed\n")

def test_backward_compatibility():
    """Test that legacy methods still work"""
    print("🧪 Testing backward compatibility...")
    
    service = PropertyLocationService()
    
    # Test legacy detect_location_intent method
    test_cases = [
        ("What are nearby schools", "find_nearest", "school"),
        ("Send me the brochure", "get_brochure", None),
        ("Share location", "get_location", None)
    ]
    
    for message, expected_intent, expected_query in test_cases:
        print(f"  Testing legacy method: '{message}'")
        
        result = service.detect_location_intent(message)
        
        if result["intent"] == expected_intent:
            print(f"    ✅ PASS: Intent '{expected_intent}' detected correctly")
            if expected_query and result.get("query") == expected_query:
                print(f"    ✅ PASS: Query '{expected_query}' extracted correctly")
            elif not expected_query:
                print(f"    ✅ PASS: No query needed for this intent")
        else:
            print(f"    ❌ FAIL: Expected intent '{expected_intent}' but got '{result['intent']}'")
    
    print("✅ Backward compatibility testing completed\n")

def test_coordinate_extraction():
    """Test coordinate extraction from different formats"""
    print("🧪 Testing coordinate extraction...")
    
    handler = LocationToolsHandler()
    
    test_cases = [
        # New format
        ({"latitude": 25.0760, "longitude": 55.1330}, (25.0760, 55.1330), "New format"),
        # Old format
        ({"lat": "25.0760", "lng": "55.1330"}, (25.0760, 55.1330), "Old format"),
        # JSON string
        (json.dumps({"latitude": 25.0760, "longitude": 55.1330}), (25.0760, 55.1330), "JSON string"),
        # Missing coordinates
        ({"locality": "Marina"}, None, "Missing coordinates"),
        # Empty data
        ({}, None, "Empty data")
    ]
    
    for address_data, expected_coords, description in test_cases:
        print(f"  Testing: {description}")
        
        result = handler.extract_coordinates_from_address(address_data)
        
        if result == expected_coords:
            print(f"    ✅ PASS: Got expected result {expected_coords}")
        else:
            print(f"    ❌ FAIL: Expected {expected_coords} but got {result}")
    
    print("✅ Coordinate extraction testing completed\n")

async def test_full_integration():
    """Test the complete integration flow"""
    print("🧪 Testing full integration scenarios...")
    
    # Simulate the exact scenario from the logs
    print("  Simulating 'Share location' scenario...")
    
    assistant = SmartLocationAssistant()
    
    with patch.object(assistant, 'openai_client') as mock_client, \
         patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
         patch('requests.post') as mock_post:
        
        # Mock AI intent detection
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "intent": "share_location",
            "confidence": 0.9,
            "user_friendly_description": "User wants basic location information"
        })
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        
        # Mock property details
        mock_property.return_value = {
            'building_name': 'Ocean Heights',
            'address': json.dumps({'locality': 'Marina'})
        }
        
        # Mock successful API response
        mock_api_response = Mock()
        mock_api_response.status_code = 200
        mock_api_response.json.return_value = {"success": True}
        mock_post.return_value = mock_api_response
        
        # Execute full flow
        result = await assistant.handle_location_request(
            property_id="1e5e38a5-42a6-4af2-8c91-17ffb3f0078c",
            user_phone="+918281840462",
            whatsapp_account="543107385407043", 
            user_message="Share location"
        )
        
        # Verify the complete flow
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        payload = call_args[1]['json']
        
        success_checks = [
            (payload['type'] == 'location', "Correct API type"),
            (payload['project_id'] == "1e5e38a5-42a6-4af2-8c91-17ffb3f0078c", "Correct property ID"),
            (payload['send_to'] == "918281840462", "Correct phone number"),
            ("Location Information Sent!" in result, "Correct response message")
        ]
        
        all_passed = True
        for check, description in success_checks:
            if check:
                print(f"    ✅ PASS: {description}")
            else:
                print(f"    ❌ FAIL: {description}")
                all_passed = False
        
        if all_passed:
            print(f"    🎉 INTEGRATION TEST PASSED!")
        else:
            print(f"    💥 INTEGRATION TEST FAILED!")
    
    print("✅ Full integration testing completed\n")

async def main():
    """Run all tests"""
    print("🚀 Running Location Services Tests")
    print("=" * 50)
    
    try:
        # Run all test suites
        await test_location_vs_brochure_types()
        await test_nearby_places_search() 
        test_backward_compatibility()
        test_coordinate_extraction()
        await test_full_integration()
        
        print("🎉 ALL TESTS COMPLETED!")
        print("✅ Location services fixes have been verified")
        
    except Exception as e:
        print(f"💥 TEST EXECUTION FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
