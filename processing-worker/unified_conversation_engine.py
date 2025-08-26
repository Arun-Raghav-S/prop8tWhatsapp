"""
Unified Conversation Engine
Supreme AI Engineering: Single source of truth for all conversation logic
Replaces multiple conflicting systems with one intelligent, efficient engine
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from pydantic import BaseModel
from openai import AsyncOpenAI

from utils.logger import setup_logger
from utils.session_manager import ConversationSession

logger = setup_logger(__name__)


class ConversationStage(str, Enum):
    """Conversation stages matching your exact flow diagram"""
    USER_INITIATED = "user_initiated"
    COLLECTING_REQUIREMENTS = "collecting_requirements"  # buy/rent, location, budget, property_type
    READY_FOR_SEARCH = "ready_for_search"
    SHOWING_RESULTS = "showing_results"  # carousel sent
    FOLLOW_UP = "follow_up"  # user asks about specific properties


class UserRequirements(BaseModel):
    """Structured user requirements with confidence tracking"""
    # Core requirements (must have all 4 to proceed)
    transaction_type: Optional[str] = None  # "buy" or "rent"
    location: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    property_type: Optional[str] = None  # "villa", "apartment", "2 beds", etc.
    
    # Optional details
    bedrooms: Optional[int] = None
    special_features: List[str] = []
    
    # Confidence scores (0.0 to 1.0)
    confidence_transaction: float = 0.0
    confidence_location: float = 0.0
    confidence_budget: float = 0.0
    confidence_property: float = 0.0
    
    def is_complete(self) -> bool:
        """Check if we have enough information to proceed with search"""
        # Core requirements: transaction_type and property_type are always needed
        has_core = (
            self.transaction_type and self.confidence_transaction >= 0.7 and
            self.property_type and self.confidence_property >= 0.7
        )
        
        # Location is optional if user explicitly wants "any location" 
        has_location = (
            (self.location and self.confidence_location >= 0.7) or
            (self.location == "any" or self.location == "anywhere" or self.location == "all areas")
        )
        
        # Budget is optional - can search without budget restrictions
        has_budget = (
            (self.budget_min and self.confidence_budget >= 0.7) or
            (self.budget_min is None and "any budget" in str(getattr(self, '_user_context', '')))
        )
        
        return has_core and (has_location or has_budget)
    
    def get_missing_requirements(self) -> List[str]:
        """Get list of missing requirements with smart handling"""
        missing = []
        
        # Core requirements (always needed)
        if not self.transaction_type or self.confidence_transaction < 0.7:
            missing.append("transaction_type")
        if not self.property_type or self.confidence_property < 0.7:
            missing.append("property_type")
            
        # Location - only required if not explicitly "any"
        has_any_location = self.location and self.location.lower() in ["any", "anywhere", "all areas", "any location"]
        if not has_any_location and (not self.location or self.confidence_location < 0.7):
            missing.append("location")
            
        # Budget - only ask if not specified and no location specified
        has_budget = self.budget_min and self.confidence_budget >= 0.7
        has_location = (self.location and self.confidence_location >= 0.7) or has_any_location
        
        if not has_budget and not has_location:
            # Need at least budget or location to search effectively
            if len(missing) == 0:  # Only ask for budget if core requirements are met
                missing.append("budget")
                
        return missing


class ConversationResponse(BaseModel):
    """Unified response from conversation engine"""
    message: str
    stage: ConversationStage
    requirements: UserRequirements
    should_search_properties: bool = False
    search_params: Optional[Dict[str, Any]] = None
    debug_info: Optional[Dict[str, Any]] = None


class UnifiedConversationEngine:
    """
    Single source of truth for all conversation logic
    Replaces multiple conflicting systems with one intelligent engine
    """
    
    def __init__(self):
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        
        # Cache for common responses
        self.response_cache = {}
        
    async def process_message(self, message: str, session: ConversationSession) -> ConversationResponse:
        """
        Single entry point for all conversation processing
        Follows your exact flow diagram logic with fresh search detection
        """
        start_time = time.time()
        
        try:
            # INTELLIGENT CONTEXT DETECTION: Use AI to understand user intent
            intent_analysis = await self._analyze_user_intent(message, session)
            
            if intent_analysis.get("is_fresh_search"):
                logger.info("🔄 FRESH_SEARCH detected by AI - resetting conversation stage")
                session.context['conversation_stage'] = ConversationStage.USER_INITIATED
                # Clear previous search context
                session.context.pop('active_properties', None)
                session.context.pop('last_search_params', None)
                session.context.pop('active_property_id', None)
            
            # Get current conversation state
            current_stage = ConversationStage(session.context.get('conversation_stage', ConversationStage.USER_INITIATED))
            current_requirements = self._get_requirements_from_session(session)
            
            logger.info(f"🎯 Processing message in stage: {current_stage}")
            
            # STAGE 1: User Initiated - Apply your flow logic
            if current_stage == ConversationStage.USER_INITIATED:
                return await self._handle_user_initiated(message, session, current_requirements)
            
            # STAGE 2: Collecting Requirements - Gather the 4 required pieces
            elif current_stage == ConversationStage.COLLECTING_REQUIREMENTS:
                return await self._handle_collecting_requirements(message, session, current_requirements)
            
            # STAGE 3: Ready for Search - Execute property search
            elif current_stage == ConversationStage.READY_FOR_SEARCH:
                return await self._handle_ready_for_search(message, session, current_requirements)
            
            # STAGE 4: Showing Results - Handle carousel interactions
            elif current_stage == ConversationStage.SHOWING_RESULTS:
                return await self._handle_showing_results(message, session, current_requirements)
            
            # STAGE 5: Follow-up - Handle property-specific questions
            elif current_stage == ConversationStage.FOLLOW_UP:
                return await self._handle_follow_up(message, session, current_requirements)
            
            else:
                # Fallback to user initiated
                return await self._handle_user_initiated(message, session, current_requirements)
                
        except Exception as e:
            logger.error(f"❌ Conversation engine error: {str(e)}")
            return ConversationResponse(
                message="I apologize, but I encountered an error. Let me help you find properties. What are you looking for?",
                stage=ConversationStage.USER_INITIATED,
                requirements=UserRequirements()
            )
    
    async def _handle_user_initiated(self, message: str, session: ConversationSession, requirements: UserRequirements) -> ConversationResponse:
        """
        Handle initial user message - extract what we can and ask for missing info
        Follows your flow: greet and ask for buy/rent, location, budget, property type
        """
        logger.info("🎯 STAGE 1: User Initiated")
        
        # Use AI to extract information from initial message
        updated_requirements = await self._extract_requirements_ai(message, requirements)
        
        # Update session with extracted requirements
        self._save_requirements_to_session(session, updated_requirements)
        
        # Check if we have everything
        if updated_requirements.is_complete():
            # Rare case: user provided everything in first message
            session.context['conversation_stage'] = ConversationStage.READY_FOR_SEARCH
            return ConversationResponse(
                message="Perfect! I have all the details I need. Let me find properties for you.",
                stage=ConversationStage.READY_FOR_SEARCH,
                requirements=updated_requirements,
                should_search_properties=True,
                search_params=self._convert_to_search_params(updated_requirements)
            )
        
        # Generate smart clarification message
        clarification_msg = await self._generate_smart_clarification(updated_requirements, message)
        
        session.context['conversation_stage'] = ConversationStage.COLLECTING_REQUIREMENTS
        
        return ConversationResponse(
            message=clarification_msg,
            stage=ConversationStage.COLLECTING_REQUIREMENTS,
            requirements=updated_requirements
        )
    
    async def _handle_collecting_requirements(self, message: str, session: ConversationSession, requirements: UserRequirements) -> ConversationResponse:
        """
        Handle requirement collection - extract info and check if complete
        """
        logger.info("🎯 STAGE 2: Collecting Requirements")
        
        # Update requirements with new message
        updated_requirements = await self._extract_requirements_ai(message, requirements)
        self._save_requirements_to_session(session, updated_requirements)
        
        # Check if we now have everything
        if updated_requirements.is_complete():
            session.context['conversation_stage'] = ConversationStage.READY_FOR_SEARCH
            return ConversationResponse(
                message="Perfect! I have all the details. Let me find the best properties for you.",
                stage=ConversationStage.READY_FOR_SEARCH,
                requirements=updated_requirements,
                should_search_properties=True,
                search_params=self._convert_to_search_params(updated_requirements)
            )
        
        # Still missing info - ask for more
        clarification_msg = await self._generate_smart_clarification(updated_requirements, message)
        
        return ConversationResponse(
            message=clarification_msg,
            stage=ConversationStage.COLLECTING_REQUIREMENTS,
            requirements=updated_requirements
        )
    
    async def _handle_ready_for_search(self, message: str, session: ConversationSession, requirements: UserRequirements) -> ConversationResponse:
        """
        Handle when we're ready to search - this triggers property search
        """
        logger.info("🎯 STAGE 3: Ready for Search")
        
        session.context['conversation_stage'] = ConversationStage.SHOWING_RESULTS
        
        return ConversationResponse(
            message="Searching for properties that match your criteria...",
            stage=ConversationStage.SHOWING_RESULTS,
            requirements=requirements,
            should_search_properties=True,
            search_params=self._convert_to_search_params(requirements)
        )
    
    async def _handle_showing_results(self, message: str, session: ConversationSession, requirements: UserRequirements) -> ConversationResponse:
        """
        Handle when properties are being shown - user might click "view more" or ask questions
        """
        logger.info("🎯 STAGE 4: Showing Results")
        
        message_lower = message.lower()
        
        # CRITICAL FIX: Check if user wants new search with different criteria
        new_search_keywords = [
            'show me', 'search for', 'find me', 'look for', 'i want', 'get me',
            'apartments', 'villas', 'properties', 'buy', 'rent', 'sale'
        ]
        
        if any(keyword in message_lower for keyword in new_search_keywords):
            logger.info("🔄 NEW_SEARCH detected in SHOWING_RESULTS - switching to search mode")
            session.context['conversation_stage'] = ConversationStage.READY_FOR_SEARCH
            
            # Extract new requirements and trigger search
            updated_requirements = await self._extract_requirements_ai(message, UserRequirements())
            self._save_requirements_to_session(session, updated_requirements)
            
            return ConversationResponse(
                message="Let me find those properties for you.",
                stage=ConversationStage.READY_FOR_SEARCH,
                requirements=updated_requirements,
                should_search_properties=True,
                search_params=self._convert_to_search_params(updated_requirements)
            )
        
        # Check if user wants to see different properties from current results
        if any(word in message_lower for word in ['other', 'different', 'more', 'cheaper', 'expensive']):
            # Modify search and get new results
            session.context['conversation_stage'] = ConversationStage.READY_FOR_SEARCH
            return ConversationResponse(
                message="Let me find different properties for you.",
                stage=ConversationStage.READY_FOR_SEARCH,
                requirements=requirements,
                should_search_properties=True,
                search_params=self._convert_to_search_params(requirements)
            )
        
        # User asking about specific property
        session.context['conversation_stage'] = ConversationStage.FOLLOW_UP
        return ConversationResponse(
            message=await self._generate_property_specific_response(message, session),
            stage=ConversationStage.FOLLOW_UP,
            requirements=requirements
        )
    
    async def _handle_follow_up(self, message: str, session: ConversationSession, requirements: UserRequirements) -> ConversationResponse:
        """
        Handle follow-up questions about properties
        """
        logger.info("🎯 STAGE 5: Follow-up")
        
        # Generate contextual response about properties
        response_msg = await self._generate_property_specific_response(message, session)
        
        return ConversationResponse(
            message=response_msg,
            stage=ConversationStage.FOLLOW_UP,
            requirements=requirements
        )
    
    async def _extract_requirements_ai(self, message: str, current_requirements: UserRequirements) -> UserRequirements:
        """
        Use AI to extract and update requirements from user message
        """
        try:
            extraction_prompt = f"""
Extract property requirements from this message. Update the existing requirements.

Current requirements: {current_requirements.dict()}
New message: "{message}"

Extract and return JSON with these fields:
{{
    "transaction_type": "buy|rent|null",
    "location": "string|null (Dubai area)",
    "budget_min": "number|null (in AED)",
    "budget_max": "number|null (in AED)", 
    "property_type": "string|null (villa, apartment, townhouse, penthouse, commercial, plot, residential, villa village, etc)",
    "bedrooms": "number|null",
    "special_features": ["array of strings"],
    "confidence_transaction": "float 0-1",
    "confidence_location": "float 0-1", 
    "confidence_budget": "float 0-1",
    "confidence_property": "float 0-1"
}}

IMPORTANT PARSING RULES:

BUDGET:
- "80k" or "80-100k" means 80,000 to 100,000 AED
- "1M" or "1.5M" means 1,000,000 to 1,500,000 AED  
- "2-3M" means 2,000,000 to 3,000,000 AED
- Always return budget values in actual AED (not thousands)
- Examples: "80k" → budget_min: 80000, "100k" → budget_max: 100000

LOCATION:
- "any location", "anywhere", "all areas", "any area" → location: "any"
- "nearby areas", "surrounding areas" → set location: "nearby" + keep current area context
- "expand search", "look nearby" → set location: "nearby"
- Specific areas like "Marina", "Downtown" → use as is

FLEXIBLE REQUIREMENTS:
- If user says "any budget" or "no budget limit" → leave budget fields null
- If user says "any location" → set location: "any"
- If user is flexible, set confidence to 0.8+ to indicate certainty about flexibility

Rules:
- Keep existing values if not mentioned
- Only update if new information is provided
- High confidence (0.8+) for explicit mentions
- Medium confidence (0.6-0.7) for implied
- Low confidence (0.3-0.5) for unclear
"""

            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": extraction_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Update current requirements with extracted data
            updated_requirements = current_requirements.copy()
            for key, value in extracted_data.items():
                if value is not None:
                    setattr(updated_requirements, key, value)
            
            return updated_requirements
            
        except Exception as e:
            logger.error(f"❌ AI extraction failed: {e}")
            return current_requirements
    
    async def _generate_smart_clarification(self, requirements: UserRequirements, original_message: str) -> str:
        """
        Generate intelligent clarification question based on what's missing
        Ask multiple questions in one turn when appropriate
        """
        missing = requirements.get_missing_requirements()
        
        if not missing:
            return "Perfect! I have all the information I need."
        
        # Create contextual clarification
        clarification_map = {
            "transaction_type": "Are you looking to *buy* or *rent* a property?",
            "location": "Which area in Dubai are you interested in? (Marina, Downtown, JBR, etc.)",
            "budget": "What's your budget range? (e.g., 80-100k for rent, 1-2M for purchase)",
            "property_type": "What type of property? (villa, apartment, townhouse, penthouse, commercial, plot, villa village, etc.)"
        }
        
        # Build smart question
        current_info = []
        if requirements.transaction_type:
            current_info.append(f"looking to {requirements.transaction_type}")
        if requirements.location:
            current_info.append(f"in {requirements.location}")
        if requirements.budget_min:
            # Convert budget to readable format
            def format_budget(amount):
                if amount >= 1000000:
                    return f"{amount/1000000:.1f}M".rstrip('0').rstrip('.')
                elif amount >= 1000:
                    return f"{amount/1000:.0f}k"
                else:
                    return str(amount)
            
            budget_str = format_budget(requirements.budget_min)
            if requirements.budget_max:
                budget_str += f"-{format_budget(requirements.budget_max)}"
            current_info.append(f"budget {budget_str}")
        
        # Create contextual intro
        intro = ""
        if current_info:
            intro = f"Great! I see you're {', '.join(current_info)}. "
        
        # Smart question grouping strategy
        if len(missing) >= 3 and not any(current_info):
            # Initial conversation - ask core questions together
            return "To find the perfect property for you, I need to know:\n\n1️⃣ Are you looking to *buy* or *rent*?\n2️⃣ Which area in Dubai? (Marina, Downtown, JBR, etc.)\n3️⃣ What's your budget range? (e.g., 80-100k for rent, 1-2M for purchase)"
        
        elif len(missing) >= 2 and "property_type" in missing:
            # Ask remaining questions together
            questions = []
            for miss in missing:
                if miss in clarification_map:
                    questions.append(clarification_map[miss])
            
            if len(questions) <= 2:
                return f"{intro}To find the perfect property, I need to know:\n\n• {questions[0]}\n• {questions[1] if len(questions) > 1 else ''}"
        
        # Single question for final missing item
        question = clarification_map.get(missing[0], "Could you provide more details?")
        return f"{intro}To find the perfect property, I need to know: {question}"
    
    def _convert_to_search_params(self, requirements: UserRequirements) -> Dict[str, Any]:
        """
        Convert AI-extracted requirements to search parameters
        """
        params = {}
        
        if requirements.transaction_type:
            params['sale_or_rent'] = 'sale' if requirements.transaction_type == 'buy' else 'rent'
        
        if requirements.location:
            location_lower = requirements.location.lower()
            # Skip location filter for flexible searches
            if location_lower not in ["any", "anywhere", "all areas", "any location", "nearby", "nearby areas"]:
                params['locality'] = requirements.location
            elif location_lower in ["nearby", "nearby areas"]:
                # For nearby searches, don't set locality to allow broader search
                logger.info(f"🌍 [LOCATION] Expanding search for nearby areas (removing location restriction)")
            
        if requirements.budget_min:
            if requirements.transaction_type == 'rent':
                params['min_rent_price_aed'] = requirements.budget_min
                if requirements.budget_max:
                    params['max_rent_price_aed'] = requirements.budget_max
            else:
                params['min_sale_price_aed'] = requirements.budget_min
                if requirements.budget_max:
                    params['max_sale_price_aed'] = requirements.budget_max
        
        if requirements.property_type:
            # Handle property type variations - match actual database values from your image
            prop_type = requirements.property_type.lower()
            if 'villa village' in prop_type:
                params['property_type'] = 'Villa village'
            elif 'villa' in prop_type:
                params['property_type'] = 'Villa'
            elif 'apartment' in prop_type or 'flat' in prop_type or 'bed' in prop_type:
                params['property_type'] = 'Apartment'
            elif 'penthouse' in prop_type:
                params['property_type'] = 'Penthouse'
            elif 'studio' in prop_type:
                params['property_type'] = 'Studio'
                params['bedrooms'] = 0
            elif 'townhouse' in prop_type or 'town house' in prop_type:
                params['property_type'] = 'Townhouse'
            elif 'residential' in prop_type:
                params['property_type'] = 'Residential'
            elif 'commercial' in prop_type:
                params['property_type'] = 'Commercial'
            elif 'plot' in prop_type:
                params['property_type'] = 'Plot'
            else:
                # Default fallback - try the value as-is first
                params['property_type'] = requirements.property_type.title()
        
        if requirements.bedrooms is not None:
            params['bedrooms'] = requirements.bedrooms
        
        # Debug logging
        logger.info(f"🔍 [SEARCH_PARAMS] Generated search parameters: {params}")
        logger.info(f"🔍 [REQUIREMENTS] From requirements: {requirements.dict()}")
        
        return params
    
    def _get_requirements_from_session(self, session: ConversationSession) -> UserRequirements:
        """
        Extract current requirements from session
        """
        req_data = session.context.get('user_requirements', {})
        return UserRequirements(**req_data)
    
    def _save_requirements_to_session(self, session: ConversationSession, requirements: UserRequirements):
        """
        Save requirements to session
        """
        session.context['user_requirements'] = requirements.dict()
        session.context['last_updated'] = time.time()
    
    async def _generate_property_specific_response(self, message: str, session: ConversationSession) -> str:
        """
        Generate response about specific properties with smart active property management
        """
        active_properties = session.context.get('active_properties', [])
        active_property_id = session.context.get('active_property_id')
        
        if not active_properties:
            return "I'd be happy to help! Could you clarify what you'd like to know about the properties?"
        
        # STEP 1: Check if user wants to switch to other properties or clear context
        switch_intent = self._detect_property_switch_intent(message)
        if switch_intent.get("wants_other_properties"):
            logger.info("🔄 User asking about other properties - clearing active property context")
            session.context['active_property_id'] = None
            return switch_intent.get("response", "Let me help you with other properties. Which specific property would you like to know about?")
        
        # STEP 2: Check if user is referencing a specific property by number/name
        property_reference = self._extract_property_reference(message)
        if property_reference:
            logger.info(f"🎯 User referenced specific property: {property_reference}")
            
            # Get specific property details
            from utils.session_manager import SessionManager
            session_manager = SessionManager()
            specific_property = session_manager.get_property_by_reference(session.user_id, property_reference)
            
            if specific_property:
                # UPDATE ACTIVE PROPERTY: Set this as the new active property
                new_property_id = specific_property.get('id') or specific_property.get('original_property_id')
                if new_property_id:
                    session.context['active_property_id'] = new_property_id
                    logger.info(f"🔄 Updated active property to: {new_property_id}")
                
                # Format and return detailed property information
                return self._format_property_details(specific_property, property_reference)
            else:
                # Property reference not found
                return f"I couldn't find property {property_reference} in our current results. Could you specify which property you're interested in? We found {len(active_properties)} properties for you."
        
        # STEP 3: Use active property for ANY property-specific query using AI intent analysis
        if active_property_id:
            logger.info(f"🏠 Using active property {active_property_id} for query: '{message}'")
            
            # Get active property details
            from tools.property_details_tool import property_details_tool
            active_property_data = await property_details_tool.get_property_details(active_property_id)
            
            if active_property_data:
                # Use AI to understand intent instead of manual detection
                intent_analysis = await self._analyze_user_intent(message, session)
                
                if intent_analysis.get("is_location_request"):
                    logger.info(f"🗺️ AI detected location request for active property: {active_property_id}")
                    
                    # Use property location service intelligently
                    from tools.property_location_service import property_location_service
                    
                    # Let the location service determine if it's nearest places or general location
                    location_intent = property_location_service.detect_location_intent(message)
                    
                    # Extract user phone from session
                    user_phone = session.user_id.replace('+', '')  # Remove + if present
                    whatsapp_account = session.context.get('whatsapp_business_account', '543107385407043')
                    
                    if location_intent.get("intent") == "find_nearest" and location_intent.get("query"):
                        # Handle nearest places request
                        return await property_location_service.find_nearest_places(
                            property_id=active_property_id,
                            query=location_intent["query"],
                            user_phone=user_phone
                        )
                    else:
                        # Handle general location request
                        return await property_location_service.handle_location_request(
                            property_id=active_property_id,
                            user_phone=user_phone,
                            whatsapp_account=whatsapp_account,
                            message=message
                        )
                
                # For NON-location queries about the active property, use AI with property context
                return await self._generate_contextual_property_response(message, active_property_data)
            else:
                logger.warning(f"❌ Could not fetch details for active property: {active_property_id}")
                # Clear invalid active property ID
                session.context['active_property_id'] = None
        
        # STEP 4: No active property or specific reference - general property question
        return await self._generate_general_property_response(message, active_properties)
    
    def _detect_property_switch_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect if user wants to switch to other properties or clear current context
        """
        message_lower = message.lower().strip()
        
        # Keywords that indicate wanting to see other properties
        other_keywords = [
            'other properties', 'different properties', 'show me others', 'other options',
            'see more', 'what else', 'alternatives', 'other ones', 'different ones',
            'show other', 'more properties', 'other listings'
        ]
        
        # Keywords that indicate general browsing (not specific to current property)
        general_keywords = [
            'show me all', 'list properties', 'list all properties', 'what properties', 'available properties',
            'all options', 'browse properties', 'property list'
        ]
        
        for keyword in other_keywords:
            if keyword in message_lower:
                return {
                    "wants_other_properties": True,
                    "response": f"Sure! Let me show you other properties. You can ask about any specific property by saying 'Tell me about property 2' or 'Show me property details'. Which property would you like to explore?"
                }
        
        for keyword in general_keywords:
            if keyword in message_lower:
                return {
                    "wants_other_properties": True,
                    "response": f"I can help you browse all the properties. Which specific property number would you like to know more about? (e.g., 'property 1', 'property 2', etc.)"
                }
        
        return {"wants_other_properties": False}
    
    async def _analyze_user_intent(self, message: str, session: ConversationSession) -> Dict[str, Any]:
        """
        INTELLIGENT AI-based intent analysis instead of stupid regex patterns
        """
        try:
            # Get current context
            has_active_properties = bool(session.context.get('active_properties'))
            has_active_property_id = bool(session.context.get('active_property_id'))
            current_stage = session.context.get('conversation_stage', ConversationStage.USER_INITIATED)
            
            context_info = f"""
Current conversation context:
- Stage: {current_stage}
- Has active properties: {has_active_properties}
- Has active property selected: {has_active_property_id}
- Previous interactions: {"Yes" if has_active_properties else "No"}
"""

            analysis_prompt = f"""
You are analyzing user intent in a real estate conversation. Based on the context and user message, determine the user's intent.

{context_info}

User message: "{message}"

Analyze and return JSON with:
{{
    "is_fresh_search": boolean,  // true if user wants to start a new property search
    "is_location_request": boolean,  // true if asking about location/map/directions/nearby places
    "is_property_question": boolean,  // true if asking about specific property details
    "is_continuing_conversation": boolean,  // true if following up on existing conversation
    "intent_category": "search|location|property_details|followup|general",
    "confidence": float  // 0-1 how confident you are
}}

RULES FOR ANALYSIS:
1. If user says things like "show location", "nearest hospital", "where is this", "send map" → is_location_request = true, is_fresh_search = false
2. If user wants new property search ("show me villas", "find apartments", "I want to buy") → is_fresh_search = true
3. If asking about current property details → is_property_question = true, is_fresh_search = false
4. If user is clearly continuing existing conversation → is_continuing_conversation = true, is_fresh_search = false
5. Use CONTEXT: if user has active properties and asks location questions, it's about those properties, NOT a fresh search

Be intelligent - understand context and intent, don't rely on keywords!
"""

            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": analysis_prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200
            )
            
            analysis = json.loads(response.choices[0].message.content)
            logger.info(f"🧠 AI Intent Analysis: {analysis}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ AI intent analysis failed: {e}")
            # Safe fallback - assume continuing conversation if we have context
            return {
                "is_fresh_search": not (has_active_properties or has_active_property_id),
                "is_location_request": any(word in message.lower() for word in ['location', 'where', 'map', 'nearest', 'nearby']),
                "is_property_question": has_active_property_id,
                "is_continuing_conversation": has_active_properties or has_active_property_id,
                "intent_category": "general",
                "confidence": 0.6
            }
    
    async def _generate_contextual_property_response(self, message: str, property_data: Dict[str, Any]) -> str:
        """
        Generate AI response about specific property using property context
        """
        try:
            # Extract key property information for context
            property_type = property_data.get('property_type', 'Property')
            bedrooms = property_data.get('bedrooms', 0)
            title = property_data.get('title', '') or property_data.get('building_name', '')
            price = property_data.get('sale_price_aed') or property_data.get('rent_price_aed')
            
            address = property_data.get('address', {})
            if isinstance(address, str):
                try:
                    import json
                    address = json.loads(address)
                except:
                    address = {}
            
            locality = address.get('locality', 'Dubai') if address else 'Dubai'
            
            # Build context-rich prompt
            property_context = f"""
Property Details:
- Type: {bedrooms}BR {property_type}
- Title: {title}
- Location: {locality}
- Price: AED {price:,} if price else 'Contact for price'
"""
            
            response_prompt = f"""
You are a helpful real estate agent. The user is asking about a specific property they're interested in.

{property_context}

User question: "{message}"

Provide a helpful, detailed response about this specific property. If the user is asking about features, amenities, price, size, or any property details, use the information provided. If you don't have specific information, acknowledge that and offer to help them get more details or schedule a viewing.

Keep response concise but informative, and always offer next steps like viewing scheduling or getting more information.
"""
            
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": response_prompt}],
                temperature=0.7,
                max_tokens=200
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ Contextual property response failed: {e}")
            # Fallback to basic property details formatting
            return self._format_property_details(property_data, "current")
    
    async def _generate_general_property_response(self, message: str, active_properties: list) -> str:
        """
        Generate response for general property questions when no active property is set
        """
        try:
            response_prompt = f"""
User is asking about properties they were shown. Generate a helpful response.

User question: "{message}"
Number of properties shown: {len(active_properties)}

Generate a concise, helpful response. Guide them to ask about specific properties by number (e.g., "Tell me about property 1") or ask about specific aspects they want to know.
"""
            
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": response_prompt}],
                temperature=0.7,
                max_tokens=150
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"❌ General property response generation failed: {e}")
            return f"I'd be happy to help with your question about the properties. You can ask about specific properties by saying 'Tell me about property 1' or ask about specific details you'd like to know. We found {len(active_properties)} properties for you."
    
    def _extract_property_reference(self, message: str) -> Optional[str]:
        """
        Extract property reference from user message (e.g., "property 1", "first one", "2nd property")
        """
        import re
        
        message_lower = message.lower().strip()
        
        # Pattern 1: "property 1", "property #1", "property number 1"
        match = re.search(r'property\s*(?:number\s*|#\s*)?(\d+)', message_lower)
        if match:
            return match.group(1)
        
        # Pattern 2: "1st", "2nd", "3rd", etc.
        match = re.search(r'(\d+)(?:st|nd|rd|th)', message_lower)
        if match:
            return match.group(1)
        
        # Pattern 3: "first", "second", "third"
        ordinal_words = {
            'first': '1', 'second': '2', 'third': '3', 'fourth': '4', 'fifth': '5',
            'one': '1', 'two': '2', 'three': '3', 'four': '4', 'five': '5'
        }
        for word, num in ordinal_words.items():
            if word in message_lower:
                return num
        
        # Pattern 4: Just a number at the beginning/end
        match = re.search(r'\b(\d+)\b', message_lower)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 20:  # Reasonable range for property references
                return str(num)
        
        return None
    
    def _format_property_details(self, property_data: Dict[str, Any], reference: str) -> str:
        """
        Format detailed property information for WhatsApp
        """
        try:
            # Handle different property data structures
            if hasattr(property_data, 'dict'):
                # PropertyResult object
                prop = property_data.dict()
            elif isinstance(property_data, dict):
                # Already a dictionary
                prop = property_data
            else:
                # Convert object to dict
                prop = dict(property_data)
            
            # Extract basic info
            property_type = prop.get('property_type', 'Property')
            bedrooms = prop.get('bedrooms', 0)
            bathrooms = prop.get('bathrooms', 0)
            
            # Format price
            price_str = "Price on request"
            if prop.get('sale_price_aed'):
                price_str = f"AED {prop['sale_price_aed']:,}"
            elif prop.get('rent_price_aed'):
                price_str = f"AED {prop['rent_price_aed']:,}/year"
            
            # Extract location
            address = prop.get('address', {})
            if isinstance(address, str):
                try:
                    import json
                    address = json.loads(address)
                except:
                    address = {}
            
            location = "Dubai"
            if isinstance(address, dict):
                location = address.get('locality') or address.get('city') or "Dubai"
                full_address = address.get('full_address') or address.get('street_address')
                if full_address:
                    location = f"{full_address}, {location}"
            
            building_name = prop.get('building_name', '')
            if building_name:
                location = f"{building_name}, {location}"
            
            # Format size
            size_str = ""
            if prop.get('bua_sqft'):
                size_str = f"📐 {prop['bua_sqft']:,} sqft"
            
            # Extract features
            features = []
            if prop.get('study'):
                features.append("study")
            if prop.get('maid_room'):
                features.append("maid room")
            if prop.get('landscaped_garden'):
                features.append("garden")
            if prop.get('covered_parking_spaces') or prop.get('covered_parking'):
                parking = prop.get('covered_parking_spaces') or prop.get('covered_parking', 1)
                features.append(f"{parking} parking")
            if prop.get('park_pool_view'):
                features.append("pool/park view")
            
            features_str = ""
            if features:
                features_str = f"✨ {' • '.join(features)}"
            
            # Format response
            response = f"""🏠 **Property {reference} Details:**

🏢 *{bedrooms}BR {property_type}*
💰 {price_str}
📍 {location}
🚿 {bathrooms} bathroom{'s' if bathrooms != 1 else ''}"""
            
            if size_str:
                response += f"\n{size_str}"
            
            if features_str:
                response += f"\n{features_str}"
            
            response += "\n\n📞 Would you like to book a viewing or need more information about this property?"
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Property formatting error: {e}")
            return f"I have the details for property {reference}, but there was an issue formatting them. Let me know what specific information you'd like to know!"


# Global instance
unified_engine = UnifiedConversationEngine()
