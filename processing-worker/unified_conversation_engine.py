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

# Import sophisticated search components
from tools.sophisticated_search_pipeline import (
    sophisticated_search_pipeline, 
    SearchCriteria, 
    search_with_sophisticated_intelligence
)
from tools.sophisticated_response_generator import generate_sophisticated_response

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
    sophisticated_search_criteria: Optional[Dict[str, Any]] = None
    use_sophisticated_search: bool = True  # Default to sophisticated search
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
            
            # Handle pagination requests first (before fresh search detection)
            if intent_analysis.get("is_pagination_request") or intent_analysis.get("intent_category") == "pagination":
                logger.info("📄 PAGINATION_REQUEST detected by AI - handling pagination")
                # Don't clear context! We need the stored properties for pagination
                return await self._handle_pagination_request(message, session, self._get_requirements_from_session(session))
            
            # Handle general questions when there's an active property
            has_active_property_id = bool(session.context.get('active_property_id'))
            if (has_active_property_id and 
                intent_analysis.get("intent_category") == "general" and 
                not intent_analysis.get("is_property_question")):
                logger.info("💬 GENERAL_QUESTION with active property - providing brief answer with property options")
                return await self._handle_general_question_with_active_property(message, session)
            
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
            
            # Prepare both legacy and sophisticated search parameters
            search_criteria = self._convert_to_sophisticated_search_criteria(updated_requirements)
            
            return ConversationResponse(
                message="Perfect! I have all the details I need. Let me find properties for you.",
                stage=ConversationStage.READY_FOR_SEARCH,
                requirements=updated_requirements,
                should_search_properties=True,
                search_params=self._convert_to_search_params(updated_requirements),
                sophisticated_search_criteria=search_criteria.to_dict(),
                use_sophisticated_search=True
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
            
            # Prepare both legacy and sophisticated search parameters
            search_criteria = self._convert_to_sophisticated_search_criteria(updated_requirements)
            
            return ConversationResponse(
                message="Perfect! I have all the details. Let me find the best properties for you.",
                stage=ConversationStage.READY_FOR_SEARCH,
                requirements=updated_requirements,
                should_search_properties=True,
                search_params=self._convert_to_search_params(updated_requirements),
                sophisticated_search_criteria=search_criteria.to_dict(),
                use_sophisticated_search=True
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
        Handle when we're ready to search - this triggers sophisticated property search
        """
        logger.info("🎯 STAGE 3: Ready for Search - Using Sophisticated Search")
        
        session.context['conversation_stage'] = ConversationStage.SHOWING_RESULTS
        
        # Prepare sophisticated search criteria
        search_criteria = self._convert_to_sophisticated_search_criteria(requirements)
        
        return ConversationResponse(
            message="Searching for properties that match your criteria...",
            stage=ConversationStage.SHOWING_RESULTS,
            requirements=requirements,
            should_search_properties=True,
            search_params=self._convert_to_search_params(requirements),
            sophisticated_search_criteria=search_criteria.to_dict(),
            use_sophisticated_search=True
        )
    
    async def _handle_showing_results(self, message: str, session: ConversationSession, requirements: UserRequirements) -> ConversationResponse:
        """
        Handle when properties are being shown - user might click "view more" or ask questions
        
        Note: AI intent analysis at top level should catch fresh searches and pagination,
        but this function provides fallback logic for robustness.
        """
        logger.info("🎯 STAGE 4: Showing Results")
        
        # FALLBACK: If AI missed a fresh search (location/budget/type change), extract and check
        logger.info("🔍 FALLBACK: Checking if AI missed a fresh search request")
        potential_new_requirements = await self._extract_requirements_ai(message, UserRequirements())
        
        # Check for significant changes that indicate fresh search
        has_location_change = (
            potential_new_requirements.location and 
            potential_new_requirements.location != requirements.location and
            potential_new_requirements.confidence_location >= 0.7 and
            potential_new_requirements.location.lower() not in ["any", "anywhere", "all areas", "nearby"]
        )
        
        has_budget_change = (
            (potential_new_requirements.budget_min and potential_new_requirements.budget_min != requirements.budget_min) or
            (potential_new_requirements.budget_max and potential_new_requirements.budget_max != requirements.budget_max)
        ) and potential_new_requirements.confidence_budget >= 0.7
        
        has_property_type_change = (
            potential_new_requirements.property_type and 
            potential_new_requirements.property_type != requirements.property_type and
            potential_new_requirements.confidence_property >= 0.7
        )
        
        has_transaction_change = (
            potential_new_requirements.transaction_type and 
            potential_new_requirements.transaction_type != requirements.transaction_type and
            potential_new_requirements.confidence_transaction >= 0.7
        )
        
        # If any significant change detected, trigger fresh search
        if has_location_change or has_budget_change or has_property_type_change or has_transaction_change:
            logger.info(f"🔄 FALLBACK_FRESH_SEARCH detected:")
            logger.info(f"   Location change: {has_location_change}")
            logger.info(f"   Budget change: {has_budget_change}")  
            logger.info(f"   Property type change: {has_property_type_change}")
            logger.info(f"   Transaction change: {has_transaction_change}")
            
            # Merge changes with existing requirements
            merged_requirements = requirements.copy()
            if has_location_change:
                merged_requirements.location = potential_new_requirements.location
                merged_requirements.confidence_location = potential_new_requirements.confidence_location
            if has_budget_change:
                if potential_new_requirements.budget_min:
                    merged_requirements.budget_min = potential_new_requirements.budget_min
                if potential_new_requirements.budget_max:
                    merged_requirements.budget_max = potential_new_requirements.budget_max
                merged_requirements.confidence_budget = potential_new_requirements.confidence_budget
            if has_property_type_change:
                merged_requirements.property_type = potential_new_requirements.property_type
                merged_requirements.confidence_property = potential_new_requirements.confidence_property
            if has_transaction_change:
                merged_requirements.transaction_type = potential_new_requirements.transaction_type
                merged_requirements.confidence_transaction = potential_new_requirements.confidence_transaction
            
            self._save_requirements_to_session(session, merged_requirements)
            session.context['conversation_stage'] = ConversationStage.READY_FOR_SEARCH
            
            # Prepare sophisticated search criteria
            search_criteria = self._convert_to_sophisticated_search_criteria(merged_requirements)
            
            return ConversationResponse(
                message="Let me find properties with your updated criteria.",
                stage=ConversationStage.READY_FOR_SEARCH,
                requirements=merged_requirements,
                should_search_properties=True,
                search_params=self._convert_to_search_params(merged_requirements),
                sophisticated_search_criteria=search_criteria.to_dict(),
                use_sophisticated_search=True
            )
        
        # FALLBACK: Check for pagination request that AI might have missed
        message_lower = message.lower().strip()
        pagination_indicators = [
            'show more', 'more properties', 'next batch', 'more results',
            'see more', 'view more', 'load more', 'get more',
            # Handle typos
            'shoe more', 'show mor', 'more prop', 'next prop'
        ]
        
        if any(indicator in message_lower for indicator in pagination_indicators):
            logger.info("📄 FALLBACK: Pagination request detected that AI missed")
            return await self._handle_pagination_request(message, session, requirements)
        
        # Default: User asking about specific property or general question
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
    "transaction_type": null | "buy" | "rent",
    "location": null | "al Barsha" | "Marina" | "JBR" | "Downtown" | "Business Bay" | "etc",
    "budget_min": null | 80000 | 100000,
    "budget_max": null | 100000 | 150000, 
    "property_type": null | "villa" | "apartment" | "townhouse" | "penthouse" | "studio",
    "bedrooms": null | 1 | 2 | 3 | 4,
    "special_features": ["array of strings"],
    "confidence_transaction": "float 0-1",
    "confidence_location": "float 0-1", 
    "confidence_budget": "float 0-1",
    "confidence_property": "float 0-1"
}}

IMPORTANT PARSING RULES:

BUDGET:
- "80k" or "80-100k" means 80,000 to 100,000 AED
- "1M" or "1.5M" means UP TO that amount (budget_max), not exact match
- "1.5M" → budget_max: 1500000, budget_min: null (find properties up to 1.5M)
- "2-3M" means 2,000,000 to 3,000,000 AED (both min and max specified)  
- Always return budget values in actual AED (not thousands)
- Examples: "80k" → budget_max: 80000, "1.5M" → budget_max: 1500000

LOCATION EXTRACTION (CRITICAL):
- Extract ANY location mentioned: "al Barsha", "Marina", "JBR", "Downtown", "Business Bay", "Jumeirah", etc.
- Patterns: "options in [area]", "properties in [area]", "what about [area]", "different area", "other location"
- "What are the other options in al Barsha" → location: "al Barsha"
- "Show me Marina properties" → location: "Marina"  
- "Any apartments in JBR" → location: "JBR"
- Set high confidence (0.9+) when location is explicitly mentioned
- "any location", "anywhere" → location: "any"
- Common Dubai areas: al Barsha, Marina, Dubai Marina, JBR, Downtown, Business Bay, Jumeirah, DIFC, etc.

PROPERTY TYPE EXTRACTION (CRITICAL):
- Extract ANY property type mentioned: "villa", "apartment", "flat", "townhouse", "penthouse", "studio", "commercial", "plot"
- Patterns: "show me [type]", "[type] properties", "looking for [type]", "I want [type]"
- "show me villas instead" → property_type: "villa"
- "apartments in Marina" → property_type: "apartment"
- "looking for townhouses" → property_type: "townhouse"
- "I want a penthouse" → property_type: "penthouse"
- "2BR apartment" → property_type: "apartment", bedrooms: 2
- Set high confidence (0.9+) when property type is explicitly mentioned
- Handle variations: "flat" = "apartment", "2BR" = bedrooms: 2

TRANSACTION TYPE EXTRACTION (CRITICAL):
- Extract ANY transaction mentioned: "buy", "purchase", "rent", "lease", "sale"
- Patterns: "I want to [transaction]", "looking to [transaction]", "switch to [transaction]"
- "I want to buy now" → transaction_type: "buy"
- "looking to rent" → transaction_type: "rent"  
- "switch to purchase" → transaction_type: "buy"
- "for sale" → transaction_type: "buy"
- "rental properties" → transaction_type: "rent"
- Set high confidence (0.9+) when transaction type is explicitly mentioned

FLEXIBLE REQUIREMENTS:
- If user says "any budget" or "no budget limit" → leave budget fields null
- If user says "any location" → set location: "any"
- If user says "any property type" → leave property_type null
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
            logger.info(f"🔍 RAW_EXTRACTION: {extracted_data}")
            
            # Clean up any "null" strings that should be None (AI sometimes returns "null" as string)
            for key, value in extracted_data.items():
                if value == "null" or value == "None":
                    extracted_data[key] = None
            
            logger.info(f"🔍 CLEANED_EXTRACTION: {extracted_data}")
            
            # Update current requirements with extracted data
            updated_requirements = current_requirements.copy()
            for key, value in extracted_data.items():
                if value is not None:
                    setattr(updated_requirements, key, value)
            
            logger.info(f"🔍 FINAL_REQUIREMENTS: {updated_requirements.dict()}")
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
        if requirements.property_type:
            current_info.append(f"{requirements.property_type}s")  # "villas", "apartments"  
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
            return "To find the perfect property for you, I need to know:\n\n1️⃣ Are you looking to *buy* or *rent*?\n2️⃣ Which area in Dubai? (Marina, Downtown, JBR, etc.)\n3️⃣ What type of property? (apartment, villa, studio, etc.)"
        
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
        Convert AI-extracted requirements to search parameters (legacy format)
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
    
    def _convert_to_sophisticated_search_criteria(self, requirements: UserRequirements) -> SearchCriteria:
        """
        🚀 Convert AI-extracted requirements to SearchCriteria for sophisticated search
        """
        # Handle location filtering for sophisticated search
        location = requirements.location
        if requirements.location:
            location_lower = requirements.location.lower()
            if location_lower in ["any", "anywhere", "all areas", "any location", "nearby", "nearby areas"]:
                location = None  # Let sophisticated search handle location flexibility
        
        # Normalize property type for sophisticated search
        property_type = None
        if requirements.property_type:
            prop_type = requirements.property_type.lower()
            if 'villa village' in prop_type:
                property_type = 'Villa village'
            elif 'villa' in prop_type:
                property_type = 'Villa'
            elif 'apartment' in prop_type or 'flat' in prop_type or 'bed' in prop_type:
                property_type = 'Apartment'
            elif 'penthouse' in prop_type:
                property_type = 'Penthouse'
            elif 'studio' in prop_type:
                property_type = 'Studio'
            elif 'townhouse' in prop_type or 'town house' in prop_type:
                property_type = 'Townhouse'
            elif 'residential' in prop_type:
                property_type = 'Residential'
            elif 'commercial' in prop_type:
                property_type = 'Commercial'
            elif 'plot' in prop_type:
                property_type = 'Plot'
            else:
                property_type = requirements.property_type.title()
        
        # Create SearchCriteria object
        criteria = SearchCriteria(
            transaction_type=requirements.transaction_type,
            location=location,
            budget_min=requirements.budget_min,
            budget_max=requirements.budget_max,
            property_type=property_type,
            bedrooms=requirements.bedrooms
        )
        
        logger.info(f"🧠 [SOPHISTICATED_SEARCH] Generated criteria: {criteria.to_dict()}")
        
        return criteria
    
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
                    
                    # Use Smart Location Assistant for comprehensive location handling
                    from tools.smart_location_assistant import smart_location_assistant
                    
                    # Extract user phone from session
                    user_phone = session.user_id.replace('+', '')  # Remove + if present
                    whatsapp_account = session.context.get('whatsapp_business_account', '543107385407043')
                    
                    # Let Smart Location Assistant handle all location requests with AI routing
                    return await smart_location_assistant.handle_location_request(
                        property_id=active_property_id,
                        user_phone=user_phone,
                        whatsapp_account=whatsapp_account,
                        user_message=message
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
            
            # Check pagination context
            all_available_properties = session.context.get('all_available_properties', [])
            properties_shown = session.context.get('properties_shown', 0)
            has_pagination_context = bool(all_available_properties and len(all_available_properties) > properties_shown)
            
            # Get current user requirements for context
            current_requirements = self._get_requirements_from_session(session)
            
            context_info = f"""
Current conversation context:
- Stage: {current_stage}  
- Has active properties: {has_active_properties}
- Has active property selected: {has_active_property_id}
- Previous interactions: {"Yes" if has_active_properties else "No"}
- PAGINATION CONTEXT: {len(all_available_properties)} total properties available, {properties_shown} already shown
- Can show more properties: {has_pagination_context}

CURRENT USER REQUIREMENTS:
- Transaction Type: {current_requirements.transaction_type or "Not specified"}
- Location: {current_requirements.location or "Not specified"} 
- Property Type: {current_requirements.property_type or "Not specified"}
- Budget: {f"{current_requirements.budget_min}-{current_requirements.budget_max}" if current_requirements.budget_min or current_requirements.budget_max else "Not specified"}
"""

            analysis_prompt = f"""
You are analyzing user intent in a real estate conversation. Based on the context and user message, determine the user's intent.

{context_info}

User message: "{message}"

IMPORTANT: If there's an active property selected, determine if the user's message is actually ABOUT that specific property or just a general question. Only set is_property_question=true if they're asking about details, features, or actions related to the specific selected property.

Examples of property-specific questions: "How many bathrooms?", "Is parking included?", "Can I see photos?", "What floor is it on?"
Examples of general questions: "Hello", "What's the weather?", "How are you?", "Tell me about Dubai", "What other properties do you have?"

Analyze and return JSON with:
{{
    "is_fresh_search": boolean,  // true if user wants to start a new property search
    "is_location_request": boolean,  // true if asking about location/map/directions/nearby places
    "is_property_question": boolean,  // true if asking about specific property details
    "is_continuing_conversation": boolean,  // true if following up on existing conversation
    "is_pagination_request": boolean,  // true if asking for more properties (show more, next batch, etc.)
    "intent_category": "search|location|property_details|followup|pagination|general",
    "confidence": float  // 0-1 how confident you are
}}

CRITICAL ANALYSIS RULES - COMPARE CURRENT vs NEW:

1. **LOCATION CHANGE DETECTION**:
   - CURRENT LOCATION: {current_requirements.location or "None"}
   - If user mentions ANY different location → is_fresh_search = true
   - Examples: "options in al Barsha", "what about JBR", "properties in Marina"
   - If current is "Marina" and user says "al Barsha" → NEW SEARCH
   - If current is "JBR" and user says "Downtown" → NEW SEARCH

2. **BUDGET CHANGE DETECTION**:
   - CURRENT BUDGET: {f"{current_requirements.budget_min or 'None'} - {current_requirements.budget_max or 'None'}" if current_requirements.budget_min or current_requirements.budget_max else "None"}
   - If user mentions different budget → is_fresh_search = true
   - Examples: "increase budget to 150k", "change budget", "under 80k", "1M budget"
   - If current is "100k max" and user says "150k" → NEW SEARCH
   - If current is "None" and user says "80k budget" → NEW SEARCH

3. **PROPERTY TYPE CHANGE DETECTION**:
   - CURRENT PROPERTY TYPE: {current_requirements.property_type or "None"}
   - If user mentions different property type → is_fresh_search = true  
   - Examples: "show me villas instead", "apartments", "townhouses", "studios"
   - If current is "Apartment" and user says "villas" → NEW SEARCH
   - If current is "Villa" and user says "apartments" → NEW SEARCH

4. **TRANSACTION TYPE CHANGE DETECTION**:
   - CURRENT TRANSACTION: {current_requirements.transaction_type or "None"}
   - If user mentions different transaction → is_fresh_search = true
   - Examples: "I want to buy now", "switch to rent", "looking to purchase"
   - If current is "rent" and user says "buy" → NEW SEARCH
   - If current is "buy" and user says "rent" → NEW SEARCH

5. **PAGINATION DETECTION**:
   - "show more", "more properties", "next batch" → is_pagination_request = true, is_fresh_search = false
   - Handle typos: "shoe more", "more prop" → still pagination

6. **PROPERTY DETAILS**:
   - Asking about specific properties → is_property_question = true, is_fresh_search = false

7. **LOCATION SERVICES**:
   - "nearest hospital", "send map", "directions", "share location", "send brochure", "brochure" → is_location_request = true, is_fresh_search = false

**BE SMART**: Don't rely on keywords. Understand INTENT. If user is clearly asking about a different location than current context, it's a fresh search!

Be intelligent - understand context and intent, don't rely on keywords! Handle typos gracefully.
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
            
            # Smart fallback logic - don't assume everything is property-related just because there's an active property
            message_lower = message.lower()
            
            # Property-specific keywords that indicate the user is asking about the active property
            property_keywords = [
                'bathroom', 'bedroom', 'kitchen', 'balcony', 'parking', 'pool', 'gym', 'garden',
                'floor', 'sqft', 'square', 'size', 'area', 'furnish', 'view', 'direction',
                'price', 'rent', 'sale', 'photo', 'image', 'visit', 'showing', 'available',
                'feature', 'amenity', 'include', 'detail', 'spec', 'when built', 'age',
                'maintenance', 'chiller', 'dewa', 'utilities'
            ]
            
            # General greeting/conversation keywords
            general_keywords = [
                'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
                'how are you', 'thank you', 'thanks', 'weather', 'dubai', 'tell me about',
                'what other', 'show me more', 'different', 'other options'
            ]
            
            # Determine if this is likely a property question or general question
            is_likely_property_question = has_active_property_id and any(keyword in message_lower for keyword in property_keywords)
            is_likely_general_question = any(keyword in message_lower for keyword in general_keywords)
            
            # If it's clearly general, don't treat as property question even with active property
            is_property_question = is_likely_property_question and not is_likely_general_question
            
            return {
                "is_fresh_search": not (has_active_properties or has_active_property_id),
                "is_location_request": any(word in message_lower for word in ['location', 'where', 'map', 'nearest', 'nearby']),
                "is_property_question": is_property_question,
                "is_continuing_conversation": has_active_properties or has_active_property_id,
                "intent_category": "property_details" if is_property_question else "general",
                "confidence": 0.6
            }
    
    async def _handle_general_question_with_active_property(self, message: str, session: ConversationSession) -> ConversationResponse:
        """
        Handle general questions when there's an active property selected
        Provide brief answer and offer property options
        """
        try:
            # Special handling for name questions
            message_lower = message.lower()
            if any(phrase in message_lower for phrase in ['what is my name', "what's my name", 'my name is', 'i am', "i'm"]):
                # Get user name from session context
                user_name = session.context.get('user_name')
                
                if 'what' in message_lower and 'name' in message_lower:
                    # User asking for their name
                    if user_name:
                        brief_answer = f"Your name is {user_name}!"
                    else:
                        brief_answer = "I don't have your name on record yet. Feel free to tell me!"
                elif 'my name is' in message_lower or 'i am' in message_lower or "i'm" in message_lower:
                    # User telling us their name - extract it
                    import re
                    name_patterns = [
                        r'my name is (\w+)', 
                        r"i'?m (\w+)", 
                        r'i am (\w+)'
                    ]
                    
                    extracted_name = None
                    for pattern in name_patterns:
                        match = re.search(pattern, message_lower)
                        if match:
                            extracted_name = match.group(1).title()
                            break
                    
                    if extracted_name:
                        # Store the name in session
                        session.context['user_name'] = extracted_name
                        brief_answer = f"Nice to meet you, {extracted_name}!"
                    else:
                        brief_answer = "Thanks for introducing yourself!"
                else:
                    brief_answer = "Thanks for your message!"
            else:
                # Generate a brief answer to other general questions using AI
                response_prompt = f"""
You are a helpful real estate assistant. The user asked: "{message}"

This appears to be a general question (not about a specific property). Provide a brief, helpful answer in 1-2 sentences. Keep it concise and friendly.

Examples:
- "Hello" → "Hi there! I'm here to help you with your property search."
- "How are you?" → "I'm doing great, thanks for asking!"  
- "Tell me about Dubai" → "Dubai is an amazing city with world-class amenities and diverse neighborhoods."
- "What's the weather like?" → "Dubai generally has sunny, warm weather year-round."

Give a brief, natural response:
"""
                
                try:
                    ai_response = await self.openai.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": response_prompt}],
                        temperature=0.7,
                        max_tokens=100
                    )
                    brief_answer = ai_response.choices[0].message.content.strip()
                except:
                    # Fallback for general responses
                    brief_answer = "Thanks for your question!"
            
            # Add the follow-up question about property options
            full_response = f"{brief_answer}\n\nWould you like to see more properties or learn more details about the current property?"
            
            # Return as a simple response (no search needed)
            return ConversationResponse(
                message=full_response,
                stage=ConversationStage.FOLLOW_UP,
                should_search_properties=False,
                use_sophisticated_search=False,
                requirements=self._get_requirements_from_session(session)
            )
            
        except Exception as e:
            logger.error(f"❌ Error handling general question: {e}")
            # Safe fallback
            return ConversationResponse(
                message="Thanks for your question! Would you like to see more properties or learn more details about the current property?",
                stage=ConversationStage.FOLLOW_UP,
                should_search_properties=False,
                use_sophisticated_search=False,
                requirements=self._get_requirements_from_session(session)
            )
    
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
You are a helpful property assistant. Answer the user's question about this specific property directly and naturally.

{property_context}

User question: "{message}"

IMPORTANT RULES:
- Answer directly and naturally like a helpful assistant
- Do NOT use formal letter templates or signatures  
- Do NOT include placeholders like "[Your Name]" or "[Contact Information]"
- Keep responses conversational and friendly
- If you don't have specific information, just say so and offer to help get more details
- End with a helpful question or suggestion about next steps

Provide a helpful, natural response:"""
            
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
        FIXED: Don't match numbers that are clearly budget amounts or other contexts
        """
        import re
        
        message_lower = message.lower().strip()
        
        # EXCLUDE budget/price contexts - these are NOT property references
        budget_contexts = [
            'budget', 'price', 'cost', 'aed', 'million', 'thousand', 'k', 'm',
            'increase', 'decrease', 'change', 'set', 'my budget', 'the budget'
        ]
        
        # If message contains budget/price context, don't extract property numbers
        if any(context in message_lower for context in budget_contexts):
            logger.info(f"🚫 Skipping property reference extraction - budget/price context detected: {message}")
            return None
        
        # Pattern 1: "property 1", "property #1", "property number 1"
        match = re.search(r'property\s*(?:number\s*|#\s*)?(\d+)', message_lower)
        if match:
            return match.group(1)
        
        # Pattern 2: "1st", "2nd", "3rd", etc. (but only in property context)
        if any(word in message_lower for word in ['property', 'apartment', 'villa', 'listing']):
            match = re.search(r'(\d+)(?:st|nd|rd|th)', message_lower)
            if match:
                return match.group(1)
        
        # Pattern 3: "first", "second", "third" (but only in property context)
        if any(word in message_lower for word in ['property', 'apartment', 'villa', 'listing', 'one', 'option']):
            ordinal_words = {
                'first': '1', 'second': '2', 'third': '3', 'fourth': '4', 'fifth': '5'
            }
            for word, num in ordinal_words.items():
                if word in message_lower:
                    return num
        
        # Pattern 4: "tell me about 1", "details of 2" (explicit property context)
        property_context_patterns = [
            r'tell me about\s+(\d+)',
            r'details of\s+(\d+)', 
            r'more about\s+(\d+)',
            r'property\s+(\d+)',
            r'option\s+(\d+)'
        ]
        
        for pattern in property_context_patterns:
            match = re.search(pattern, message_lower)
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
    
    async def execute_sophisticated_search_and_respond(self, criteria_dict: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        🚀 Execute sophisticated search and generate intelligent response
        
        This is the main integration point between conversation engine and sophisticated search.
        Called by the main processing worker when should_search_properties=True and use_sophisticated_search=True.
        
        Args:
            criteria_dict: Search criteria dictionary from ConversationResponse.sophisticated_search_criteria
        
        Returns:
            Tuple of (intelligent_response_message, property_objects_for_carousel)
        """
        try:
            # Convert dict back to SearchCriteria object
            criteria = SearchCriteria(**criteria_dict)
            
            logger.info(f"🧠 Executing sophisticated search with criteria: {criteria.to_dict()}")
            
            # Execute sophisticated search
            search_result = await sophisticated_search_pipeline.search_with_intelligence(criteria, limit=15)
            
            logger.info(f"🎯 Sophisticated search completed:")
            logger.info(f"   Tier: {search_result.tier.value}")
            logger.info(f"   Strategy: {search_result.strategy_used}")
            logger.info(f"   Properties found: {search_result.count}")
            logger.info(f"   Execution time: {search_result.execution_time_ms:.0f}ms")
            
            # CRITICAL FIX: Reorder properties by priority BEFORE generating response
            # This ensures response analysis and carousel properties match
            ordered_properties = self._reorder_properties_by_priority(
                search_result.properties, 
                search_result.alternatives_found if hasattr(search_result, 'alternatives_found') else {},
                criteria
            )
            
            # Update search result with ordered properties for response generation
            search_result.properties = ordered_properties
            
            # Generate intelligent response message using ordered properties
            intelligent_response = generate_sophisticated_response(search_result, criteria)
            
            # Return both the response and ordered property objects for carousel
            return intelligent_response, ordered_properties
            
        except Exception as e:
            logger.error(f"❌ Sophisticated search execution failed: {e}")
            
            # Fallback response
            fallback_response = """🔍 I encountered an issue with the advanced search, but let me help you find properties.

💡 **What I can do:**
• Search with different criteria
• Browse popular properties
• Connect you with a property consultant

What would you like to try?"""
            
            return fallback_response, []
    
    def _reorder_properties_by_priority(self, properties, alternatives_found, criteria):
        """
        Reorder properties by priority: budget increase first, then location expansion, then property type
        """
        try:
            if not alternatives_found or not criteria:
                return properties
            
            budget_max = getattr(criteria, 'budget_max', None) or getattr(criteria, 'budget_min', None)
            original_location = getattr(criteria, 'location', None)
            original_property_type = getattr(criteria, 'property_type', None)
            
            budget_properties = []
            location_properties = []
            property_type_properties = []
            other_properties = []
            
            for prop in properties:
                prop_price = self._get_property_price(prop)
                prop_location = self._get_property_location(prop)
                prop_type = self._get_property_type(prop)
                
                # Priority 1: Budget increase properties (price above original budget)
                if budget_max and prop_price and prop_price > budget_max:
                    # Check if it's in original location (budget increase, not location change)
                    if original_location and prop_location and original_location.lower() in prop_location.lower():
                        budget_properties.append(prop)
                        continue
                
                # Priority 2: Location expansion properties (different location, within budget considerations)
                if (original_location and prop_location and 
                    original_location.lower() not in prop_location.lower()):
                    location_properties.append(prop)
                    continue
                
                # Priority 3: Property type expansion (different property type)
                if (original_property_type and prop_type and 
                    prop_type.lower() != original_property_type.lower()):
                    property_type_properties.append(prop)
                    continue
                
                # Everything else
                other_properties.append(prop)
            
            # Combine in priority order
            ordered_properties = budget_properties + location_properties + property_type_properties + other_properties
            
            logger.info(f"🔄 Property reordering: {len(budget_properties)} budget, {len(location_properties)} location, {len(property_type_properties)} type, {len(other_properties)} other")
            
            return ordered_properties
            
        except Exception as e:
            logger.error(f"❌ Error reordering properties: {e}")
            return properties  # Return original order on error
    
    def _get_property_price(self, prop):
        """Extract property price from property object"""
        try:
            if isinstance(prop, dict):
                return prop.get('sale_price_aed') or prop.get('rent_price_aed')
            else:
                return getattr(prop, 'sale_price_aed', None) or getattr(prop, 'rent_price_aed', None)
        except:
            return None
    
    def _get_property_location(self, prop):
        """Extract property location from property object"""
        try:
            if isinstance(prop, dict):
                address = prop.get('address', {})
                if isinstance(address, str):
                    import json
                    try:
                        address = json.loads(address)
                    except:
                        return address
                return address.get('locality', '') if isinstance(address, dict) else ''
            else:
                address = getattr(prop, 'address', {})
                if isinstance(address, str):
                    import json
                    try:
                        address = json.loads(address)
                    except:
                        return address
                return address.get('locality', '') if isinstance(address, dict) else ''
        except:
            return ''
    
    def _get_property_type(self, prop):
        """Extract property type from property object"""
        try:
            if isinstance(prop, dict):
                return prop.get('property_type', '')
            else:
                return getattr(prop, 'property_type', '')
        except:
            return ''
    
    async def _handle_pagination_request(self, message: str, session: ConversationSession, requirements: UserRequirements) -> ConversationResponse:
        """
        🔄 Handle pagination requests for "show more properties"
        """
        logger.info("📄 Handling pagination request")
        
        # Check if we have stored properties for pagination
        all_properties = session.context.get('all_available_properties', [])
        properties_shown = session.context.get('properties_shown', 0)
        properties_per_batch = session.context.get('properties_per_batch', 10)
        
        logger.info(f"📄 PAGINATION_DEBUG: all_properties count = {len(all_properties)}, properties_shown = {properties_shown}")
        
        if not all_properties:
            logger.warning("⚠️ No all_available_properties found in session context")
            return ConversationResponse(
                message="I don't have any stored properties to show more of. Please search for properties first.",
                stage=ConversationStage.COLLECTING_REQUIREMENTS,
                requirements=requirements
            )
        
        # Calculate next batch
        total_properties = len(all_properties)
        remaining_properties = total_properties - properties_shown
        
        if remaining_properties <= 0:
            return ConversationResponse(
                message=f"You've already seen all {total_properties} available properties! Would you like to search with different criteria?",
                stage=ConversationStage.SHOWING_RESULTS,
                requirements=requirements
            )
        
        # Get next batch
        next_batch_size = min(properties_per_batch, remaining_properties)
        start_index = properties_shown
        end_index = start_index + next_batch_size
        next_batch = all_properties[start_index:end_index]
        
        logger.info(f"📄 Sending next batch: properties {start_index+1}-{end_index} of {total_properties}")
        
        # Extract property IDs for carousel
        property_ids = []
        for i, prop in enumerate(next_batch):
            prop_id = None
            
            if isinstance(prop, dict):
                if prop.get('original_property_id'):
                    prop_id = str(prop['original_property_id'])
                elif prop.get('id'):
                    prop_id = str(prop['id'])
            elif hasattr(prop, 'original_property_id') and prop.original_property_id:
                prop_id = str(prop.original_property_id)
            elif hasattr(prop, 'id') and prop.id:
                prop_id = str(prop.id)
            
            if prop_id:
                property_ids.append(prop_id)
                logger.info(f"🆔 Batch {start_index//properties_per_batch + 2} Property {i+1}: ID = {prop_id}")
        
        if len(property_ids) >= 1:  # Send carousel for 1+ properties
            # Store pagination info for carousel sending (will be handled by agent system)
            session.context['pagination_batch_ids'] = property_ids
            session.context['pagination_batch_start'] = start_index + 1
            session.context['pagination_batch_end'] = end_index
            session.context['pagination_total'] = total_properties
            
            return ConversationResponse(
                message="pagination_request",  # Special message type to trigger carousel in agent system
                stage=ConversationStage.SHOWING_RESULTS,
                requirements=requirements,
                should_search_properties=False,  # This is pagination, not new search
                debug_info={
                    "pagination": True,
                    "batch_size": next_batch_size,
                    "properties_shown_after": end_index,
                    "total_properties": total_properties
                }
            )
        else:
            # Not enough properties for carousel, format as text
            properties_text = self._format_properties_text(next_batch, start_index + 1)
            
            # Update session
            session.context['properties_shown'] = end_index
            
            remaining_after = total_properties - end_index
            if remaining_after > 0:
                properties_text += f"\n\n💬 Say *\"show more properties\"* to see {remaining_after} more properties!"
            
            return ConversationResponse(
                message=properties_text,
                stage=ConversationStage.SHOWING_RESULTS,
                requirements=requirements
            )
    
    def _format_properties_text(self, properties: List[Dict[str, Any]], start_number: int = 1) -> str:
        """
        Format properties as WhatsApp text message
        """
        if not properties:
            return "No properties to display."
        
        response_parts = [f"🏠 **Properties {start_number}-{start_number + len(properties) - 1}:**\n"]
        
        for i, prop in enumerate(properties):
            try:
                # Extract basic info
                property_type = prop.get('property_type', 'Property')
                bedrooms = prop.get('bedrooms', 0)
                bathrooms = prop.get('bathrooms', 0)
                
                # Format price
                price = "Price on request"
                if prop.get('sale_price_aed'):
                    price = f"AED {prop['sale_price_aed']:,}"
                elif prop.get('rent_price_aed'):
                    price = f"AED {prop['rent_price_aed']:,}/year"
                
                # Extract location
                address = prop.get('address', {})
                if isinstance(address, str):
                    try:
                        address = json.loads(address)
                    except:
                        address = {}
                
                location = "Dubai"
                if address and address.get('locality'):
                    location = address['locality']
                
                building_name = prop.get('building_name', '')
                if building_name:
                    location = f"{building_name}, {location}"
                
                # Format size and features
                features = []
                if prop.get('bua_sqft'):
                    features.append(f"{prop['bua_sqft']:,} sqft")
                if bathrooms:
                    features.append(f"{bathrooms} bath")
                if prop.get('study'):
                    features.append('study')
                if prop.get('maid_room'):
                    features.append('maid room')
                if prop.get('landscaped_garden'):
                    features.append('garden')
                if prop.get('covered_parking_spaces'):
                    features.append(f"{prop['covered_parking_spaces']} parking")
                
                features_text = " • ".join(features) if features else ""
                
                property_line = f"{start_number + i}. 🏠 *{bedrooms}BR {property_type}*\n"
                property_line += f"💰 {price}\n"
                property_line += f"📍 {location}\n"
                if features_text:
                    property_line += f"✨ {features_text}\n"
                
                response_parts.append(property_line)
                
            except Exception as e:
                logger.error(f"❌ Error formatting property {i+1}: {e}")
                response_parts.append(f"{start_number + i}. Property details available - ask for more info!\n")
        
        return "\n".join(response_parts)


# Global instance
unified_engine = UnifiedConversationEngine()
