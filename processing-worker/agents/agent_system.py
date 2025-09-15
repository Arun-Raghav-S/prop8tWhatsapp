"""
Multi-Agent System for WhatsApp Property Search
Using OpenAI Agents SDK
"""

import os
import time
from typing import Dict, Any, Optional
from openai import AsyncOpenAI

from utils.logger import setup_logger, log_agent_interaction
from utils.session_manager import ConversationSession
from tools.property_search_advanced import PropertySearchAgent as AdvancedPropertySearchAgent
from tools.fast_statistical_handler import FastStatisticalQueryHandler
from unified_conversation_engine import unified_engine, ConversationStage
from optimized_property_search import optimized_search


logger = setup_logger(__name__)


class WhatsAppAgentSystem:
    """
    Streamlined agent system using unified conversation engine
    Eliminates multiple conflicting systems for consistent flow
    """
    
    def __init__(self):
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize only essential components
        self.unified_engine = unified_engine
        self.optimized_search = optimized_search
        self.fast_statistical_handler = FastStatisticalQueryHandler()
        
        # Keep conversation agent for fallback
        self.conversation_agent = ConversationAgent(self.openai)
        
        logger.info("WhatsApp Agent System initialized with unified conversation engine")
    
    async def process_message(self, message: str, session: ConversationSession) -> str:
        """
        STREAMLINED message processing using unified conversation engine
        Follows your exact conversation flow diagram
        """
        start_time = time.time()
        
        try:
            logger.info(f"🎯 Processing message: {message[:50]}...")
            
            # STEP 1: Check for statistical queries first (fast path)
            fast_query_type = await self.fast_statistical_handler.can_handle_fast(message)
            if fast_query_type:
                logger.info(f"⚡ FAST PATH: {fast_query_type}")
                
                result = await self.fast_statistical_handler.execute_fast_query(fast_query_type, message)
                response = self.fast_statistical_handler.generate_fast_response(
                    result['results'], 
                    fast_query_type, 
                    result['execution_time_ms'],
                    result.get('sale_or_rent', 'sale')
                )
                
                # Log to session
                session.add_message("user", message, "fast_statistical", metadata={
                    "query_type": fast_query_type,
                    "execution_time_ms": result['execution_time_ms']
                })
                session.add_message("assistant", response, "fast_statistical")
                
                return response
            
            # STEP 2: Use unified conversation engine for main flow
            logger.info("🧠 Using unified conversation engine")
            
            # Process through unified conversation engine
            conv_response = await self.unified_engine.process_message(message, session)
            
            # STEP 3: Handle property search if needed
            if conv_response.should_search_properties:
                logger.info("🔍 Executing property search")
                
                # SOPHISTICATED SEARCH: Use new intelligent search pipeline
                if conv_response.use_sophisticated_search and conv_response.sophisticated_search_criteria:
                    logger.info("🧠 Using SOPHISTICATED SEARCH pipeline")
                    
                    # Execute sophisticated search and get intelligent response
                    intelligent_response, properties = await self.unified_engine.execute_sophisticated_search_and_respond(
                        conv_response.sophisticated_search_criteria
                    )
                    
                    # Store properties in session for follow-up
                    if properties:
                        session.context['active_properties'] = properties
                        session.context['last_search_params'] = conv_response.search_params
                        session.context['last_sophisticated_criteria'] = conv_response.sophisticated_search_criteria
                        
                        # PAGINATION LOGIC: Store ALL properties, send first batch via carousel
                        if len(properties) >= 1:
                            from tools.whatsapp_carousel_tool import carousel_tool
                            
                            logger.info(f"🎠 SOPHISTICATED_CAROUSEL: {len(properties)} total properties, sending first 10 via carousel")
                            
                            # Properties are already reordered by priority in unified_conversation_engine
                            # Store ALL properties with pagination info
                            session.context['all_available_properties'] = properties
                            session.context['properties_shown'] = 0
                            session.context['properties_per_batch'] = 10
                            
                            # Extract property IDs for first batch (first 10)
                            first_batch = properties[:10]
                            property_ids = []
                            
                            for i, prop in enumerate(first_batch):
                                prop_id = None
                                id_type = None
                                
                                # Handle different property object types - prioritize original_property_id
                                if isinstance(prop, dict):
                                    if prop.get('original_property_id'):
                                        prop_id = str(prop['original_property_id'])
                                        id_type = "original_property_id"
                                    elif prop.get('id'):
                                        prop_id = str(prop['id'])
                                        id_type = "id (fallback)"
                                        logger.warning(f"⚠️ Property {i+1}: using fallback 'id' instead of 'original_property_id'")
                                elif hasattr(prop, 'original_property_id') and prop.original_property_id:
                                    prop_id = str(prop.original_property_id)
                                    id_type = "original_property_id"
                                elif hasattr(prop, 'id') and prop.id:
                                    prop_id = str(prop.id)
                                    id_type = "id (fallback)"
                                    logger.warning(f"⚠️ Property {i+1}: using fallback 'id' instead of 'original_property_id'")
                                
                                if prop_id:
                                    property_ids.append(prop_id)
                                    logger.info(f"🆔 Batch 1 Property {i+1}: {id_type} = {prop_id}")
                                else:
                                    logger.error(f"❌ Batch 1 Property {i+1}: failed to extract ID")
                            
                            if len(property_ids) >= 1:
                                try:
                                    # Send carousel for first batch
                                    carousel_result = await carousel_tool.send_property_carousel(
                                        session.user_id,
                                        property_ids,
                                        max_properties=10
                                    )
                                    
                                    if carousel_result['success']:
                                        logger.info(f"✅ SOPHISTICATED_CAROUSEL_SENT: {carousel_result['property_count']} properties (batch 1 of {len(properties)} total)")
                                        
                                        # Update conversation stage
                                        session.context['conversation_stage'] = ConversationStage.SHOWING_RESULTS
                                        session.context['properties_shown'] = 10
                                        
                                        # Use the intelligent response as-is (it's already properly formatted)
                                        response = intelligent_response
                                        
                                        logger.info(f"🏠 SOPHISTICATED_PROPERTIES_FOUND: {len(properties)} total properties")
                                        return response
                                    else:
                                        logger.error(f"❌ Sophisticated carousel failed: {carousel_result['message']}")
                                        logger.info("🔄 Falling back to text response with property details")
                                        # Fall through to text response
                                except Exception as e:
                                    logger.error(f"❌ Sophisticated carousel error: {str(e)}")
                                    logger.info("🔄 Falling back to text response with property details")
                                    # Fall through to text response
                        
                        # Text response for <7 properties or carousel failure
                        session.context['conversation_stage'] = ConversationStage.SHOWING_RESULTS
                        
                        # Ensure we're showing property details, not market analysis
                        if len(properties) > 0:
                            logger.info(f"📋 Using text response for {len(properties)} properties")
                            response = intelligent_response
                        else:
                            logger.warning("⚠️ No properties in text response fallback")
                            response = intelligent_response
                        
                        agent_used = "sophisticated_search_text"
                        
                        logger.info(f"🏠 SOPHISTICATED_PROPERTIES_FOUND: {len(properties)} properties")
                    else:
                        # No properties found - sophisticated search provides intelligent alternatives
                        session.context['conversation_stage'] = ConversationStage.COLLECTING_REQUIREMENTS
                        response = intelligent_response
                        agent_used = "sophisticated_search_no_results"
                
                # FALLBACK: Use optimized property search if sophisticated search not available
                elif conv_response.search_params:
                    logger.info("🔄 Using FALLBACK optimized search")
                    
                    # Execute optimized property search
                    search_results = await self.optimized_search.search_properties(
                        conv_response.search_params, message
                    )
                    
                    if search_results['properties']:
                        # Store properties in session for follow-up
                        session.context['active_properties'] = search_results['properties']
                        session.context['last_search_params'] = conv_response.search_params
                        
                        # CAROUSEL LOGIC: Use carousel for 1+ properties, limit to first 10
                        if len(search_results['properties']) >= 1:
                            from tools.whatsapp_carousel_tool import carousel_tool
                            from utils.whatsapp_formatter import whatsapp_formatter
                            
                            logger.info(f"🎠 AUTO_CAROUSEL: {len(search_results['properties'])} properties found (>=7), sending carousel")
                            
                            # Extract property IDs - take first 10 properties
                            limited_properties = search_results['properties'][:10]
                            property_ids = []
                            
                            for i, prop in enumerate(limited_properties):
                                prop_id = None
                                
                                # Handle different property object types
                                if hasattr(prop, 'original_property_id') and prop.original_property_id:
                                    prop_id = str(prop.original_property_id)
                                    logger.info(f"🆔 Property {i+1}: using original_property_id = {prop_id}")
                                elif hasattr(prop, 'id') and prop.id:
                                    prop_id = str(prop.id)
                                    logger.info(f"🆔 Property {i+1}: using id = {prop_id}")
                                elif isinstance(prop, dict):
                                    # Handle dict objects from optimized search
                                    if prop.get('original_property_id'):
                                        prop_id = str(prop['original_property_id'])
                                        logger.info(f"🆔 Property {i+1}: using dict original_property_id = {prop_id}")
                                    elif prop.get('id'):
                                        prop_id = str(prop['id'])
                                        logger.info(f"🆔 Property {i+1}: using dict id = {prop_id}")
                                    else:
                                        logger.warning(f"⚠️ Property {i+1}: no ID found in dict: {list(prop.keys())}")
                                else:
                                    logger.warning(f"⚠️ Property {i+1}: unknown object type: {type(prop)}")
                                
                                if prop_id:
                                    property_ids.append(prop_id)
                                else:
                                    logger.error(f"❌ Property {i+1}: failed to extract ID")
                            
                            if len(property_ids) >= 1:
                                try:
                                    # Send carousel
                                    carousel_result = await carousel_tool.send_property_carousel(
                                        session.user_id,
                                        property_ids,
                                        max_properties=10
                                    )
                                
                                    if carousel_result['success']:
                                        logger.info(f"✅ CAROUSEL_SENT: {carousel_result['property_count']} properties")
                                        
                                        # Update conversation stage
                                        session.context['conversation_stage'] = ConversationStage.SHOWING_RESULTS
                                        
                                        # Store limited properties for follow-up queries
                                        session.context['active_properties'] = limited_properties
                                        
                                        # Return simple carousel confirmation message
                                        response = f"🏠 *Found {len(search_results['properties'])} properties!* I've sent you the first {len(property_ids)} properties as cards with all the details.\n\n📱 Tap *Know More* button to view details or *Schedule Visit* button to book a viewing."
                                        agent_used = "property_search_optimized_carousel"
                                        
                                        logger.info(f"🏠 PROPERTIES_FOUND: {len(search_results['properties'])} properties in {search_results['execution_time_ms']:.0f}ms")
                                        # Return early to avoid text formatting
                                        return response
                                    else:
                                        logger.error(f"❌ Carousel failed: {carousel_result['message']}")
                                        # Fall through to text response as fallback
                                except Exception as e:
                                    logger.error(f"❌ Carousel error: {str(e)}")
                                    # Fall through to text response as fallback
                            else:
                                logger.warning(f"Not enough property IDs for carousel: {len(property_ids)}")
                                # Fall through to text response
                        
                        # Format properties for WhatsApp (fallback or <7 properties)
                        properties_text = self.optimized_search.format_properties_for_whatsapp(
                            search_results['properties'], 
                            conv_response.requirements.dict()
                        )
                        
                        # Update conversation stage
                        session.context['conversation_stage'] = ConversationStage.SHOWING_RESULTS
                        
                        response = properties_text
                        agent_used = "property_search_optimized"
                        
                        logger.info(f"🏠 PROPERTIES_FOUND: {len(search_results['properties'])} properties in {search_results['execution_time_ms']:.0f}ms")
                    else:
                        # No properties found - provide better guidance
                        session.context['conversation_stage'] = ConversationStage.COLLECTING_REQUIREMENTS
                        
                        # Generate helpful no-results response
                        req = conv_response.requirements
                        suggestions = []
                        
                        if req.budget_min and req.budget_max:
                            new_max = int(req.budget_max * 1.3)  # Suggest 30% higher budget
                            suggestions.append(f"• Increase budget to {new_max//1000}k AED")
                        
                        if req.location and req.location.lower() in ['marina', 'downtown', 'jbr']:
                            suggestions.append("• Try nearby areas like JLT, Business Bay, or DIFC")
                        
                        if req.bedrooms and req.bedrooms >= 3:
                            suggestions.append(f"• Consider {req.bedrooms-1} bedroom apartments")
                        
                        suggestions_text = "\n".join(suggestions) if suggestions else "• Try adjusting your budget or location\n• Consider different property types"
                        
                        response = f"""🔍 No properties found matching your exact criteria.

Here are some suggestions:
{suggestions_text}

Would you like me to search with adjusted criteria, or would you prefer to modify your requirements?"""
                        agent_used = "no_results_enhanced"
            else:
                # Handle pagination requests
                if conv_response.message == "pagination_request":
                    logger.info("📄 Handling pagination carousel request")
                    
                    # Get pagination data from session
                    property_ids = session.context.get('pagination_batch_ids', [])
                    batch_start = session.context.get('pagination_batch_start', 1)
                    batch_end = session.context.get('pagination_batch_end', 1)
                    total_properties = session.context.get('pagination_total', 0)
                    
                    if property_ids and len(property_ids) >= 3:
                        try:
                            from tools.whatsapp_carousel_tool import carousel_tool
                            
                            # Send pagination carousel
                            carousel_result = await carousel_tool.send_property_carousel(
                                session.user_id,
                                property_ids,
                                max_properties=10
                            )
                            
                            if carousel_result['success']:
                                logger.info(f"✅ PAGINATION_CAROUSEL_SENT: properties {batch_start}-{batch_end} of {total_properties}")
                                
                                # Update session with new properties shown count
                                session.context['properties_shown'] = batch_end
                                
                                # Calculate remaining properties
                                remaining = total_properties - batch_end
                                if remaining > 0:
                                    response = f"📱 Here are properties {batch_start}-{batch_end} of {total_properties}!\n\n💬 Say *\"show more properties\"* to see {remaining} more properties."
                                else:
                                    response = f"📱 Here are properties {batch_start}-{batch_end} of {total_properties}!\n\nYou've now seen all available properties! 🎉"
                                
                                agent_used = "pagination_carousel"
                            else:
                                logger.error(f"❌ Pagination carousel failed: {carousel_result['message']}")
                                response = "I had trouble sending the property cards. Let me know what you'd like to see!"
                                agent_used = "pagination_failed"
                        except Exception as e:
                            logger.error(f"❌ Pagination carousel error: {str(e)}")
                            response = "I had trouble showing more properties. Please try again!"
                            agent_used = "pagination_error"
                    else:
                        logger.warning("📄 Pagination request but no property IDs available")
                        response = "I don't have more properties to show. Please search again!"
                        agent_used = "pagination_no_data"
                else:
                    # Regular conversation response
                    response = conv_response.message
                    agent_used = "unified_conversation"
                
                # Update conversation stage in session
                session.context['conversation_stage'] = conv_response.stage
            
            # STEP 4: Log conversation to session
            processing_time = (time.time() - start_time) * 1000
            
            session.add_message("user", message, agent_used, metadata={
                "conversation_stage": conv_response.stage.value,
                "processing_time_ms": processing_time
            })
            session.add_message("assistant", response, agent_used, metadata={
                "requirements_complete": conv_response.requirements.is_complete(),
                "missing_requirements": conv_response.requirements.get_missing_requirements()
            })
            
            logger.info(f"✅ UNIFIED_RESPONSE: {conv_response.stage.value} ({processing_time:.0f}ms) -> {response[:100]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Unified processing failed: {str(e)}")
            
            # Fallback to conversation agent for error recovery
            try:
                fallback_response = await self.conversation_agent.handle_message(message, session)
                return fallback_response
            except Exception as fallback_error:
                logger.error(f"❌ Fallback also failed: {str(fallback_error)}")
                return "I apologize for the technical issue. Let me help you find properties. What are you looking for?"
    



# =============================================================================
# OLD COMPLEX AGENT CLASSES - REPLACED BY UNIFIED CONVERSATION ENGINE
# Commenting out to reduce complexity and avoid conflicts
# =============================================================================

"""
# OLD TRIAGE AGENT - NO LONGER NEEDED
class TriageAgent:
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai = openai_client
    
    async def route_message(self, message: str, session: ConversationSession) -> str:
        # OLD TRIAGE LOGIC - REPLACED BY UNIFIED ENGINE
        pass
"""

# =============================================================================
# ALL OLD AGENT CLASSES COMMENTED OUT - USING UNIFIED CONVERSATION ENGINE
# =============================================================================


class ConversationAgent:
    """
    Agent for general conversation, greetings, and casual interactions
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai = openai_client
        # Import here to avoid circular imports
        from utils.whatsapp_formatter import whatsapp_formatter
        from src.services.property_details_service import property_details_service
        self.formatter = whatsapp_formatter
        self.property_details_service = property_details_service
    
    async def handle_message(self, message: str, session: ConversationSession) -> str:
        """
        Handle general conversation messages with optimized WhatsApp formatting
        """
        try:
            message_lower = message.lower().strip()
            
            # Check if we have active properties first - if so, skip hardcoded responses and use AI
            active_properties = session.context.get('active_properties', [])
            has_active_properties = len(active_properties) > 0
            
            # Only use hardcoded responses if NO active properties (to avoid context conflicts)
            if not has_active_properties:
                # Quick responses for common patterns (no AI needed)
                if any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good evening']):
                    # Get user name from session for personalized greeting
                    user_name = session.customer_name if hasattr(session, 'customer_name') and session.customer_name else None
                    return self.formatter.format_greeting(user_name)
                
                if any(help_word in message_lower for help_word in ['help', 'what can you do', 'assist', 'guide']):
                    return self.formatter.format_help()
                
                if any(thanks in message_lower for thanks in ['thank', 'thanks', 'appreciate']):
                    return f"You're welcome! {self.formatter.emojis['sparkles']} Anything else I can help you find? {self.formatter.emojis['property']}"
            
            # Check if user is asking for detailed property information
            active_properties = session.context.get('active_properties', [])
            is_detail_request = self._is_property_detail_request(message)
            
            if has_active_properties and is_detail_request and len(active_properties) > 0:
                # User wants detailed info about an active property - fetch comprehensive details
                logger.info(f"🔍 User requesting detailed property info: '{message}'")
                
                # Get the first/most relevant property (users usually refer to the last shown)
                target_property = active_properties[0]
                property_id = target_property.get('id')
                
                if property_id:
                    # Fetch comprehensive property details
                    detailed_property = await self.property_details_service.get_property_details(property_id)
                    
                    if detailed_property:
                        # Return formatted detailed response
                        return self.property_details_service.format_detailed_property_response(
                            detailed_property, message
                        )
                    else:
                        logger.warning(f"Failed to fetch detailed property info for ID: {property_id}")
                        # Fall through to AI response
                else:
                    logger.warning("Property ID not available for detailed lookup")
            
            # Build context-aware prompt with conversation history and active properties
            conversation_context = self._build_conversation_context(session)
            
            conversation_prompt = f"""
You are a helpful Dubai property assistant. You have full context of the conversation.

{conversation_context}

Current user message: "{message}"

Instructions:
- If they're asking about previously shown properties, answer specifically about those properties
- If it's a general question, respond helpfully
- Use emojis sparingly and keep responses WhatsApp-friendly
- If you need to reference properties, use the details from the context above

Respond naturally and contextually."""

            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": conversation_prompt}],
                temperature=0.7,
                max_tokens=400
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Conversation agent failed: {str(e)}")
            return self.formatter.format_error()
    
    def _build_conversation_context(self, session: ConversationSession) -> str:
        """
        Build rich context from conversation history and active properties
        """
        context_parts = []
        
        # Add recent conversation history
        if session.conversation_history:
            recent_messages = session.conversation_history[-4:]  # Last 4 exchanges
            context_parts.append("Recent conversation:")
            for msg in recent_messages:
                role = "User" if msg['role'] == 'user' else "Assistant"
                content = msg['content'][:100] + ("..." if len(msg['content']) > 100 else "")
                context_parts.append(f"- {role}: {content}")
        
        # Add active properties if any
        active_properties = session.context.get('active_properties', [])
        if active_properties:
            context_parts.append(f"\nCurrently shown properties ({len(active_properties)}):")
            for i, prop in enumerate(active_properties[:3], 1):  # Show up to 3 properties
                # Safely get address info
                address = prop.get('address', {})
                if isinstance(address, str):
                    try:
                        import json
                        address = json.loads(address)
                    except:
                        address = {}
                locality = address.get('locality', 'Dubai') if isinstance(address, dict) else 'Dubai'
                prop_summary = f"Property {i}: {prop.get('bedrooms', '?')}BR {prop.get('property_type', 'Property')} in {locality}"
                if prop.get('sale_price_aed'):
                    prop_summary += f" - AED {prop['sale_price_aed']:,}"
                elif prop.get('rent_price_aed'): 
                    prop_summary += f" - AED {prop['rent_price_aed']:,}/year"
                
                # Add key features
                features = []
                if prop.get('bua_sqft'):
                    features.append(f"{prop['bua_sqft']} sqft")
                if prop.get('bathrooms'):
                    features.append(f"{prop['bathrooms']} bath")
                if features:
                    prop_summary += f" ({', '.join(features)})"
                    
                context_parts.append(f"- {prop_summary}")
        
        # Add user info if available
        if hasattr(session, 'customer_name') and session.customer_name:
            context_parts.append(f"\nUser name: {session.customer_name}")
            
        return "\n".join(context_parts) if context_parts else "No previous context."
    
    def _is_property_detail_request(self, message: str) -> bool:
        """
        Detect if user is asking for detailed property information
        """
        message_lower = message.lower().strip()
        
        # Patterns that indicate user wants detailed information
        detail_patterns = [
            # Direct requests
            'tell me more', 'more about', 'more info', 'more details',
            'details about', 'tell me about', 'what about',
            
            # Feature questions
            'features', 'amenities', 'what features', 'what amenities',
            'facilities', 'what facilities',
            
            # Specific aspects
            'special about', 'unique about', 'special features',
            'what makes', 'why', 'how is', 'describe',
            
            # Property specifics
            'layout', 'size', 'rooms', 'parking', 'view',
            'garden', 'balcony', 'study', 'maid room',
            
            # General inquiry patterns
            'about this', 'about it', 'this one', 'this property',
            'more on', 'elaborate', 'explain'
        ]
        
        return any(pattern in message_lower for pattern in detail_patterns)


class PropertySearchAgent:
    """
    Agent specialized in property search and recommendations
    """
    
    def __init__(self, openai_client: AsyncOpenAI, advanced_property_agent: AdvancedPropertySearchAgent):
        self.openai = openai_client
        self.advanced_property_agent = advanced_property_agent
        # Import here to avoid circular imports
        from utils.whatsapp_formatter import whatsapp_formatter
        self.formatter = whatsapp_formatter
    
    def _update_clarification_context(self, session: ConversationSession, user_message: str, clarification_type: str):
        """Update session context to track clarification progress - NEW FLOW"""
        # Initialize clarification context if not exists
        if 'clarification' not in session.context:
            session.context['clarification'] = {}
        
        clarification_context = session.context['clarification']
        message_lower = user_message.lower().strip()
        
        # Handle different clarification types based on new flow
        if clarification_type == 'initial_collection':
            # Parse combined initial response (buy/rent, location, budget)
            self._parse_initial_collection(message_lower, clarification_context)
            
        elif clarification_type == 'complete_initial_info':
            # Parse additional information to complete initial collection
            self._parse_initial_collection(message_lower, clarification_context)
            
        elif clarification_type == 'buy_ready_off_plan':
            # Mark that we've asked the ready/off-plan question
            clarification_context['asked_detailed_preference'] = True
            
            # Check if they're answering
            if any(word in message_lower for word in ['ready', 'move-in', 'completed']):
                clarification_context['answered_detailed_preference'] = True
                clarification_context['ready_or_off_plan'] = 'ready'
            elif any(word in message_lower for word in ['off-plan', 'off plan', 'construction', 'under construction']):
                clarification_context['answered_detailed_preference'] = True
                clarification_context['ready_or_off_plan'] = 'off_plan'
                
        elif clarification_type == 'rent_duration':
            # Mark that we've asked the duration question
            clarification_context['asked_detailed_preference'] = True
            
            # Extract duration information
            import re
            duration_match = re.search(r'(\d+)\s*(month|months|year|years)', message_lower)
            if duration_match:
                clarification_context['answered_detailed_preference'] = True
                clarification_context['rent_duration'] = duration_match.group(0)
            elif any(word in message_lower for word in ['long term', 'longterm', 'permanent']):
                clarification_context['answered_detailed_preference'] = True
                clarification_context['rent_duration'] = 'long_term'
                
        elif clarification_type == 'property_type_detailed':
            # Mark that we've asked the property type question
            clarification_context['asked_property_type'] = True
            
            # Check for property types with bedroom info
            if any(word in message_lower for word in ['villa']):
                clarification_context['answered_property_type'] = True
                clarification_context['preferred_property_type'] = 'villa'
            elif any(word in message_lower for word in ['studio']):
                clarification_context['answered_property_type'] = True
                clarification_context['preferred_property_type'] = 'studio'
                clarification_context['preferred_bedrooms'] = 0
            elif any(word in message_lower for word in ['townhouse']):
                clarification_context['answered_property_type'] = True
                clarification_context['preferred_property_type'] = 'townhouse'
            elif any(word in message_lower for word in ['penthouse']):
                clarification_context['answered_property_type'] = True
                clarification_context['preferred_property_type'] = 'penthouse'
                
            # Check for bedroom numbers (use "beds" not "bhk")
            import re
            bedroom_match = re.search(r'(\d+)\s*(bed|beds|bedroom|bedrooms)', message_lower)
            if bedroom_match:
                clarification_context['answered_property_type'] = True
                clarification_context['preferred_bedrooms'] = int(bedroom_match.group(1))
                clarification_context['preferred_property_type'] = 'apartment'
        
        # Update session
        from utils.session_manager import SessionManager
        session_manager = SessionManager()
        session_manager.update_session(session.user_id, session)
    
    def _parse_initial_collection(self, message_lower: str, clarification_context: dict):
        """Parse initial collection message for buy/rent, location, budget, property type"""
        
        # Parse buy/rent preference
        if any(word in message_lower for word in ['buy', 'sale', 'purchase', 'buying']):
            clarification_context['answered_buy_rent'] = True
            clarification_context['preferred_type'] = 'sale'
        elif any(word in message_lower for word in ['rent', 'rental', 'renting']):
            clarification_context['answered_buy_rent'] = True
            clarification_context['preferred_type'] = 'rent'
            
        # Parse location (look for common Dubai areas)
        dubai_areas = [
            'dubai marina', 'marina', 'downtown dubai', 'downtown', 'jbr', 
            'jumeirah beach residence', 'business bay', 'jlt', 'jumeirah lakes towers',
            'palm jumeirah', 'palm', 'deira', 'bur dubai', 'sheikh zayed road',
            'dubai hills', 'arabian ranches', 'jumeirah', 'al barsha', 'tecom',
            'difc', 'dubai international financial centre', 'dubai south',
            'dubai investment park', 'dip', 'jvc', 'jumeirah village circle',
            'dubai sports city', 'motor city', 'studio city', 'internet city',
            'media city', 'knowledge village', 'academic city', 'silicon oasis'
        ]
        
        for area in dubai_areas:
            if area in message_lower:
                clarification_context['answered_location'] = True
                clarification_context['preferred_location'] = area
                break
                
        # Parse budget (look for numbers with k, thousand, million, etc.)
        import re
        budget_patterns = [
            r'(\d+)\s*(?:k|thousand)',  # 100k, 100 thousand
            r'(\d+)\s*(?:m|million)',   # 1m, 1 million  
            r'(\d+)\s*(?:-|to)\s*(\d+)\s*(?:k|thousand)',  # 80-100k
            r'(\d+)\s*(?:-|to)\s*(\d+)\s*(?:m|million)',   # 1-2m
            r'(\d{1,3}(?:,\d{3})*)',    # 100,000
        ]
        
        for pattern in budget_patterns:
            if re.search(pattern, message_lower):
                clarification_context['answered_budget'] = True
                clarification_context['budget_text'] = re.search(pattern, message_lower).group(0)
                break
                
        # Parse property type (NEW - critical for flow compliance)
        if any(word in message_lower for word in ['villa', 'villas']):
            clarification_context['answered_property_type'] = True
            clarification_context['preferred_property_type'] = 'villa'
        elif any(word in message_lower for word in ['studio']):
            clarification_context['answered_property_type'] = True
            clarification_context['preferred_property_type'] = 'studio'
        elif any(word in message_lower for word in ['townhouse', 'townhouses']):
            clarification_context['answered_property_type'] = True
            clarification_context['preferred_property_type'] = 'townhouse'
        elif any(word in message_lower for word in ['penthouse', 'penthouses']):
            clarification_context['answered_property_type'] = True
            clarification_context['preferred_property_type'] = 'penthouse'
        elif any(word in message_lower for word in ['plot', 'plots']):
            clarification_context['answered_property_type'] = True
            clarification_context['preferred_property_type'] = 'plot'
            
        # Check for bedroom numbers (use "beds" not "bhk" as per flow requirement)
        bedroom_match = re.search(r'(\d+)\s*(bed|beds|bedroom|bedrooms)', message_lower)
        if bedroom_match:
            clarification_context['answered_property_type'] = True
            clarification_context['preferred_bedrooms'] = int(bedroom_match.group(1))
            clarification_context['preferred_property_type'] = 'apartment'
    
    def _update_intelligent_context(self, session: ConversationSession, intent, message: str):
        """Update session context with AI-extracted information"""
        # Store the AI analysis in session context
        session.context['last_intent'] = intent.intent
        session.context['last_confidence'] = intent.confidence_score
        session.context['conversation_stage'] = intent.stage
        
        # Update session with AI-extracted requirements
        if intent.requirements:
            req = intent.requirements
            session.context['ai_requirements'] = {
                'transaction_type': req.transaction_type,
                'location': req.location,
                'budget_min': req.budget_min,
                'budget_max': req.budget_max,
                'property_type': req.property_type,
                'bedrooms': req.bedrooms,
                'bathrooms': req.bathrooms,
                'special_features': req.special_features
            }
        
        # Update session in session manager
        from utils.session_manager import SessionManager
        session_manager = SessionManager()
        session_manager.update_session(session.user_id, session)
        
        logger.info(f"🔄 Updated session context with AI analysis for {session.user_id}")
    
    def _is_direct_query(self, message: str) -> bool:
        """Check if this is a direct specific query that can bypass clarification"""
        message_lower = message.lower().strip()
        
        # Direct queries that should show results immediately
        direct_query_patterns = [
            'cheapest', 'most expensive', 'largest', 'smallest',
            'show me', 'find me', 'what is the', 'where is the',
            'villa in', 'apartment in', 'property in', 'properties in',
            'studio', 'penthouse', '1 bedroom', '2 bedroom', '3 bedroom', '4 bedroom',
            '1 bed', '2 beds', '3 beds', '4 beds',
            'under', 'above', 'below', 'between'
        ]
        
        return any(pattern in message_lower for pattern in direct_query_patterns)
    
    async def handle_message(self, message: str, session: ConversationSession) -> str:
        """
        Handle property search requests using AI-native conversation understanding
        """
        try:
            # 🧠 AI-NATIVE APPROACH: Use intelligent conversation manager
            current_stage = session.context.get('conversation_stage', ConversationStage.INITIAL)
            conversation_history = session.conversation_history or []
            
                        # LEGACY CODE BLOCK - REPLACED BY UNIFIED ENGINE ABOVE
            # All this logic is now handled by the streamlined process_message method
            return "This legacy code path should not be reached - unified engine handles all conversations"
            
            # Store active properties in session if we have results
            if search_result.context and len(search_result.context) > 0:
                # Convert PropertyResult objects to dictionaries for session storage
                properties_data = []
                for prop in search_result.context:
                    if hasattr(prop, 'dict'):
                        properties_data.append(prop.dict())
                    else:
                        # Handle dict-like objects
                        properties_data.append(dict(prop))
                
                # Import session manager to update session
                from utils.session_manager import SessionManager
                session_manager = SessionManager()
                session_manager.set_active_properties(session.user_id, properties_data)
                
                logger.info(f"🏠 PROPERTIES_STORED: {len(properties_data)} properties for user {session.user_id}")
            
            # Handle clarification requests with session tracking
            if hasattr(search_result, 'requires_clarification') and search_result.requires_clarification:
                # Track clarification state in session
                clarification_type = search_result.debug.get('clarification_type', 'unknown') if search_result.debug else 'unknown'
                self._update_clarification_context(session, message, clarification_type)
                return search_result.clarification_message
            
            # NEW CAROUSEL LOGIC: Use carousel for 7-10 properties only
            if search_result.context and 7 <= len(search_result.context) <= 10:
                from tools.whatsapp_carousel_tool import carousel_tool
                
                logger.info(f"🎠 CAROUSEL_RANGE: {len(search_result.context)} properties (7-10), attempting carousel")
                
                # Extract property IDs
                property_ids = []
                for prop in search_result.context:
                    if hasattr(prop, 'original_property_id') and prop.original_property_id:
                        property_ids.append(str(prop.original_property_id))
                    elif hasattr(prop, 'id') and prop.id:
                        property_ids.append(str(prop.id))
                
                try:
                    # Send carousel - but with fallback to text if API fails
                    carousel_result = await carousel_tool.send_property_carousel(
                        session.user_id,
                        property_ids,
                        max_properties=10
                    )
                    
                    if carousel_result['success']:
                        # Store properties for "view more" functionality  
                        properties_data = [
                            {
                                'id': prop.id,
                                'original_property_id': getattr(prop, 'original_property_id', None),
                                'property_type': getattr(prop, 'property_type', 'Unknown'),
                                'bedrooms': getattr(prop, 'bedrooms', 0),
                                'sale_price_aed': getattr(prop, 'sale_price_aed', None),
                                'rent_price_aed': getattr(prop, 'rent_price_aed', None),
                                'address': getattr(prop, 'address', {}),
                                'building_name': getattr(prop, 'building_name', ''),
                                'bua_sqft': getattr(prop, 'bua_sqft', None)
                            }
                            for prop in search_result.context
                        ]
                        session_manager.set_active_properties(session.user_id, properties_data)
                        
                        logger.info(f"✅ CAROUSEL_SENT: {carousel_result['property_count']} properties")
                        return "Here are some great properties for you! 🏠\n\n*Tap 'View More' on any property for detailed information*"
                    else:
                        logger.error(f"❌ Carousel failed: {carousel_result['message']}")
                        # Fall through to text response
                except Exception as e:
                    logger.error(f"❌ Carousel error: {str(e)}")
                    # Fall through to text response
            
            # For <7 properties or carousel failure, use normal text response
            
            # Return the generated answer directly from the advanced agent
            return search_result.answer
            
        except Exception as e:
            logger.error(f"Property search agent failed: {str(e)}")
            return self.formatter.format_error("property search")
    
    def _generate_no_results_response(self, query: str, params: Dict[str, Any]) -> str:
        """
        Generate response when no properties are found
        """
        criteria = []
        if params.get("property_type"):
            criteria.append(params["property_type"].lower())
        if params.get("bedrooms"):
            criteria.append(f"{params['bedrooms']} bedroom")
        if params.get("sale_or_rent"):
            criteria.append(f"for {params['sale_or_rent']}")
        if params.get("locality"):
            criteria.append(f"in {params['locality']}")
        
        criteria_text = " ".join(criteria) if criteria else "your criteria"
        
        return f"""I couldn't find any properties matching {criteria_text}. 

Here are some suggestions:
• Try broadening your search criteria
• Check similar nearby areas
• Consider different property types
• Adjust your budget range

Would you like me to search with different criteria? 🔍"""
    
    def _generate_results_response(self, query: str, results: list, search_result: Dict[str, Any]) -> str:
        """
        Generate response with property results
        """
        try:
            count = len(results)
            execution_time = search_result.get("execution_time_ms", 0)
            
            # Create formatted results
            formatted_results = []
            for i, prop in enumerate(results[:5], 1):  # Show top 5
                price = ""
                if prop.get("sale_price_aed"):
                    price = f"AED {prop['sale_price_aed']:,}"
                elif prop.get("rent_price_aed"):
                    price = f"AED {prop['rent_price_aed']:,}/year"
                else:
                    price = "Price on request"
                
                location = prop.get("address", {}).get("locality") or prop.get("address", {}).get("city") or "Location not specified"
                
                formatted_results.append(
                    f"{i}. {prop['property_type']} - {prop['bedrooms']}BR/{prop['bathrooms']}BA\n"
                    f"   📍 {location}\n"
                    f"   💰 {price}\n"
                    f"   📐 {prop['bua_sqft']} sqft"
                )
            
            results_text = "\n\n".join(formatted_results)
            
            # Build response
            response = f"🏠 **Found {count} properties** ({execution_time:.0f}ms)\n\n{results_text}"
            
            if count > 5:
                response += f"\n\n📋 Showing top 5 of {count} properties."
            
            response += "\n\nWould you like more details about any of these properties or refine your search? 🔍"
            
            return response
            
        except Exception as e:
            logger.error(f"Results formatting failed: {str(e)}")
            return f"Found {len(results)} properties but couldn't format them properly. Please try again."


class StatisticsAgent:
    """
    Agent specialized in market statistics and analysis with fast path optimization
    """
    
    def __init__(self, openai_client: AsyncOpenAI, advanced_property_agent: AdvancedPropertySearchAgent, fast_handler: FastStatisticalQueryHandler):
        self.openai = openai_client
        self.advanced_property_agent = advanced_property_agent
        self.fast_handler = fast_handler
    
    async def handle_message(self, message: str, session: ConversationSession) -> str:
        """
        Handle statistical queries with fast path optimization when possible
        """
        try:
            # Check if fast path can handle this query (AWAIT the coroutine)
            fast_query_type = await self.fast_handler.can_handle_fast(message)
            
            if fast_query_type:
                logger.info(f"⚡ Statistics Agent using FAST PATH for {fast_query_type}")
                
                # Execute ultra-fast query
                fast_result = await self.fast_handler.execute_fast_query(fast_query_type, message)
                return self.fast_handler.generate_fast_response(
                    fast_result['results'], 
                    fast_query_type, 
                    fast_result['execution_time_ms'],
                    fast_result.get('sale_or_rent', 'sale')
                )
            
            # Fallback to advanced property search for complex statistical queries
            logger.info("🔄 Statistics Agent using FULL PIPELINE for complex analysis")
            
            # Create user context for the advanced agent
            user_context = {
                'user_id': session.user_id,
                'active_properties_count': len(session.context.get('active_properties', [])),
                'last_search_type': 'statistics'
            }
            
            search_result = await self.advanced_property_agent.process_query(message, user_context)
            
            # SIMPLE RULE: If 7+ properties found → ALWAYS send carousel
            if search_result.context and len(search_result.context) >= 7:
                from tools.whatsapp_carousel_tool import carousel_tool
                from utils.whatsapp_formatter import whatsapp_formatter
                
                logger.info(f"🎠 STATS_AUTO_CAROUSEL: {len(search_result.context)} properties found (>=7), sending carousel")
                
                # Extract property IDs
                property_ids = []
                for prop in search_result.context:
                    if hasattr(prop, 'original_property_id') and prop.original_property_id:
                        property_ids.append(str(prop.original_property_id))
                    elif hasattr(prop, 'id') and prop.id:
                        property_ids.append(str(prop.id))
                
                if len(property_ids) >= 1:
                    try:
                        # Send carousel
                        carousel_result = await carousel_tool.send_property_carousel(
                            session.user_id,
                            property_ids,
                            max_properties=10
                        )
                        
                        if carousel_result['success']:
                            logger.info(f"✅ STATS_CAROUSEL_SENT: {carousel_result['property_count']} properties")
                            # Simple 1-line response
                            return whatsapp_formatter.format_carousel_sent_response(carousel_result['property_count'])
                        else:
                            logger.error(f"❌ Stats carousel failed: {carousel_result['message']}")
                            # Continue to text response as fallback
                    except Exception as e:
                        logger.error(f"❌ Stats carousel error: {str(e)}")
                        # Continue to text response as fallback
            
            # For <7 properties or carousel failure, use normal text response
            return search_result.answer
            
        except Exception as e:
            logger.error(f"Statistics agent failed: {str(e)}")
            return "I'm sorry, I couldn't calculate the statistics you requested. Please try again."
    
    def _generate_stats_response(self, query: str, results: list, stats: Dict[str, Any], search_result: Dict[str, Any]) -> str:
        """
        Generate statistical analysis response
        """
        try:
            count = stats["count"]
            response_parts = [f"📊 **Market Analysis** (based on {count} properties)"]
            
            # Add price statistics
            if "sale_price" in stats:
                sale_stats = stats["sale_price"]
                response_parts.append(
                    f"\n💰 **Sale Prices:**\n"
                    f"   • Average: AED {sale_stats['average']:,.0f}\n"
                    f"   • Range: AED {sale_stats['min']:,} - AED {sale_stats['max']:,}"
                )
            
            if "rent_price" in stats:
                rent_stats = stats["rent_price"]
                response_parts.append(
                    f"\n🏠 **Rental Prices:**\n"
                    f"   • Average: AED {rent_stats['average']:,.0f}/year\n"
                    f"   • Range: AED {rent_stats['min']:,} - AED {rent_stats['max']:,}/year"
                )
            
            # Add size statistics if available
            if "size" in stats:
                size_stats = stats["size"]
                response_parts.append(
                    f"\n📐 **Property Sizes:**\n"
                    f"   • Average: {size_stats['average']:.0f} sqft\n"
                    f"   • Range: {size_stats['min']:.0f} - {size_stats['max']:.0f} sqft"
                )
            
            # Add market insights
            response_parts.append("\n💡 **Insights:**")
            
            if len(results) >= 10:
                response_parts.append("   • Good market sample size for reliable statistics")
            else:
                response_parts.append("   • Limited sample size - consider broader criteria")
            
            response_parts.append("\nWould you like more detailed analysis or search with different criteria? 📈")
            
            return "".join(response_parts)
            
        except Exception as e:
            logger.error(f"Stats response generation failed: {str(e)}")
            return f"I found {len(results)} properties but couldn't generate detailed statistics. Please try again."


