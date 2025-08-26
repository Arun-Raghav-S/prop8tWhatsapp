"""
Intelligent Conversation Manager
AI-Native approach for handling property search conversations
Replaces brittle pattern matching with robust LLM-powered understanding
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Union
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from enum import Enum

from utils.logger import setup_logger

logger = setup_logger(__name__)


class ConversationStage(str, Enum):
    """Conversation stages for property search"""
    INITIAL = "initial"
    COLLECTING_BASIC_INFO = "collecting_basic_info"
    COLLECTING_DETAILED_PREFERENCES = "collecting_detailed_preferences"
    READY_TO_SEARCH = "ready_to_search"
    SHOWING_RESULTS = "showing_results"
    FOLLOW_UP = "follow_up"


class PropertyRequirements(BaseModel):
    """Structured property requirements extracted by AI"""
    transaction_type: Optional[str] = Field(None, description="buy, rent, or sale")
    location: Optional[str] = Field(None, description="Preferred location/area")
    budget_min: Optional[int] = Field(None, description="Minimum budget in AED")
    budget_max: Optional[int] = Field(None, description="Maximum budget in AED")
    budget_period: Optional[str] = Field(None, description="yearly, monthly for rent")
    property_type: Optional[str] = Field(None, description="villa, apartment, townhouse, studio, penthouse, plot")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    special_features: List[str] = Field(default_factory=list, description="Special requirements like study, maid room, garden, etc.")
    
    # Confidence scores for extracted information
    confidence_transaction_type: float = Field(0.0, description="Confidence in transaction type extraction")
    confidence_location: float = Field(0.0, description="Confidence in location extraction")
    confidence_budget: float = Field(0.0, description="Confidence in budget extraction")
    confidence_property_type: float = Field(0.0, description="Confidence in property type extraction")


class ConversationIntent(BaseModel):
    """AI-extracted user intent and information"""
    intent: str = Field(description="User's primary intent: property_search, clarification_response, follow_up, greeting, etc.")
    stage: ConversationStage = Field(description="Current conversation stage")
    requirements: PropertyRequirements = Field(description="Extracted property requirements")
    missing_critical_info: List[str] = Field(default_factory=list, description="List of missing critical information")
    confidence_score: float = Field(description="Overall confidence in intent understanding")
    needs_clarification: bool = Field(description="Whether clarification is needed")
    clarification_question: Optional[str] = Field(None, description="Specific clarification question to ask")


class IntelligentConversationManager:
    """
    AI-Native conversation manager that understands user intent and extracts structured information
    """
    
    def __init__(self):
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        
        # Critical information required for property search
        self.critical_requirements = ["transaction_type", "location", "budget_min", "property_type"]
        
    async def analyze_user_message(self, message: str, conversation_history: List[Dict], current_stage: ConversationStage = ConversationStage.INITIAL) -> ConversationIntent:
        """
        Use AI to understand user intent and extract structured information
        This replaces all the brittle pattern matching
        """
        
        # Build conversation context
        context = self._build_context(conversation_history, current_stage)
        
        # Create AI prompt for intent analysis
        analysis_prompt = self._create_analysis_prompt(message, context, current_stage)
        
        try:
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": f"User message: {message}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            # Parse AI response
            ai_analysis = json.loads(response.choices[0].message.content)
            
            # Convert to structured format
            intent = ConversationIntent(**ai_analysis)
            
            # Determine what information is missing
            intent.missing_critical_info = self._identify_missing_info(intent.requirements)
            
            # Determine if clarification is needed
            intent.needs_clarification = len(intent.missing_critical_info) > 0 or intent.confidence_score < 0.7
            
            # Generate clarification question if needed
            if intent.needs_clarification:
                intent.clarification_question = await self._generate_smart_clarification(intent, message)
            
            logger.info(f"🧠 AI Intent Analysis: {intent.intent} (confidence: {intent.confidence_score:.2f})")
            logger.info(f"📋 Missing info: {intent.missing_critical_info}")
            
            return intent
            
        except Exception as e:
            logger.error(f"❌ AI analysis failed: {str(e)}")
            # Fallback to basic intent
            return self._create_fallback_intent(message)
    
    def _create_analysis_prompt(self, message: str, context: str, current_stage: ConversationStage) -> str:
        """Create comprehensive AI prompt for intent analysis"""
        
        return f"""
You are an expert real estate conversation analyst. Analyze the user's message and extract structured information.

CONTEXT:
{context}

CURRENT STAGE: {current_stage.value}

Your task is to understand the user's intent and extract property requirements with confidence scores.

RETURN VALID JSON with this exact structure:
{{
    "intent": "string (property_search|clarification_response|follow_up|greeting|other)",
    "stage": "string (initial|collecting_basic_info|collecting_detailed_preferences|ready_to_search|showing_results|follow_up)",
    "requirements": {{
        "transaction_type": "string|null (buy, rent, sale)",
        "location": "string|null (specific area/location)",
        "budget_min": "number|null (in AED)",
        "budget_max": "number|null (in AED)", 
        "budget_period": "string|null (yearly, monthly)",
        "property_type": "string|null (villa, apartment, townhouse, studio, penthouse, plot)",
        "bedrooms": "number|null",
        "bathrooms": "number|null",
        "special_features": ["list of strings"],
        "confidence_transaction_type": "float 0-1",
        "confidence_location": "float 0-1",
        "confidence_budget": "float 0-1",
        "confidence_property_type": "float 0-1"
    }},
    "confidence_score": "float 0-1 (overall confidence)",
    "needs_clarification": "boolean",
    "clarification_question": "string|null"
}}

EXTRACTION RULES:
1. Extract ANY mention of buy/sale/purchase → transaction_type: "buy"
2. Extract ANY mention of rent/rental → transaction_type: "rent"  
3. Location: Dubai areas (Marina, Downtown, JBR, etc.) or general areas
4. Budget: Extract numbers with k/thousand/million/AED, handle ranges
5. Property: villa, apartment, flat, studio, townhouse, penthouse, plot
6. Bedrooms: Extract "2 bed", "3BR", "studio" (=0), etc.
7. Features: study, maid room, garden, parking, pool view, etc.

CONFIDENCE SCORING:
- 1.0: Explicitly stated and clear
- 0.8: Strongly implied or likely
- 0.6: Mentioned but ambiguous  
- 0.4: Weakly implied
- 0.0: Not mentioned

INTENT CLASSIFICATION:
- "property_search": User wants to find properties
- "clarification_response": User answering our questions
- "follow_up": User asking about shown properties
- "greeting": Hello, hi, etc.
- "other": Everything else

Be intelligent about variations:
- "looking for apartments" = property_search
- "need a place to rent" = property_search  
- "2 bedroom flat" = apartment + 2 bedrooms
- "80-100k" = budget_min: 80000, budget_max: 100000
- "Dubai Marina" = location: "Dubai Marina"
"""

    def _build_context(self, conversation_history: List[Dict], current_stage: ConversationStage) -> str:
        """Build conversation context for AI analysis"""
        if not conversation_history:
            return "No previous conversation history."
        
        context_parts = [f"Current stage: {current_stage.value}"]
        context_parts.append("Recent conversation:")
        
        for msg in conversation_history[-4:]:  # Last 4 messages
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')[:100]
            context_parts.append(f"- {role}: {content}")
        
        return "\n".join(context_parts)
    
    def _identify_missing_info(self, requirements: PropertyRequirements) -> List[str]:
        """Identify what critical information is still missing"""
        missing = []
        
        if not requirements.transaction_type or requirements.confidence_transaction_type < 0.6:
            missing.append("transaction_type")
        if not requirements.location or requirements.confidence_location < 0.6:
            missing.append("location")
        if not requirements.budget_min or requirements.confidence_budget < 0.6:
            missing.append("budget")
        if not requirements.property_type or requirements.confidence_property_type < 0.6:
            missing.append("property_type")
            
        return missing
    
    async def _generate_smart_clarification(self, intent: ConversationIntent, original_message: str) -> str:
        """Generate intelligent clarification questions based on what's missing"""
        
        missing = intent.missing_critical_info
        requirements = intent.requirements
        
        if not missing:
            return None
            
        # Create contextual clarification prompt
        clarification_prompt = f"""
Generate a natural, conversational clarification question for a Dubai property search.

USER'S MESSAGE: "{original_message}"
MISSING INFORMATION: {missing}
CURRENT REQUIREMENTS: {requirements.dict()}

Generate ONE smart question that asks for the most important missing information.
Make it natural, friendly, and Dubai-specific.

Examples:
- If missing transaction_type: "Are you looking to buy or rent a property?"
- If missing location: "Which area in Dubai are you interested in? (Marina, Downtown, JBR, etc.)"
- If missing budget: "What's your budget range? (e.g., 80-100k for rent, 1-2M for purchase)"
- If missing property_type: "What type of property? (villa, 2-bed apartment, studio, etc.)"

Return ONLY the clarification question, nothing else.
"""

        try:
            response = await self.openai.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": clarification_prompt}],
                temperature=0.3,
                max_tokens=100
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate clarification: {e}")
            # Fallback to manual clarification
            return self._fallback_clarification(missing)
    
    def _fallback_clarification(self, missing: List[str]) -> str:
        """Fallback clarification for when AI fails"""
        clarification_map = {
            "transaction_type": "Are you looking to buy or rent?",
            "location": "Which area in Dubai are you interested in?",
            "budget": "What's your budget range?",
            "property_type": "What type of property are you looking for?"
        }
        
        if missing:
            return clarification_map.get(missing[0], "Could you provide more details about your property requirements?")
        
        return "Could you provide more details about what you're looking for?"
    
    def _create_fallback_intent(self, message: str) -> ConversationIntent:
        """Create fallback intent when AI analysis fails"""
        return ConversationIntent(
            intent="property_search",
            stage=ConversationStage.INITIAL,
            requirements=PropertyRequirements(),
            missing_critical_info=self.critical_requirements,
            confidence_score=0.3,
            needs_clarification=True,
            clarification_question="I'd be happy to help you find a property! Could you tell me if you're looking to buy or rent, which area you prefer, and your budget range?"
        )
    
    def is_ready_for_search(self, requirements: PropertyRequirements) -> bool:
        """Determine if we have enough information to perform property search"""
        return (
            requirements.transaction_type and requirements.confidence_transaction_type >= 0.6 and
            requirements.location and requirements.confidence_location >= 0.6 and
            requirements.budget_min and requirements.confidence_budget >= 0.6 and
            requirements.property_type and requirements.confidence_property_type >= 0.6
        )
    
    def convert_to_search_params(self, requirements: PropertyRequirements) -> Dict[str, Any]:
        """Convert AI-extracted requirements to search parameters"""
        params = {}
        
        if requirements.transaction_type:
            params['sale_or_rent'] = 'sale' if requirements.transaction_type == 'buy' else 'rent'
        
        if requirements.location:
            params['locality'] = requirements.location
            
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
            params['property_type'] = requirements.property_type.title()
            
        if requirements.bedrooms is not None:
            params['bedrooms'] = requirements.bedrooms
            
        if requirements.bathrooms is not None:
            params['bathrooms'] = requirements.bathrooms
            
        # Handle special features
        for feature in requirements.special_features:
            feature_lower = feature.lower()
            if 'study' in feature_lower:
                params['study'] = True
            elif 'maid' in feature_lower:
                params['maid_room'] = True
            elif 'garden' in feature_lower:
                params['landscaped_garden'] = True
            elif 'pool' in feature_lower or 'view' in feature_lower:
                params['park_pool_view'] = True
        
        return params


# Global instance for easy import
intelligent_conversation_manager = IntelligentConversationManager()
