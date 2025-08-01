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
                session.add_message("user", message, "fast_path")
                session.add_message("assistant", response, "fast_path", {
                    "execution_time_ms": result['execution_time_ms'],
                    "method": result['method'],
                    "query_type": fast_query_type
                })
                
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
            session.add_message("user", message, agent_choice)
            session.add_message("assistant", response, agent_choice, {
                "processing_time_ms": processing_time,
                "agent_used": agent_choice
            })
            
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
- If user is asking for property search (apartments, villas, rent, sale, specific locations), route to "property_search"
- If user asks for statistics (average prices, market trends, what's the cheapest/most expensive), route to "statistics"  
- For greetings, casual chat, help requests, or unclear messages, route to "conversation"
- Consider the conversation context to maintain flow
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
    
    async def handle_message(self, message: str, session: ConversationSession) -> str:
        """
        Handle general conversation messages
        """
        try:
            # Get conversation history for context
            history = session.conversation_history[-10:] if session.conversation_history else []
            
            system_prompt = """
You are a friendly and helpful real estate assistant for a Dubai property search service. You handle general conversation, greetings, and provide help about the service.

🏠 YOUR CAPABILITIES:
- Advanced property search across Dubai (apartments, villas, penthouses, townhouses)
- Market statistics and analysis with lightning-fast responses
- Multi-agent system with specialized expertise
- Industrial-grade search features (negative filtering, advanced sorting, etc.)

✨ PERSONALITY & FORMATTING:
- Professional but warm and approachable
- Knowledgeable about Dubai real estate market
- Helpful, patient, and enthusiastic
- Use emojis appropriately for WhatsApp (🏠 🏢 📊 💰 📍 ✨)
- Format responses for mobile viewing with line breaks
- Use **bold** for important information

📝 RESPONSE GUIDELINES:
When users greet you or ask for help:
- Start with a warm greeting using emojis
- Briefly explain your advanced capabilities
- Mention the multi-agent system features
- Ask how you can assist them today
- Provide clear examples of what they can ask

EXAMPLES TO SUGGEST:
• "Show me 3BR apartments in Marina"
• "What's the average price in Downtown?"
• "Find villas WITHOUT maid room in JBR"
• "Cheapest penthouses in Palm Jumeirah"

Keep responses concise, engaging, and mobile-friendly.
"""
            
            # Build messages array with history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add recent conversation history
            for msg in history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            response = await self.openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Conversation agent failed: {str(e)}")
            return "Hello! I'm here to help you with Dubai real estate. How can I assist you today? 🏠"


class PropertySearchAgent:
    """
    Agent specialized in property search and recommendations
    """
    
    def __init__(self, openai_client: AsyncOpenAI, advanced_property_agent: AdvancedPropertySearchAgent):
        self.openai = openai_client
        self.advanced_property_agent = advanced_property_agent
    
    async def handle_message(self, message: str, session: ConversationSession) -> str:
        """
        Handle property search requests using advanced search
        """
        try:
            # Create user context for the advanced agent
            user_context = {
                'user_id': session.user_id,
                'active_properties_count': len(session.context.get('active_properties', [])),
                'last_search_type': session.current_agent
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
            
            # Handle clarification requests
            if hasattr(search_result, 'requires_clarification') and search_result.requires_clarification:
                return search_result.clarification_message
            
            # Check if we should send carousel for large result sets
            if search_result.context and len(search_result.context) >= 7:
                from tools.whatsapp_carousel_tool import carousel_tool
                
                logger.info(f"🎠 CAROUSEL_CHECK: Found {len(search_result.context)} properties, checking if suitable for carousel")
                
                # Check if query is suitable for carousel
                if carousel_tool.should_send_carousel(message, len(search_result.context)):
                    logger.info(f"🎠 CAROUSEL_SUITABLE: Query '{message[:30]}...' is suitable for carousel")
                    
                    # Extract original property IDs
                    property_ids = []
                    for prop in search_result.context:
                        if hasattr(prop, 'original_property_id') and prop.original_property_id:
                            property_ids.append(str(prop.original_property_id))
                    
                    logger.info(f"🎠 CAROUSEL_IDS: Extracted {len(property_ids)} original property IDs")
                    
                    # Only send carousel if we have enough original property IDs
                    if len(property_ids) >= 7:
                        try:
                            logger.info(f"🎠 CAROUSEL_ATTEMPT: Sending carousel with {len(property_ids)} properties")
                            
                            # Send carousel broadcast
                            carousel_result = await carousel_tool.send_property_carousel(
                                session.user_id,  # Assuming user_id is the phone number
                                property_ids,
                                max_properties=10
                            )
                            
                            if carousel_result['success']:
                                logger.info(f"🎠 CAROUSEL_SENT: {carousel_result['property_count']} properties to {session.user_id}")
                                # Return simple one-line response
                                property_count = carousel_result['property_count']
                                return f"🏠 Here are {property_count} properties that match your search! I've sent you property cards with all the details."
                            else:
                                logger.error(f"❌ CAROUSEL_FAILED: {carousel_result['message']}")
                                # Fall back to text response
                                return search_result.answer
                        except Exception as carousel_error:
                            logger.error(f"❌ CAROUSEL_ERROR: {str(carousel_error)}")
                            # Fall back to text response
                            return search_result.answer
                    else:
                        logger.info(f"🎠 CAROUSEL_SKIP: Not enough property IDs ({len(property_ids)}/7)")
                        return search_result.answer
                else:
                    logger.info(f"🎠 CAROUSEL_SKIP: Query not suitable for carousel")
                    return search_result.answer
            else:
                if search_result.context:
                    logger.info(f"🎠 CAROUSEL_SKIP: Only {len(search_result.context)} properties (< 7 required)")
                else:
                    logger.info(f"🎠 CAROUSEL_SKIP: No properties found")
            
            # Return the generated answer directly from the advanced agent
            return search_result.answer
            
        except Exception as e:
            logger.error(f"Property search agent failed: {str(e)}")
            return "I'm sorry, I couldn't search for properties right now. Please try again."
    
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
            
            # The advanced agent handles statistical queries internally
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