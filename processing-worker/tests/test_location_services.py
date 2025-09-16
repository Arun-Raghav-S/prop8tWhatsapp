"""
Comprehensive tests for location services
Tests all the fixes for location vs brochure types and nearby places search
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add the parent directory to the path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.smart_location_assistant import SmartLocationAssistant
from tools.property_location_service import PropertyLocationService
from tools.location_tools import LocationToolsHandler


class TestSmartLocationAssistant:
    """Test the new Smart Location Assistant"""
    
    def setup_method(self):
        self.assistant = SmartLocationAssistant()
        
    @pytest.mark.asyncio
    async def test_intent_analysis_location_request(self):
        """Test AI intent analysis for basic location requests"""
        with patch.object(self.assistant, 'openai_client') as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "intent": "share_location",
                "confidence": 0.9,
                "user_friendly_description": "User wants basic location information"
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await self.assistant.analyze_location_intent("Share location")
            
            assert result["intent"] == "share_location"
            assert result["confidence"] == 0.9
            assert "location information" in result["user_friendly_description"]
    
    @pytest.mark.asyncio
    async def test_intent_analysis_brochure_request(self):
        """Test AI intent analysis for brochure requests"""
        with patch.object(self.assistant, 'openai_client') as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "intent": "send_brochure",
                "confidence": 0.9,
                "user_friendly_description": "User wants detailed property brochure"
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await self.assistant.analyze_location_intent("Send me the brochure")
            
            assert result["intent"] == "send_brochure"
            assert result["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_intent_analysis_nearby_places(self):
        """Test AI intent analysis for nearby places requests"""
        with patch.object(self.assistant, 'openai_client') as mock_client:
            mock_response = Mock()
            mock_response.choices[0].message.content = json.dumps({
                "intent": "find_nearby",
                "place_type": "school",
                "confidence": 0.9,
                "user_friendly_description": "User wants to find nearby schools"
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await self.assistant.analyze_location_intent("What are nearby schools")
            
            assert result["intent"] == "find_nearby"
            assert result["place_type"] == "school"
            assert result["confidence"] == 0.9
    
    @pytest.mark.asyncio
    async def test_send_location_api_call(self):
        """Test that location API is called with correct type parameter"""
        property_id = "test-property-id"
        user_phone = "+918281840462"
        whatsapp_account = "543107385407043"
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
             patch('requests.post') as mock_post:
            
            # Mock property details
            mock_property.return_value = {
                'building_name': 'Test Building',
                'address': json.dumps({'locality': 'Marina'})
            }
            
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response
            
            # Test location request
            result = await self.assistant.send_basic_location(property_id, user_phone, whatsapp_account)
            
            # Verify API was called with correct type
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload['type'] == 'location'  # This was the bug - it was always 'brochure'
            assert payload['project_id'] == property_id
            assert payload['send_to'] == user_phone.replace('+', '')
            assert "Location Information Sent!" in result
    
    @pytest.mark.asyncio
    async def test_send_property_brochure_api_call(self):
        """Test that brochure API is called with correct type parameter"""
        property_id = "test-property-id"
        user_phone = "+918281840462"
        whatsapp_account = "543107385407043"
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
             patch('requests.post') as mock_post:
            
            # Mock property details
            mock_property.return_value = {
                'building_name': 'Test Building',
                'address': json.dumps({'locality': 'Marina'})
            }
            
            # Mock successful API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response
            
            # Test brochure request
            result = await self.assistant.send_property_brochure(property_id, user_phone, whatsapp_account)
            
            # Verify API was called with correct type
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload['type'] == 'brochure'  # Correct type for brochure
            assert payload['project_id'] == property_id
            assert payload['send_to'] == user_phone.replace('+', '')
            assert "Property Brochure Sent!" in result
    
    @pytest.mark.asyncio
    async def test_nearby_places_with_coordinates(self):
        """Test nearby places search when coordinates are available"""
        property_id = "test-property-id"
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
             patch('requests.post') as mock_post:
            
            # Mock property details with coordinates
            mock_property.return_value = {
                'building_name': 'Ocean Heights',
                'address': json.dumps({
                    'latitude': 25.0760,
                    'longitude': 55.1330,
                    'locality': 'Marina'
                })
            }
            
            # Mock successful places API response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "nearestPlaces": [
                    {
                        "name": "Dubai British School",
                        "address": "Dubai Marina, Dubai",
                        "rating": 4.5
                    },
                    {
                        "name": "GEMS Academy",
                        "address": "Jumeirah Beach Road, Dubai",
                        "rating": 4.2
                    }
                ]
            }
            mock_post.return_value = mock_response
            
            result = await self.assistant.find_nearby_places(property_id, "school")
            
            # Verify API was called correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload['action'] == 'findNearestPlace'
            assert payload['query'] == 'school'
            assert payload['location'] == '25.076,55.133'
            assert payload['k'] == 3
            
            # Verify response formatting
            assert "Nearest school to Ocean Heights" in result
            assert "Dubai British School" in result
            assert "GEMS Academy" in result
            assert "⭐ 4.5" in result
    
    @pytest.mark.asyncio
    async def test_nearby_places_without_coordinates(self):
        """Test nearby places search when coordinates are missing (should provide fallback)"""
        property_id = "test-property-id"
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property:
            
            # Mock property details without coordinates
            mock_property.return_value = {
                'building_name': 'Test Building',
                'address': json.dumps({
                    'locality': 'Marina'
                })  # No coordinates
            }
            
            result = await self.assistant.find_nearby_places(property_id, "school")
            
            # Should provide helpful fallback message
            assert "don't have exact coordinates" in result
            assert "share location" in result
            assert "Test Building" in result


class TestPropertyLocationService:
    """Test the enhanced Property Location Service"""
    
    def setup_method(self):
        self.service = PropertyLocationService()
    
    @pytest.mark.asyncio
    async def test_ai_intent_detection(self):
        """Test AI-based intent detection vs old keyword matching"""
        with patch.object(self.service, 'openai_client') as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "intent": "get_location",
                "request_type": "location",
                "confidence": 0.9
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await self.service.detect_location_intent_ai("Share location")
            
            assert result["intent"] == "get_location"
            assert result["request_type"] == "location"
            assert result["confidence"] == 0.9
    
    def test_legacy_keyword_detection(self):
        """Test backward compatibility with legacy keyword detection"""
        # Test nearby places
        result = self.service.detect_location_intent("What are nearby schools")
        assert result["intent"] == "find_nearest"
        assert result["query"] == "school"
        
        # Test brochure request
        result = self.service.detect_location_intent("Send me the brochure")
        assert result["intent"] == "get_brochure"
        
        # Test location request  
        result = self.service.detect_location_intent("Share location")
        assert result["intent"] == "get_location"
    
    @pytest.mark.asyncio
    async def test_routing_to_smart_assistant(self):
        """Test that requests are properly routed to Smart Location Assistant"""
        with patch('tools.smart_location_assistant.smart_location_assistant.handle_location_request') as mock_assistant:
            mock_assistant.return_value = "Test response from smart assistant"
            
            result = await self.service.handle_location_request(
                property_id="test-id",
                user_phone="+918281840462", 
                whatsapp_account="543107385407043",
                message="Share location"
            )
            
            mock_assistant.assert_called_once_with(
                property_id="test-id",
                user_phone="+918281840462",
                whatsapp_account="543107385407043", 
                user_message="Share location"
            )
            assert result == "Test response from smart assistant"


class TestLocationToolsHandler:
    """Test the enhanced Location Tools Handler"""
    
    def setup_method(self):
        self.handler = LocationToolsHandler()
    
    def test_coordinate_extraction_new_format(self):
        """Test coordinate extraction with new latitude/longitude format"""
        address_data = {
            "latitude": 25.0760,
            "longitude": 55.1330,
            "locality": "Marina"
        }
        
        coords = self.handler.extract_coordinates_from_address(address_data)
        assert coords == (25.0760, 55.1330)
    
    def test_coordinate_extraction_old_format(self):
        """Test coordinate extraction with old lat/lng format"""
        address_data = {
            "lat": "25.0760",  # String format
            "lng": "55.1330",
            "locality": "Marina"
        }
        
        coords = self.handler.extract_coordinates_from_address(address_data)
        assert coords == (25.0760, 55.1330)
    
    def test_coordinate_extraction_json_string(self):
        """Test coordinate extraction from JSON string"""
        address_data = json.dumps({
            "latitude": 25.0760,
            "longitude": 55.1330,
            "locality": "Marina"
        })
        
        coords = self.handler.extract_coordinates_from_address(address_data)
        assert coords == (25.0760, 55.1330)
    
    def test_coordinate_extraction_missing_data(self):
        """Test coordinate extraction when data is missing"""
        address_data = {"locality": "Marina"}  # No coordinates
        
        coords = self.handler.extract_coordinates_from_address(address_data)
        assert coords is None
    
    @pytest.mark.asyncio
    async def test_ai_place_type_extraction(self):
        """Test AI-based place type extraction"""
        with patch.object(self.handler, 'openai_client') as mock_client:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "place_type": "school",
                "category": "education",
                "confidence": 0.9,
                "search_terms": ["school", "academy"]
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            result = await self.handler.extract_place_type_with_ai("What are nearby schools")
            
            assert result["place_type"] == "school"
            assert result["category"] == "education"
            assert result["confidence"] == 0.9
            assert "school" in result["search_terms"]
            assert "academy" in result["search_terms"]


class TestIntegrationScenarios:
    """Integration tests simulating real scenarios from the logs"""
    
    @pytest.mark.asyncio
    async def test_share_location_scenario(self):
        """Test the complete flow for 'Share location' request"""
        assistant = SmartLocationAssistant()
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
             patch('requests.post') as mock_post, \
             patch.object(assistant, 'openai_client') as mock_client:
            
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
            
            # Execute the request
            result = await assistant.handle_location_request(
                property_id="1e5e38a5-42a6-4af2-8c91-17ffb3f0078c",
                user_phone="+918281840462",
                whatsapp_account="543107385407043",
                user_message="Share location"
            )
            
            # Verify correct API call was made
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload['type'] == 'location'  # This was the main bug
            assert payload['project_id'] == "1e5e38a5-42a6-4af2-8c91-17ffb3f0078c"
            assert "Location Information Sent!" in result
    
    @pytest.mark.asyncio
    async def test_nearby_schools_scenario(self):
        """Test the complete flow for 'Nearby schools' request"""
        assistant = SmartLocationAssistant()
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
             patch('requests.post') as mock_post, \
             patch.object(assistant, 'openai_client') as mock_client:
            
            # Mock AI intent detection
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "intent": "find_nearby",
                "place_type": "school",
                "confidence": 0.9,
                "user_friendly_description": "User wants to find nearby schools"
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Mock property details with coordinates
            mock_property.return_value = {
                'building_name': 'Ocean Heights',
                'address': json.dumps({
                    'latitude': 25.0760,
                    'longitude': 55.1330,
                    'locality': 'Marina'
                })
            }
            
            # Mock successful places API response
            mock_api_response = Mock()
            mock_api_response.status_code = 200
            mock_api_response.json.return_value = {
                "nearestPlaces": [
                    {
                        "name": "Dubai British School",
                        "address": "Dubai Marina, Dubai",
                        "rating": 4.5
                    }
                ]
            }
            mock_post.return_value = mock_api_response
            
            # Execute the request
            result = await assistant.handle_location_request(
                property_id="1e5e38a5-42a6-4af2-8c91-17ffb3f0078c",
                user_phone="+918281840462",
                whatsapp_account="543107385407043",
                user_message="Nearby schools"
            )
            
            # Verify correct API call was made
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            
            assert payload['action'] == 'findNearestPlace'
            assert payload['query'] == 'school'
            assert "Dubai British School" in result
    
    @pytest.mark.asyncio 
    async def test_error_handling_no_coordinates(self):
        """Test error handling when coordinates are missing"""
        assistant = SmartLocationAssistant()
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
             patch.object(assistant, 'openai_client') as mock_client:
            
            # Mock AI intent detection
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "intent": "find_nearby",
                "place_type": "school",
                "confidence": 0.9,
                "user_friendly_description": "User wants to find nearby schools"
            })
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            
            # Mock property details WITHOUT coordinates
            mock_property.return_value = {
                'building_name': 'Ocean Heights',
                'address': json.dumps({'locality': 'Marina'})  # No lat/lng
            }
            
            # Execute the request
            result = await assistant.handle_location_request(
                property_id="1e5e38a5-42a6-4af2-8c91-17ffb3f0078c",
                user_phone="+918281840462", 
                whatsapp_account="543107385407043",
                user_message="Nearby schools"
            )
            
            # Should provide helpful fallback
            assert "don't have exact coordinates" in result
            assert "Ocean Heights" in result
            assert "share location" in result


class TestErrorScenarios:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_api_failure_handling(self):
        """Test handling of API failures"""
        assistant = SmartLocationAssistant()
        
        with patch('tools.property_details_tool.property_details_tool.get_property_details') as mock_property, \
             patch('requests.post') as mock_post, \
             patch.object(assistant, 'openai_client') as mock_client:
            
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
            
            # Mock API failure
            mock_api_response = Mock()
            mock_api_response.status_code = 400
            mock_api_response.text = '{"status":"failure","error":"Brochure URL not available"}'
            mock_post.return_value = mock_api_response
            
            # Execute the request
            result = await assistant.send_basic_location(
                property_id="test-property-id",
                user_phone="+918281840462",
                whatsapp_account="543107385407043"
            )
            
            # Should provide helpful fallback response
            assert "Location Information" in result
            assert "having trouble" in result
            assert "Alternative options" in result


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
