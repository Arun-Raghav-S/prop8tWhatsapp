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
from tools.property_followup_tools import PropertyFollowupHandler

logger = setup_logger(__name__)


class WhatsAppAgentSystem:
    """
    Multi-agent system that routes conversations to specialized agents
    """
    
    def __init__(self):
        self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.advanced_property_agent = AdvancedPropertySearchAgent()
        self.fast_statistical_handler = FastStatisticalQueryHandler()
        self.followup_handler = PropertyFollowupHandler(self.openai)
        
        # Initialize agents
        self.triage_agent = TriageAgent(self.openai)
        self.conversation_agent = ConversationAgent(self.openai)
        self.property_search_agent = PropertySearchAgent(self.openai, self.advanced_property_agent)
        self.statistics_agent = StatisticsAgent(self.openai, self.advanced_property_agent, self.fast_statistical_handler)
        self.followup_agent = PropertyFollowupAgent(self.openai, self.followup_handler)
        
        logger.info("WhatsApp Agent System initialized with 5 specialized agents + follow-up tools")
    
    async def process_message(self, message: str, session: ConversationSession) -> str:
        """
        Main entry point - processes user message through multi-agent system
        with AI-powered fast path detection
        """
        start_time = time.time()  # Initialize start_time at the beginning
        
        try:
            logger.info(f"🎯 Processing message: {message[:100]}...")
            
            # FAST PATH: AI-powered intent classification for statistical queries
            fast_query_type = await self.fast_statistical_handler.can_handle_fast(message)
            if fast_query_type:
                logger.info(f"🚀 AI FAST PATH activated for: {fast_query_type}")
                result = await self.fast_statistical_handler.execute_fast_query(fast_query_type, message)
                response = self.fast_statistical_handler.generate_fast_response(
                    result['results'], 
                    fast_query_type, 
                    result['execution_time_ms'],
                    result.get('sale_or_rent', 'sale')
                )
                
                # Log to session
                session.add_message("user", message, "fast_path", metadata=None, message_type="text")
                session.add_message("assistant", response, "fast_path", metadata={
                    "execution_time_ms": result['execution_time_ms'],
                    "method": result['method'],
                    "query_type": fast_query_type
                }, message_type="text")
                
                return response
            
            # FULL PATH: Regular multi-agent processing for complex queries
            logger.info("🔄 Using FULL PIPELINE for complex query")
            
            # Check for property follow-up first
            has_active_properties = bool(session.context.get('active_properties'))
            followup_result = await self.followup_handler.detect_followup_intent(message, has_active_properties)
            
            if followup_result.get('is_followup', False):
                logger.info(f"🔍 FOLLOW-UP detected: {followup_result.get('intent')}")
                response = await self.followup_agent.handle_message(message, session, followup_result)
                agent_choice = "followup"
            else:
                # Step 1: Determine which agent should handle this message
                agent_choice = await self.triage_agent.route_message(message, session)
                
                # Step 2: Route to appropriate agent
                if agent_choice == "conversation":
                    response = await self.conversation_agent.handle_message(message, session)
                elif agent_choice == "property_search":
                    response = await self.property_search_agent.handle_message(message, session)
                elif agent_choice == "statistics":
                    response = await self.statistics_agent.handle_message(message, session)
                else:
                    # Default to conversation agent
                    response = await self.conversation_agent.handle_message(message, session)
            
            processing_time = (time.time() - start_time) * 1000
            
            # Log to session
            session.add_message("user", message, agent_choice, metadata=None, message_type="text")
            session.add_message("assistant", response, agent_choice, metadata={
                "processing_time_ms": processing_time,
                "agent_used": agent_choice
            }, message_type="text")
            
            # Update session context
            session.current_agent = agent_choice
            
            logger.info(f"✅ RESPONSE_SENT: {agent_choice} agent ({processing_time:.0f}ms) -> {response[:100]}...")
            
            return response
            
        except Exception as e:
            logger.error(f"Message processing failed: {str(e)}")
            return "I'm sorry, I encountered an error processing your message. Please try again."


class TriageAgent:
    """
    Agent that determines which specialized agent should handle each message
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai = openai_client
    
    async def route_message(self, message: str, session: ConversationSession) -> str:
        """
        Determine which agent should handle the message
        """
        try:
            # Get conversation context
            recent_messages = session.conversation_history[-5:] if session.conversation_history else []
            context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_messages])
            
            triage_prompt = f"""
You are a triage agent for a real estate WhatsApp bot. Analyze the user's message and determine which specialized agent should handle it.

Recent conversation context:
{context_text}

User's current message: "{message}"

Available agents:
1. "conversation" - For greetings, general chat, help requests, casual conversation
2. "property_search" - For searching properties, finding apartments/villas, specific property queries
3. "statistics" - For market analysis, price averages, trends, statistical queries about properties

Rules:
- If user is asking for property search (apartments, villas, properties, rent, sale, specific locations, "what apartments do you have", "show me properties"), route to "property_search"
- If user asks ONLY for pure statistics (average prices, market trends) WITHOUT wanting to see specific properties, route to "statistics"  
- For greetings, casual chat, help requests, or unclear messages, route to "conversation"
- When in doubt between property_search and statistics, choose "property_search"
- NOTE: Follow-up questions about specific properties are handled by a separate system

Respond with only one word: conversation, property_search, or statistics
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": triage_prompt}],
                temperature=0.1,
                max_tokens=10
            )
            
            agent_choice = response.choices[0].message.content.strip().lower()
            
            # Validate response
            if agent_choice not in ["conversation", "property_search", "statistics"]:
                logger.warning(f"Invalid agent choice: {agent_choice}, defaulting to conversation")
                agent_choice = "conversation"
            
            logger.info(f"🔀 AGENT_ROUTED: {agent_choice} for: '{message[:50]}...'")
            return agent_choice
            
        except Exception as e:
            logger.error(f"Triage routing failed: {str(e)}")
            return "conversation"


class ConversationAgent:
    """
    Agent for general conversation, greetings, and casual interactions
    """
    
    def __init__(self, openai_client: AsyncOpenAI):
        self.openai = openai_client
        # Import here to avoid circular imports
        from utils.whatsapp_formatter import whatsapp_formatter
        self.formatter = whatsapp_formatter
    
    async def handle_message(self, message: str, session: ConversationSession) -> str:
        """
        Handle general conversation messages with optimized WhatsApp formatting
        """
        try:
            message_lower = message.lower().strip()
            
            # Quick responses for common patterns (no AI needed)
            if any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good evening']):
                # Get user name from session for personalized greeting
                user_name = session.customer_name if hasattr(session, 'customer_name') and session.customer_name else None
                return self.formatter.format_greeting(user_name)
            
            if any(help_word in message_lower for help_word in ['help', 'what can you do', 'assist', 'guide']):
                return self.formatter.format_help()
            
            if any(thanks in message_lower for thanks in ['thank', 'thanks', 'appreciate']):
                return f"You're welcome! {self.formatter.emojis['sparkles']} Anything else I can help you find? {self.formatter.emojis['property']}"
            
            # For other conversation, use minimal AI with focused prompt
            conversation_prompt = f"""
You are a casual but helpful Dubai property assistant. Keep responses short and WhatsApp-friendly.

User said: "{message}"

Respond naturally and briefly. Use emojis sparingly. If they're asking about properties, guide them to be more specific.

Examples:
- "That's great! What kind of property are you looking for?"
- "Sure! Try asking 'show me 2BR apartments in Marina'"
- "No problem! What area interests you?"

Keep it under 50 words and conversational."""

            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": conversation_prompt}],
                temperature=0.7,
                max_tokens=100
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Conversation agent failed: {str(e)}")
            return self.formatter.format_error()


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
        """Update session context to track clarification progress"""
        # Initialize clarification context if not exists
        if 'clarification' not in session.context:
            session.context['clarification'] = {}
        
        clarification_context = session.context['clarification']
        
        # Track what user is answering
        message_lower = user_message.lower().strip()
        
        if clarification_type == 'buy_rent':
            # Mark that we've asked the buy/rent question
            clarification_context['asked_buy_rent'] = True
            
            # Check if they're answering with buy/rent info
            buy_rent_answers = ['buy', 'rent', 'sale', 'rental', 'purchase', 'buying', 'renting']
            if any(answer in message_lower for answer in buy_rent_answers):
                clarification_context['answered_buy_rent'] = True
                
                # Extract their preference
                if any(word in message_lower for word in ['buy', 'sale', 'purchase', 'buying']):
                    clarification_context['preferred_type'] = 'sale'
                elif any(word in message_lower for word in ['rent', 'rental', 'renting']):
                    clarification_context['preferred_type'] = 'rent'
        
        elif clarification_type == 'property_type':
            # Mark that we've asked the property type question
            clarification_context['asked_property_type'] = True
            
            # Check if they're answering with property type info
            property_types = ['villa', 'apartment', 'flat', 'townhouse', 'penthouse', 'studio', 'plot', 'building']
            if any(ptype in message_lower for ptype in property_types):
                clarification_context['answered_property_type'] = True
                
                # Extract their preference
                for ptype in property_types:
                    if ptype in message_lower:
                        clarification_context['preferred_property_type'] = ptype
                        break
        
        # Update session
        from utils.session_manager import SessionManager
        session_manager = SessionManager()
        session_manager.update_session(session.user_id, session)
    
    async def handle_message(self, message: str, session: ConversationSession) -> str:
        """
        Handle property search requests using advanced search
        """
        try:
            # Create user context for the advanced agent, including clarification state
            clarification_context = session.context.get('clarification', {})
            user_context = {
                'user_id': session.user_id,
                'active_properties_count': len(session.context.get('active_properties', [])),
                'last_search_type': session.current_agent,
                'answered_buy_rent': clarification_context.get('answered_buy_rent', False),
                'answered_property_type': clarification_context.get('answered_property_type', False),
                'preferred_type': clarification_context.get('preferred_type'),
                'preferred_property_type': clarification_context.get('preferred_property_type')
            }
            
            # Execute advanced property search with context
            search_result = await self.advanced_property_agent.process_query(message, user_context)
            
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
                clarification_type = search_result.industrial_features.get('clarification_type', 'unknown')
                self._update_clarification_context(session, message, clarification_type)
                return search_result.clarification_message
            
            # SIMPLE RULE: If 7+ properties found → ALWAYS send carousel
            if search_result.context and len(search_result.context) >= 7:
                from tools.whatsapp_carousel_tool import carousel_tool
                
                logger.info(f"🎠 AUTO_CAROUSEL: {len(search_result.context)} properties found (>=7), sending carousel")
                
                # Extract property IDs
                property_ids = []
                for prop in search_result.context:
                    if hasattr(prop, 'original_property_id') and prop.original_property_id:
                        property_ids.append(str(prop.original_property_id))
                    elif hasattr(prop, 'id') and prop.id:
                        property_ids.append(str(prop.id))
                
                if len(property_ids) >= 7:
                    try:
                        # Send carousel
                        carousel_result = await carousel_tool.send_property_carousel(
                            session.user_id,
                            property_ids,
                            max_properties=10
                        )
                        
                        if carousel_result['success']:
                            logger.info(f"✅ CAROUSEL_SENT: {carousel_result['property_count']} properties")
                            # Simple 1-line response
                            return self.formatter.format_carousel_sent_response(carousel_result['property_count'])
                        else:
                            logger.error(f"❌ Carousel failed: {carousel_result['message']}")
                            # Continue to text response as fallback
                    except Exception as e:
                        logger.error(f"❌ Carousel error: {str(e)}")
                        # Continue to text response as fallback
            
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
                
                if len(property_ids) >= 7:
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


class PropertyFollowupAgent:
    """
    Agent specialized in handling follow-up questions about active properties
    """
    
    def __init__(self, openai_client: AsyncOpenAI, followup_handler: PropertyFollowupHandler):
        self.openai = openai_client
        self.followup_handler = followup_handler
    
    async def handle_message(self, message: str, session: ConversationSession, followup_result: Dict[str, Any]) -> str:
        """
        Handle follow-up messages about active properties
        """
        try:
            intent = followup_result.get('intent')
            property_reference = followup_result.get('property_reference', '')
            
            # Import session manager to get properties
            from utils.session_manager import SessionManager
            session_manager = SessionManager()
            
            # Get the specific property being referenced
            target_property = session_manager.get_property_by_reference(session.user_id, property_reference)
            
            if not target_property:
                return "I'm sorry, I couldn't find the property you're referring to. Could you please be more specific?"
            
            logger.info(f"🎯 Follow-up for property: {target_property.get('building_name', 'Unknown')} - Intent: {intent}")
            
            if intent == "location":
                return await self.followup_handler.location_tool.get_location_details(target_property)
            
            elif intent == "visit":
                return await self._handle_visit_scheduling(message, target_property, session, session_manager)
            
            elif intent == "nearest_place":
                return await self._handle_nearest_place(message, target_property, followup_result)
            
            elif intent == "route":
                return await self._handle_route_calculation(message, target_property, followup_result)
            
            elif intent == "general":
                return await self._handle_general_followup(message, target_property, session)
            
            else:
                return "I'm not sure what you'd like to know about this property. Could you please be more specific?"
                
        except Exception as e:
            logger.error(f"Property followup agent failed: {str(e)}")
            return "I'm sorry, I couldn't process your follow-up question. Please try again."
    
    async def _handle_visit_scheduling(self, message: str, property_data: Dict[str, Any], session: ConversationSession, session_manager) -> str:
        """
        Handle visit scheduling requests
        """
        try:
            # Get current session context for any pending booking data
            session_context = session.context
            
            # Collect visit details from the message
            visit_result = await self.followup_handler.visit_scheduler.collect_visit_details(
                message, property_data, session_context
            )
            
            booking_data = visit_result['booking_data']
            is_complete = visit_result['is_complete']
            missing_info = visit_result['missing_info']
            
            # Update session with pending booking data
            session.context['pending_visit_booking'] = booking_data
            session_manager.update_session(session.user_id, session)
            
            if is_complete:
                # Schedule the visit
                response = await self.followup_handler.visit_scheduler.schedule_visit(booking_data)
                # Clear pending booking data
                session.context.pop('pending_visit_booking', None)
                session_manager.update_session(session.user_id, session)
                return response
            else:
                # Ask for missing information
                return await self.followup_handler.visit_scheduler.ask_for_missing_info(missing_info, property_data)
                
        except Exception as e:
            logger.error(f"Visit scheduling failed: {str(e)}")
            return "I'm sorry, I couldn't process your visit request. Please try again."
    
    async def _handle_nearest_place(self, message: str, property_data: Dict[str, Any], followup_result: Dict[str, Any]) -> str:
        """
        Handle nearest place queries using the location tools
        """
        try:
            query = followup_result.get('query', message)
            
            # Extract what the user is looking for
            query_lower = query.lower()
            place_type = ""
            
            # Map keywords to place types
            place_mapping = {
                'hospital': 'hospital',
                'school': 'school', 
                'restaurant': 'restaurant',
                'mall': 'shopping mall',
                'airport': 'airport',
                'metro': 'metro station',
                'bus': 'bus station',
                'pharmacy': 'pharmacy',
                'bank': 'bank',
                'grocery': 'grocery store',
                'market': 'market',
                'gym': 'gym',
                'park': 'park'
            }
            
            # Find the place type from the message
            for keyword, place in place_mapping.items():
                if keyword in query_lower:
                    place_type = place
                    break
            
            # If no specific place type found, use a generic query
            if not place_type:
                if 'nearest' in query_lower or 'nearby' in query_lower:
                    place_type = query.replace('nearest', '').replace('nearby', '').strip()
                else:
                    place_type = query
            
            logger.info(f"🔍 Finding nearest '{place_type}' for property: {property_data.get('building_name', 'Unknown')}")
            
            # Use the location tools to find nearest places
            result = await self.followup_handler.location_tools.find_nearest_place(
                property_data, place_type, k=3
            )
            
            # Format and return the response
            return self.followup_handler.location_tools.format_nearest_places_response(result)
            
        except Exception as e:
            logger.error(f"Nearest place search failed: {str(e)}")
            return f"I'm sorry, I couldn't find nearby places. Please try again or be more specific about what you're looking for."
    
    async def _handle_route_calculation(self, message: str, property_data: Dict[str, Any], followup_result: Dict[str, Any]) -> str:
        """
        Handle route calculation queries using the location tools
        """
        try:
            query = followup_result.get('query', message)
            query_lower = query.lower()
            
            # Determine if property is origin or destination
            is_origin = True  # Default: property is origin
            destination = ""
            
            # Extract destination from the query
            if 'from' in query_lower and 'to' in query_lower:
                # Handle "route from X to Y" format
                parts = query_lower.split('to')
                if len(parts) >= 2:
                    destination = parts[-1].strip()
                    if 'property' not in parts[0] and property_data.get('building_name', '').lower() not in parts[0]:
                        is_origin = False  # Property is destination
            elif 'to' in query_lower:
                # Handle "route to X" format - property is origin
                destination = query_lower.split('to')[-1].strip()
                is_origin = True
            elif 'from' in query_lower:
                # Handle "route from X" format - property is destination
                destination = query_lower.split('from')[-1].strip()
                is_origin = False
            elif 'how to reach' in query_lower:
                # Handle "how to reach X" - property is origin, X is destination
                destination = query_lower.replace('how to reach', '').strip()
                is_origin = True
            elif 'how to get' in query_lower:
                # Handle "how to get to X" - property is origin
                if 'to' in query_lower:
                    destination = query_lower.split('to')[-1].strip()
                else:
                    destination = query_lower.replace('how to get', '').strip()
                is_origin = True
            else:
                # Extract destination as any location mentioned
                common_words = ['route', 'direction', 'distance', 'travel', 'time', 'driving', 'walking', 'commute', 'the', 'a', 'an', 'is', 'are', 'what', 'how']
                words = query.split()
                destination_words = [word for word in words if word.lower() not in common_words]
                destination = ' '.join(destination_words) if destination_words else query
            
            if not destination:
                return "Please specify where you'd like to go or come from. For example: 'route to airport' or 'how to reach the mall'."
            
            logger.info(f"🗺️ Calculating route: Property '{property_data.get('building_name', 'Unknown')}' {'→' if is_origin else '←'} '{destination}'")
            
            # Use the location tools to calculate route
            result = await self.followup_handler.location_tools.calculate_route(
                property_data, destination, is_origin=is_origin
            )
            
            # Format and return the response
            return self.followup_handler.location_tools.format_route_response(result)
            
        except Exception as e:
            logger.error(f"Route calculation failed: {str(e)}")
            return f"I'm sorry, I couldn't calculate the route. Please try again with a specific destination like 'route to airport' or 'how to reach the mall'."
    
    async def _handle_general_followup(self, message: str, property_data: Dict[str, Any], session: ConversationSession) -> str:
        """
        Handle general follow-up questions about properties
        """
        try:
            # Generate a contextual response about the property
            property_info = {
                'building_name': property_data.get('building_name', 'N/A'),
                'property_type': property_data.get('property_type', 'N/A'),
                'bedrooms': property_data.get('bedrooms', 'N/A'),
                'bathrooms': property_data.get('bathrooms', 'N/A'),
                'bua_sqft': property_data.get('bua_sqft', 'N/A'),
                'locality': property_data.get('address', {}).get('locality', 'N/A'),
                'sale_price_aed': property_data.get('sale_price_aed'),
                'rent_price_aed': property_data.get('rent_price_aed'),
                'study': property_data.get('study'),
                'maid_room': property_data.get('maid_room'),
                'balconies': property_data.get('balconies'),
                'covered_parking': property_data.get('covered_parking')
            }
            
            prompt = f"""
Answer this follow-up question about a specific property: "{message}"

Property Details:
- Building: {property_info['building_name']}
- Type: {property_info['property_type']}
- Bedrooms: {property_info['bedrooms']}
- Bathrooms: {property_info['bathrooms']}
- Size: {property_info['bua_sqft']} sqft
- Location: {property_info['locality']}
- Price: {property_info.get('sale_price_aed') or property_info.get('rent_price_aed', 'Contact for price')}
- Study: {property_info['study']}
- Maid Room: {property_info['maid_room']}
- Balconies: {property_info['balconies']}
- Parking: {property_info['covered_parking']}

Generate a helpful, specific answer about this property:
1. Address the user's question directly
2. Use relevant property details
3. Keep it concise and mobile-friendly
4. Use appropriate emojis
5. Offer to help with location details or scheduling a visit

Format for WhatsApp with line breaks and emojis.
"""
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=400
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"General followup failed: {str(e)}")
            return f"Here are the details for **{property_data.get('building_name', 'this property')}**:\n\n🏠 {property_data.get('bedrooms')}BR/{property_data.get('bathrooms')}BA {property_data.get('property_type')}\n📍 {property_data.get('address', {}).get('locality', 'Dubai')}\n📐 {property_data.get('bua_sqft')} sqft\n\nWould you like location details or to schedule a visit? 🗺️📅" 