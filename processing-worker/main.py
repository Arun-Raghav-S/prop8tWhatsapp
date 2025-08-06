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
from src.utils.pubsub import (
    PubSubMessageProcessor,
    extract_whatsapp_messages,
    get_business_account_from_webhook
)

# Setup logging
logger = setup_logger(__name__)

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
            # Save the name
            session_manager.save_customer_name(user_number, extracted_name)
            logger.info(f"💾 [NAME_EXTRACTION] Saved name: {extracted_name} for {user_number}")
            
            # Send a follow-up message confirming name was saved
            confirmation_message = f"Got it! I'll remember your name is {extracted_name}. 😊"
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

async def process_single_message(message: Dict[str, Any], whatsapp_business_account: str) -> None:
    """
    Process a single WhatsApp message exactly like the reference implementation
    
    Args:
        message: The message data from WhatsApp webhook
        whatsapp_business_account: WhatsApp business account ID
    """
    try:
        # Handle different message types
        message_type = message.get("type")
        from_phone = message.get("from")
        user_number = f"+{from_phone}" if from_phone else None
        message_id = message.get("id")
        message_timestamp = message.get("timestamp")
        
        logger.info(f"💬 USER_MESSAGE: {message_type} from {user_number}")
        
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
                    
                    # Always process through agent system first (normal flow)
                    agent_response = await agent_system.process_message(
                        message=text_message, 
                        session=session
                    )
                    
                    # Handle name collection logic asynchronously
                    if session_manager.is_awaiting_name_response(user_number):
                        # Try to extract name in background (non-blocking)
                        asyncio.create_task(_handle_name_extraction_async(
                            user_number, text_message, whatsapp_business_account
                        ))
                    else:
                        # Increment question count for non-name responses
                        session_manager.increment_question_count(user_number)
                        
                        # Check if we should ask for name (using config threshold)
                        from src.config import config
                        if session_manager.should_ask_for_name(user_number, config.NAME_COLLECTION_QUESTION_THRESHOLD):
                            session_manager.mark_name_collection_asked(user_number)
                            # Override agent response to ask for name
                            agent_response = name_collection_service.generate_name_request_message()
                            logger.info(f"🎯 NAME_REQUEST: Asked {user_number} for name after {session.user_question_count} questions")
                    
                    # Send response via AiSensy
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
            
            logger.info(f"🔘 BUTTON_CLICK: '{button_text}' from {user_number}")
            
            if user_number and whatsapp_business_account:
                try:
                    # Get or create session for this user with database initialization
                    session = await session_manager.initialize_session_with_user_data(
                        user_number, whatsapp_business_account
                    )
                    
                    # Create a message based on button click
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
                            org_id=org_id,
                            user_name=customer_name
                        ))
                        logger.info("📊 AGENT_HISTORY: Queued for API sync (button)")
                    else:
                        logger.error(f"❌ BUTTON_SEND_FAILED: to {user_number}")
                    
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