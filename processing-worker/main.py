"""
WhatsApp Agent Processing Worker
Pub/Sub based message processor with AiSensy integration
"""

import os
import json
import base64
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load environment variables
load_dotenv()

# Import existing agent system (PRESERVED)
from agents.agent_system import WhatsAppAgentSystem
from utils.logger import setup_logger
from utils.session_manager import SessionManager

# Import new services
from src.config import config
from src.services.messaging import (
    send_message_via_aisensy,
    mark_message_as_read,
    is_duplicate_message
)
from src.services.agent_history import update_agent_history_async
from src.services.name_collection import name_collection_service
from src.services.ai_mode_service import check_ai_mode_enabled
from src.utils.pubsub import (
    PubSubMessageProcessor,
    extract_whatsapp_messages,
    get_business_account_from_webhook
)

# Setup logging
logger = setup_logger(__name__)

# Initialize OpenAI client for AI intent classification
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize FastAPI app for health checks
app = FastAPI(
    title="WhatsApp Agent Processing Worker",
    description="Pub/Sub based message processor with agent system",
    version="2.0.0"
)

# Initialize the agent system (PRESERVED)
agent_system = WhatsAppAgentSystem()
session_manager = SessionManager()

# Global pub/sub processor
pubsub_processor = None

async def _handle_name_extraction_async(user_number: str, message: str, whatsapp_business_account: str):
    """Handle name extraction in background without blocking conversation"""
    try:
        logger.info(f"🔄 [NAME_EXTRACTION] Processing in background for {user_number}")
        
        # Try to extract name using LLM
        extracted_name = await name_collection_service.extract_name_from_message(message)
        
        if extracted_name:
            # Get the pending question before saving the name
            pending_question = session_manager.get_pending_question(user_number)
            
            # Save the name
            session_manager.save_customer_name(user_number, extracted_name)
            logger.info(f"💾 [NAME_EXTRACTION] Saved name: {extracted_name} for {user_number}")
            
            # If there's a pending question, re-process it through the agent system for proper response
            if pending_question and any(keyword in pending_question.lower() for keyword in ['apartment', 'property', 'villa', 'rent', 'buy', 'house', 'properties']):
                logger.info(f"🔄 [NAME_EXTRACTION] Re-processing property query: '{pending_question}' for {extracted_name}")
                
                # Clear the pending question first
                session_manager.clear_pending_question(user_number)
                
                # Get user session
                session = session_manager.get_session(user_number)
                
                # Process the original query through the agent system
                try:
                    agent_response = await agent_system.process_message(pending_question, session)
                    
                    # Send name confirmation + the actual property results  
                    confirmation_message = f"Got it, {extracted_name}! {agent_response}"
                    
                    await send_message_via_aisensy(
                        to_phone=user_number,
                        message=confirmation_message,
                        whatsapp_business_account=whatsapp_business_account
                    )
                    
                except Exception as e:
                    logger.error(f"❌ [NAME_EXTRACTION] Error re-processing query: {e}")
                    # Fallback to basic confirmation
                    confirmation_message = f"Got it, {extracted_name}! I'll help you find properties. To get started, please tell me:\n\n🏠 Are you looking to *buy* or *rent*?\n📍 Which area/location are you interested in?\n🏡 What type of property? (apartment, villa, studio, etc.)"
                    
                    await send_message_via_aisensy(
                        to_phone=user_number,
                        message=confirmation_message,
                        whatsapp_business_account=whatsapp_business_account
                    )
            else:
                # For non-property queries, use the regular confirmation message
                confirmation_message = name_collection_service.generate_name_confirmation_message(
                    extracted_name, pending_question
                )
                
                # Clear the pending question since we're addressing it
                session_manager.clear_pending_question(user_number)
                
                # Send the combined response
                await send_message_via_aisensy(
                    to_phone=user_number,
                    message=confirmation_message,
                    whatsapp_business_account=whatsapp_business_account
                )
            
            # Update agent history with the name information
            customer_name = session_manager.get_customer_name(user_number)
            org_id = session_manager.get_org_id(user_number)
            asyncio.create_task(update_agent_history_async(
                user_message=f"[NAME_PROVIDED: {extracted_name}]",
                agent_response=confirmation_message,
                user_number=user_number,
                whatsapp_business_account=whatsapp_business_account,
                org_id=org_id,
                user_name=customer_name
            ))
            
        else:
            logger.info(f"❌ [NAME_EXTRACTION] No name found in message from {user_number}")
            
    except Exception as e:
        logger.error(f"❌ [NAME_EXTRACTION] Error in background processing: {e}")

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "WhatsApp Agent Processing Worker",
        "version": "2.0.0",
        "status": "running",
        "mode": "pub_sub_processing_worker",
        "agent_system": "active",
        "pubsub_subscription": config.PUBSUB_SUBSCRIPTION
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {
        "status": "healthy",
        "mode": "processing_worker",
        "version": "2.0.0",
        "agent_system": "ready",
        "pubsub": "listening" if pubsub_processor else "not_started"
    }

@app.post("/")
async def process_message(request: Request):
    """Process messages from Pub/Sub (main processing endpoint)"""
    
    try:
        # 1. Get the Pub/Sub message envelope
        envelope = await request.json()
        logger.info(f"📥 RECEIVED_ENVELOPE: {json.dumps(envelope.get('message', {}).get('attributes', {}), indent=2) if envelope else 'None'}")
        if not envelope or "message" not in envelope:
            logger.error("❌ ERROR: Invalid Pub/Sub message format")
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format")

        # 2. Decode the actual data sent from the ingestion service
        pubsub_message = envelope["message"]
        if "data" not in pubsub_message:
            logger.error("❌ ERROR: No data in Pub/Sub message")
            raise HTTPException(status_code=400, detail="No data in Pub/Sub message")
            
        # Decode the base64 data
        try:
            data_str = base64.b64decode(pubsub_message["data"]).decode("utf-8")
            payload_data = json.loads(data_str)
            logger.info(f"💬 MESSAGE_RECEIVED: from={payload_data.get('whatsapp_business_account')}, type={payload_data.get('object')}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"❌ ERROR: Invalid JSON data in Pub/Sub message: {e}")
            raise HTTPException(status_code=400, detail="Invalid message data")
        
        # 3. Process WhatsApp Business Account webhook (from AiSensy)
        if payload_data.get("object") == "whatsapp_business_account":
            entries = payload_data.get("entry", [])
            
            for entry in entries:
                # Extract WhatsApp business account ID
                whatsapp_business_account = entry.get("id")
                if not whatsapp_business_account:
                    logger.error("❌ ERROR: Missing WhatsApp business account ID in webhook")
                    continue
                
                changes = entry.get("changes", [])
                
                for change in changes:
                    # Check if this is a message event
                    if change.get("field") == "messages":
                        value = change.get("value", {})
                        messages = value.get("messages", [])
                        
                        logger.info(f"🔄 PROCESSING: {len(messages)} messages from {whatsapp_business_account}")
                        for message in messages:
                            await process_single_message(message, whatsapp_business_account)
                            
        return {"success": True}
        
    except HTTPException as he:
        logger.error(f"❌ HTTP_ERROR: {he.detail}")
        raise he
    except Exception as e:
        logger.error(f"❌ PROCESSING_ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

async def _handle_know_more_button(user_number: str, property_id: str, whatsapp_business_account: str, session) -> None:
    """Handle Know More button click - fetch and send detailed property information"""
    try:
        logger.info(f"🔍 KNOW_MORE: Fetching details for property {property_id}")
        
        # Import the property details tool
        from tools.property_details_tool import property_details_tool
        
        # Fetch property details
        property_data = await property_details_tool.get_property_details(property_id)
        
        if property_data:
            # Format detailed response
            response = property_details_tool.format_property_details(property_data)
            logger.info(f"✅ PROPERTY_DETAILS: Found details for {property_id}")
        else:
            response = f"""🏠 *Property Information*

I'm sorry, I couldn't find detailed information for this property right now. 

📞 *Alternative Options:*
• Let me know what specific details you need
• I can help you find similar properties
• Contact our team directly for more information

💬 How else can I assist you?"""
            logger.warning(f"❌ PROPERTY_DETAILS: Not found for {property_id}")
        
        # Send response
        success = await send_message_via_aisensy(
            to_phone=user_number,
            message=response,
            whatsapp_business_account=whatsapp_business_account
        )
        
        if success:
            logger.info(f"📤 KNOW_MORE_RESPONSE_SENT: to {user_number}")
            
            # Update agent history
            customer_name = session_manager.get_customer_name(user_number)
            org_id = session_manager.get_org_id(user_number)
            asyncio.create_task(update_agent_history_async(
                user_message=f"User clicked: Know More (Property: {property_id})",
                agent_response=response,
                user_number=user_number,
                whatsapp_business_account=whatsapp_business_account,
                user_name=customer_name,
                org_id=org_id
            ))
        
    except Exception as e:
        logger.error(f"❌ KNOW_MORE_ERROR: {str(e)}")
        error_response = "I'm sorry, there was an issue getting the property details. Please try again or let me know what specific information you need."
        await send_message_via_aisensy(
            to_phone=user_number,
            message=error_response,
            whatsapp_business_account=whatsapp_business_account
        )


async def _handle_scheduling_flow(user_number: str, text_message: str, whatsapp_business_account: str, session) -> None:
    """Handle visit scheduling flow based on current state"""
    try:
        scheduling_state = session.context.get('scheduling_state')
        property_id = session.context.get('scheduling_property_id')
        
        logger.info(f"📅 SCHEDULING_FLOW: State={scheduling_state}, Property={property_id}")
        
        if scheduling_state == 'awaiting_name':
            # Extract name from user message
            customer_name = text_message.strip()
            
            # Update session with customer name
            session_manager.set_customer_name(user_number, customer_name)
            session.context['scheduling_customer_name'] = customer_name
            session.context['scheduling_state'] = 'awaiting_datetime'
            
            response = f"""👤 *Thank you, {customer_name}!*

🗓️ *When would you like to visit the property?*

Please share your preferred:
• Date (e.g., "Tomorrow", "Dec 25", "25/12/2023")
• Time (e.g., "2:00 PM", "14:00")

💡 *Example:* "Tomorrow at 3 PM" or "Dec 25 at 2:00 PM" """
            
            logger.info(f"📝 SCHEDULING_FLOW: Name collected - {customer_name}")
            
        elif scheduling_state == 'awaiting_datetime':
            # Parse date/time and schedule the visit
            from tools.visit_scheduling_tool import visit_scheduling_tool
            
            customer_name = session.context.get('scheduling_customer_name')
            formatted_datetime = visit_scheduling_tool.parse_date_time(text_message)
            
            if formatted_datetime:
                # Schedule the visit
                result = await visit_scheduling_tool.schedule_visit(
                    user_name=customer_name,
                    user_number=user_number,
                    date_and_time=formatted_datetime,
                    property_id=property_id
                )
                
                if result['success']:
                    response = visit_scheduling_tool.format_scheduling_response(
                        success=True, 
                        user_name=customer_name, 
                        date_time=formatted_datetime
                    )
                    logger.info(f"✅ VISIT_SCHEDULED: {customer_name} at {formatted_datetime}")
                else:
                    response = visit_scheduling_tool.format_scheduling_response(
                        success=False, 
                        user_name=customer_name, 
                        error=result.get('message', 'Unknown error')
                    )
                    logger.error(f"❌ VISIT_SCHEDULING_FAILED: {result.get('message')}")
                
                # Clear scheduling state
                session.context.pop('scheduling_state', None)
                session.context.pop('scheduling_property_id', None)
                session.context.pop('scheduling_customer_name', None)
            else:
                # Invalid date/time format
                response = f"""🗓️ *I couldn't understand the date/time format.*

Please try again with:
• "Tomorrow at 2 PM"
• "Dec 25 at 14:00"
• "25/12/2023 2:00 PM"

💡 *What date and time works best for you?*"""
                logger.warning(f"❌ INVALID_DATETIME: {text_message}")
        else:
            # Unknown state, clear it
            session.context.pop('scheduling_state', None)
            response = "I'm sorry, something went wrong with the scheduling. Please try clicking the Schedule Visit button again."
            logger.error(f"❌ UNKNOWN_SCHEDULING_STATE: {scheduling_state}")
        
        # Send response
        success = await send_message_via_aisensy(
            to_phone=user_number,
            message=response,
            whatsapp_business_account=whatsapp_business_account
        )
        
        if success:
            logger.info(f"📤 SCHEDULING_FLOW_RESPONSE_SENT: to {user_number}")
            
            # Update agent history
            customer_name = session_manager.get_customer_name(user_number)
            org_id = session_manager.get_org_id(user_number)
            asyncio.create_task(update_agent_history_async(
                user_message=text_message,
                agent_response=response,
                user_number=user_number,
                whatsapp_business_account=whatsapp_business_account,
                user_name=customer_name,
                org_id=org_id
            ))
        
    except Exception as e:
        logger.error(f"❌ SCHEDULING_FLOW_ERROR: {str(e)}")
        error_response = "I'm sorry, there was an issue with the scheduling. Please try again or let me know how else I can help."
        await send_message_via_aisensy(
            to_phone=user_number,
            message=error_response,
            whatsapp_business_account=whatsapp_business_account
        )


async def _analyze_schedule_visit_intent(message: str) -> Dict[str, Any]:
    """
    AI-based intent analysis to detect schedule visit requests intelligently
    Replaces primitive regex patterns with proper LLM understanding
    """
    try:
        analysis_prompt = f"""
You are analyzing a user message in a real estate conversation to detect if they want to schedule a property visit.

User message: "{message}"

Analyze the message and return JSON with:
{{
    "is_schedule_request": boolean,  // true if user wants to schedule/book a property visit
    "confidence": float,  // 0-1 confidence score
    "detected_phrases": [list of phrases that indicate scheduling intent],
    "reason": "explanation of why this is or isn't a schedule request"
}}

SCHEDULE VISIT INDICATORS:
- Direct requests: "schedule visit", "book visit", "arrange viewing", "schedule viewing"
- Booking language: "book appointment", "set up visit", "plan visit"
- Time-related: "when can I visit", "available times", "visit appointment"
- Viewing language: "see property", "viewing", "tour", "show property"
- Informal: "visit schedule", "wanna visit", "can visit"

EXCLUDE these as false positives:
- General inquiries: "tell me about visiting", "visiting process"
- Past tense: "I visited", "have visited"  
- Hypothetical: "if I visit", "before visiting"
- Other context: "visiting family", "tourist visiting"

Return only valid JSON.
"""

        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": analysis_prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=200
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Log the AI analysis for debugging
        if result.get("is_schedule_request"):
            logger.info(f"🧠 AI detected schedule intent in: '{message}' (confidence: {result.get('confidence', 0):.2f})")
            logger.info(f"🔍 Detected phrases: {result.get('detected_phrases', [])}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ AI intent analysis failed: {str(e)}")
        # Fallback to conservative detection
        return {
            "is_schedule_request": False,
            "confidence": 0.0,
            "detected_phrases": [],
            "reason": f"AI analysis failed: {str(e)}"
        }


async def _handle_schedule_visit_button(user_number: str, property_id: str, whatsapp_business_account: str, session) -> None:
    """Handle Schedule Visit button click - initiate visit scheduling flow"""
    try:
        logger.info(f"📅 SCHEDULE_VISIT: Starting flow for property {property_id}")
        
        # Check if we have customer name
        customer_name = session_manager.get_customer_name(user_number)
        
        if not customer_name:
            # Ask for name first
            response = f"""📅 *Schedule Property Visit*

To schedule your visit, I'll need your name first.

👤 *Please share your name so I can book the appointment for you.*"""
            
            # Set scheduling state in session
            session.context['scheduling_state'] = 'awaiting_name'
            session.context['scheduling_property_id'] = property_id
            logger.info(f"📝 SCHEDULE_VISIT: Awaiting name for {user_number}")
        else:
            # We have name, ask for date/time
            response = f"""📅 *Schedule Property Visit*

Hi {customer_name}! I'd be happy to schedule a visit for you.

🗓️ *When would you like to visit?*

Please share your preferred:
• Date (e.g., "Tomorrow", "Dec 25", "25/12/2023")
• Time (e.g., "2:00 PM", "14:00")

💡 *Example:* "Tomorrow at 3 PM" or "Dec 25 at 2:00 PM" """
            
            # Set scheduling state in session
            session.context['scheduling_state'] = 'awaiting_datetime'
            session.context['scheduling_property_id'] = property_id
            session.context['scheduling_customer_name'] = customer_name
            logger.info(f"📝 SCHEDULE_VISIT: Awaiting date/time for {user_number}")
        
        # Send response
        success = await send_message_via_aisensy(
            to_phone=user_number,
            message=response,
            whatsapp_business_account=whatsapp_business_account
        )
        
        if success:
            logger.info(f"📤 SCHEDULE_VISIT_RESPONSE_SENT: to {user_number}")
            
            # Update agent history
            customer_name = session_manager.get_customer_name(user_number)
            org_id = session_manager.get_org_id(user_number)
            asyncio.create_task(update_agent_history_async(
                user_message=f"User clicked: Schedule Visit (Property: {property_id})",
                agent_response=response,
                user_number=user_number,
                whatsapp_business_account=whatsapp_business_account,
                user_name=customer_name,
                org_id=org_id
            ))
        
    except Exception as e:
        logger.error(f"❌ SCHEDULE_VISIT_ERROR: {str(e)}")
        error_response = "I'm sorry, there was an issue starting the visit scheduling. Please try again or let me know how else I can help."
        await send_message_via_aisensy(
            to_phone=user_number,
            message=error_response,
            whatsapp_business_account=whatsapp_business_account
        )


async def process_single_message(message: Dict[str, Any], whatsapp_business_account: str) -> None:
    """
    Process a single WhatsApp message exactly like the reference implementation
    
    Args:
        message: The message data from WhatsApp webhook
        whatsapp_business_account: WhatsApp business account ID
    """
    try:
        # 🔍 DETAILED LOGGING: Print ALL incoming AiSensy data
        logger.info(f"🔍 RAW_AISENSY_MESSAGE: {json.dumps(message, indent=2)}")
        
        # Handle different message types
        message_type = message.get("type")
        from_phone = message.get("from")
        user_number = f"+{from_phone}" if from_phone else None
        message_id = message.get("id")
        message_timestamp = message.get("timestamp")
        
        logger.info(f"💬 USER_MESSAGE: {message_type} from {user_number}")
        logger.info(f"🆔 MESSAGE_ID: {message_id}")
        logger.info(f"⏰ TIMESTAMP: {message_timestamp}")
        
        # 🔒 PRIORITY CHECK 1: Check if AI mode is enabled for this business account
        ai_mode_enabled = await check_ai_mode_enabled(whatsapp_business_account)
        if not ai_mode_enabled:
            logger.info(f"🚫 [AI_MODE_DISABLED] Skipping message processing for {whatsapp_business_account} - AI mode is disabled")
            return  # Skip processing this message entirely
        
        logger.info(f"✅ [AI_MODE_ENABLED] AI mode is enabled for {whatsapp_business_account}, proceeding with message processing")
        
        # Check for duplicate/delayed messages from AiSensy
        if message_id:
            if is_duplicate_message(message_id, message_timestamp):
                logger.warning(f"🚨 DUPLICATE_SKIPPED: {message_id}")
                return  # Skip processing this message
        
        # Mark message as read and show typing indicator for better UX
        if message_id and whatsapp_business_account:
            # Mark message as read asynchronously (don't wait for response)
            asyncio.create_task(mark_message_as_read(message_id, whatsapp_business_account))
        
        # Handle text messages
        if message_type == "text":
            text_message = message.get("text", {}).get("body", "").strip()
            
            if not text_message:
                return
            
            logger.info(f"💭 USER_TEXT: '{text_message[:50]}...'")
            
            if user_number and text_message and whatsapp_business_account:
                try:
                    # Get or create session for this user with database initialization
                    session = await session_manager.initialize_session_with_user_data(
                        user_number, whatsapp_business_account
                    )
                    
                    # Store whatsapp_business_account in session context
                    session.context['whatsapp_business_account'] = whatsapp_business_account
                    
                    # 📅 CHECK FOR SCHEDULING FLOW: Handle visit scheduling states
                    scheduling_state = session.context.get('scheduling_state')
                    if scheduling_state:
                        await _handle_scheduling_flow(user_number, text_message, whatsapp_business_account, session)
                        return  # Exit early, scheduling flow handled the response
                    
                    # 📅 CHECK FOR TEXT-BASED SCHEDULE VISIT: Use AI intent classification instead of regex
                    schedule_intent = await _analyze_schedule_visit_intent(text_message)
                    
                    if schedule_intent['is_schedule_request']:
                        # Check if user has an active property to schedule visit for
                        active_property_id = session.context.get('active_property_id')
                        if active_property_id:
                            logger.info(f"🔄 TEXT_SCHEDULE_VISIT: Routing '{text_message}' to schedule visit flow for property {active_property_id}")
                            await _handle_schedule_visit_button(user_number, active_property_id, whatsapp_business_account, session)
                            return  # Exit early, scheduling flow handled the response
                        else:
                            # No active property, ask user to select one first
                            active_properties = session.context.get('active_properties', [])
                            if active_properties:
                                response = "📅 I'd be happy to schedule a visit! Which property would you like to visit? Please click 'Know More' on a property first, then I can help you schedule a visit."
                            else:
                                response = "📅 I'd love to help you schedule a visit! Please search for properties first, then I can help you schedule a viewing for any property that interests you."
                            
                            await send_message_via_aisensy(
                                to_phone=user_number,
                                message=response,
                                whatsapp_business_account=whatsapp_business_account
                            )
                            logger.info(f"📤 SCHEDULE_VISIT_NO_PROPERTY_RESPONSE_SENT: to {user_number}")
                            return
                    
                    # 🏠 PRESERVE ACTIVE PROPERTY: Maintain context for follow-up questions
                    active_property_id = session.context.get('active_property_id')
                    if active_property_id:
                        # Add property context to the message for the agent
                        enhanced_message = f"[User has active property: {active_property_id}] {text_message}"
                        logger.info(f"🏠 ENHANCED_MESSAGE: Added property context to user message")
                    else:
                        enhanced_message = text_message
                    
                    # Always process through agent system first (normal flow)
                    agent_response = await agent_system.process_message(
                        message=enhanced_message, 
                        session=session
                    )
                    
                    # Handle name collection logic
                    if session_manager.is_awaiting_name_response(user_number):
                        # Try to extract name in background (non-blocking) - this will send its own response
                        asyncio.create_task(_handle_name_extraction_async(
                            user_number, text_message, whatsapp_business_account
                        ))
                        # Don't send the agent_response here, name extraction will handle it
                        success = True  # Skip sending regular response
                    else:
                        # Increment question count for non-name responses
                        session_manager.increment_question_count(user_number)
                        
                        # Check if we should ask for name (using config threshold)
                        from src.config import config
                        should_ask_name = session_manager.should_ask_for_name(user_number, config.NAME_COLLECTION_QUESTION_THRESHOLD)
                        
                        if should_ask_name:
                            session_manager.mark_name_collection_asked(user_number, text_message)  # Store the pending question
                            # Just ask for name, don't send properties first (they'll get properties after providing name)
                            # Generate contextual name request based on what they asked
                            if any(keyword in text_message.lower() for keyword in ['apartment', 'villa', 'property', 'house', 'rent', 'buy']):
                                if 'apartment' in text_message.lower():
                                    name_request = "Before I show you apartments, may I know your name please?"
                                elif 'villa' in text_message.lower():
                                    name_request = "Before I show you villas, may I know your name please?"
                                else:
                                    name_request = "Before I show you properties, may I know your name please?"
                            else:
                                name_request = "Before I help you further, may I know your name please?"
                            success = await send_message_via_aisensy(
                                to_phone=user_number,
                                message=name_request,
                                whatsapp_business_account=whatsapp_business_account
                            )
                            logger.info(f"🎯 NAME_REQUEST: Asked {user_number} for name after {session.user_question_count} questions")
                        else:
                            # Normal flow - send the agent response
                            success = await send_message_via_aisensy(
                                to_phone=user_number,
                                message=agent_response,
                                whatsapp_business_account=whatsapp_business_account
                            )
                    
                    if success:
                        logger.info(f"📤 RESPONSE_SENT: to {user_number}")
                        
                        # Update agent history in background (non-blocking)
                        customer_name = session_manager.get_customer_name(user_number)
                        org_id = session_manager.get_org_id(user_number)
                        asyncio.create_task(update_agent_history_async(
                            user_message=text_message,
                            agent_response=agent_response,
                            user_number=user_number,
                            whatsapp_business_account=whatsapp_business_account,
                            org_id=org_id,
                            user_name=customer_name
                        ))
                        logger.info("📊 AGENT_HISTORY: Queued for API sync")
                    else:
                        logger.error(f"❌ SEND_FAILED: to {user_number}")
                    
                    # Update session
                    session_manager.update_session(user_number, session)
                    
                except Exception as e:
                    logger.error(f"❌ AGENT_ERROR: {str(e)}")
                    
                    # Send error response
                    from utils.whatsapp_formatter import whatsapp_formatter
                    error_response = whatsapp_formatter.format_error()
                    await send_message_via_aisensy(
                        to_phone=user_number,
                        message=error_response,
                        whatsapp_business_account=whatsapp_business_account
                    )
        
        # Handle button clicks (like in reference)
        elif message_type == "button":
            button_data = message.get("button", {})
            button_payload = button_data.get("payload", "")
            button_text = button_data.get("text", "")
            
            # 🔍 DETAILED LOGGING: Print all AiSensy button data
            logger.info(f"🔘 BUTTON_CLICK: '{button_text}' from {user_number}")
            logger.info(f"📋 FULL_MESSAGE_DATA: {json.dumps(message, indent=2)}")
            logger.info(f"📋 BUTTON_DATA: {json.dumps(button_data, indent=2)}")
            logger.info(f"🏷️ BUTTON_PAYLOAD: '{button_payload}'")
            logger.info(f"🏷️ BUTTON_TEXT: '{button_text}'")
            
            # 🎯 EXTRACT PROPERTY ID: Format is property_id_action
            property_id = None
            action = None
            if "_" in button_payload:
                parts = button_payload.rsplit("_", 1)  # Split from right to handle UUIDs with hyphens
                if len(parts) == 2:
                    property_id = parts[0]
                    action = parts[1]
                    logger.info(f"🆔 EXTRACTED_PROPERTY_ID: {property_id}")
                    logger.info(f"🎬 EXTRACTED_ACTION: {action}")
                else:
                    logger.warning(f"⚠️ Invalid payload format: {button_payload}")
            else:
                logger.warning(f"⚠️ No property ID found in payload: {button_payload}")
            
            if user_number and whatsapp_business_account:
                try:
                    # Get or create session for this user with database initialization
                    session = await session_manager.initialize_session_with_user_data(
                        user_number, whatsapp_business_account
                    )
                    
                    # Store whatsapp_business_account in session context  
                    session.context['whatsapp_business_account'] = whatsapp_business_account
                    
                    # Handle button clicks with property-specific actions
                    if property_id and action:
                        # 🎯 SET ACTIVE PROPERTY: Store the property ID in session
                        session.context['active_property_id'] = property_id
                        session.context['last_button_action'] = action
                        logger.info(f"🏠 SET_ACTIVE_PROPERTY: {property_id} for user {user_number}")
                        
                        # Handle specific button actions
                        if action == "knowMore":
                            await _handle_know_more_button(user_number, property_id, whatsapp_business_account, session)
                        elif action == "scheduleVisit":
                            await _handle_schedule_visit_button(user_number, property_id, whatsapp_business_account, session)
                        else:
                            logger.warning(f"⚠️ Unknown button action: {action}")
                            # Fallback to generic button message
                            button_message = f"User clicked: {button_text}"
                            agent_response = await agent_system.process_message(button_message, session)
                            await send_message_via_aisensy(user_number, agent_response, whatsapp_business_account)
                    else:
                        # Handle buttons without property IDs (legacy buttons, etc.)
                        logger.info(f"🔘 LEGACY_BUTTON: No property ID, using fallback logic")
                        button_message = f"User clicked: {button_text}"
                        if button_payload.startswith("site_visit_"):
                            button_message = "I want to schedule a visit for this property"
                        
                        # Process through agent system
                        agent_response = await agent_system.process_message(
                            message=button_message, 
                            session=session
                        )
                        
                        # Send response via AiSensy
                        success = await send_message_via_aisensy(
                            to_phone=user_number,
                            message=agent_response,
                            whatsapp_business_account=whatsapp_business_account
                        )
                        
                        if success:
                            logger.info(f"📤 BUTTON_RESPONSE_SENT: to {user_number}")
                            
                            # Update agent history in background (non-blocking)
                            customer_name = session_manager.get_customer_name(user_number)
                            org_id = session_manager.get_org_id(user_number)
                            asyncio.create_task(update_agent_history_async(
                                user_message=button_message,
                                agent_response=agent_response,
                                user_number=user_number,
                                whatsapp_business_account=whatsapp_business_account,
                                user_name=customer_name,
                                org_id=org_id
                            ))
                    
                    # Update session
                    session_manager.update_session(user_number, session)
                    
                except Exception as e:
                    logger.error(f"❌ [BUTTON] Processing error: {e}")
                    
                    # Send error response
                    error_response = "Sorry, I encountered an error processing your request. Please try again."
                    await send_message_via_aisensy(
                        to_phone=user_number,
                        message=error_response,
                        whatsapp_business_account=whatsapp_business_account
                    )
        
        # Handle other message types (location, image, etc.)
        else:
            logger.info(f"ℹ️ [MESSAGE] Received {message_type} message from {user_number}, skipping processing")
            
    except Exception as e:
        logger.error(f"💥 [PROCESSOR] Error processing single message: {e}")
        raise

async def start_pubsub_listener():
    """
    Start the Pub/Sub listener for processing messages
    Note: This is now handled by the REST endpoint (/post) but kept for compatibility
    """
    global pubsub_processor
    
    try:
        logger.info("🚀 [STARTUP] Pub/Sub processing now handled by REST endpoint")
        logger.info("ℹ️ [STARTUP] Messages will be processed via POST /")
        
        # No longer starting the pub/sub listener since we use REST endpoint
        # This allows for easier testing and matches the reference implementation
        
    except Exception as e:
        logger.error(f"❌ [STARTUP] Failed to start listener: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """
    FastAPI startup event to initialize the pub/sub listener
    """
    logger.info("🚀 [STARTUP] WhatsApp Agent Processing Worker starting up...")
    logger.info(f"🚀 [STARTUP] Agent system initialized with {len(agent_system.__dict__)} agents")
    
    # Start pub/sub listener in background
    asyncio.create_task(start_pubsub_listener())
    
    logger.info("✅ [STARTUP] Processing worker ready")

@app.on_event("shutdown") 
async def shutdown_event():
    """
    FastAPI shutdown event to cleanup resources
    """
    logger.info("🛑 [SHUTDOWN] Shutting down processing worker...")
    
    if pubsub_processor:
        pubsub_processor.stop_listening()
    
    logger.info("✅ [SHUTDOWN] Processing worker stopped")

# Endpoint for testing (preserves existing chat functionality)
@app.post("/chat")
async def test_chat(request: Request):
    """
    Test endpoint for direct chat (bypasses pub/sub for testing)
    """
    try:
        data = await request.json()
        message = data.get("message", "")
        user_id = data.get("userId", "test-user")
        
        if not message:
            return JSONResponse({"error": "No message provided"}, status_code=400)
        
        # Get session
        session = session_manager.get_session(user_id)
        
        # Process through agent system
        response = await agent_system.process_message(message, session)
        
        # Update session
        session_manager.update_session(user_id, session)
        
        return JSONResponse({
            "status": "success",
            "message": "Message processed",
            "response": response,
            "user_id": user_id
        })
        
    except Exception as e:
        logger.error(f"❌ [CHAT] Error processing test chat: {e}")
        return JSONResponse(
            {"error": f"Processing failed: {str(e)}"}, 
            status_code=500
        )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("🚀 Starting WhatsApp Agent Processing Worker")
    logger.info(f"🔧 Configuration:")
    logger.info(f"   - GCP Project: {config.GCP_PROJECT}")
    logger.info(f"   - Pub/Sub Subscription: {config.PUBSUB_SUBSCRIPTION}")
    logger.info(f"   - AiSensy Base URL: {config.AISENSY_BASE_URL}")
    
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
        reload=False  # Disable reload in production
    )