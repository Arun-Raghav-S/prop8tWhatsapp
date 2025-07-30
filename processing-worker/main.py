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
        if not envelope or "message" not in envelope:
            logger.error("Invalid Pub/Sub message format")
            return {"error": "Bad Request"}, 400

        # 2. Decode the actual data sent from the ingestion service
        pubsub_message = envelope["message"]
        if "data" not in pubsub_message:
            logger.error("No data in Pub/Sub message")
            return {"error": "Bad Request"}, 400
            
        # Decode the base64 data
        try:
            data_str = base64.b64decode(pubsub_message["data"]).decode("utf-8")
            payload_data = json.loads(data_str)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error decoding Pub/Sub message data: {e}")
            return {"error": "Invalid message data"}, 400
        
        logger.info(f"🚀 [PUB_SUB] Processing message from Pub/Sub: {payload_data}")
        
        # 3. Process WhatsApp Business Account webhook (from AiSensy)
        if payload_data.get("object") == "whatsapp_business_account":
            entries = payload_data.get("entry", [])
            
            for entry in entries:
                # Extract WhatsApp business account ID
                whatsapp_business_account = entry.get("id")
                if not whatsapp_business_account:
                    logger.error("Missing WhatsApp business account ID in webhook")
                    continue
                
                logger.info(f"WhatsApp Business Account ID: {whatsapp_business_account}")
                
                changes = entry.get("changes", [])
                
                for change in changes:
                    # Check if this is a message event
                    if change.get("field") == "messages":
                        value = change.get("value", {})
                        messages = value.get("messages", [])
                        statuses = value.get("statuses", [])
                        
                        for message in messages:
                            await process_single_message(message, whatsapp_business_account)
                            
        return {"success": True}
        
    except Exception as e:
        logger.error(f"💥 [PUB_SUB] Error processing Pub/Sub message: {e}")
        return {"error": "Internal Server Error"}, 500

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
        
        # Check for duplicate/delayed messages from AiSensy
        if message_id:
            if is_duplicate_message(message_id, message_timestamp):
                logger.warning(f"🚨 [DEDUP] Skipping duplicate/delayed message: {message_id}")
                return  # Skip processing this message
        
        # Mark message as read and show typing indicator for better UX
        if message_id and whatsapp_business_account:
            logger.info(f"📬 [MARK_READ] Processing message ID: {message_id}")
            logger.info(f"📬 [MARK_READ] From: {user_number}")
            logger.info(f"📬 [MARK_READ] Type: {message_type}")
            
            # Mark message as read asynchronously (don't wait for response)
            asyncio.create_task(mark_message_as_read(message_id, whatsapp_business_account))
        
        # Handle text messages
        if message_type == "text":
            text_message = message.get("text", {}).get("body", "").strip()
            
            if not text_message:
                logger.info(f"📭 [TEXT] Empty text message from {user_number}")
                return
            
            logger.info(f"💬 [TEXT] Processing message from {user_number}: {text_message}")
            
            if user_number and text_message and whatsapp_business_account:
                try:
                    # Get or create session for this user
                    session = session_manager.get_session(user_number)
                    
                    # Process through agent system
                    agent_response = await agent_system.process_message(
                        message=text_message, 
                        session=session
                    )
                    
                    logger.info(f"🤖 [TEXT] Agent response generated: {agent_response[:100]}...")
                    
                    # Send response via AiSensy
                    success = await send_message_via_aisensy(
                        to_phone=user_number,
                        message=agent_response,
                        whatsapp_business_account=whatsapp_business_account
                    )
                    
                    if success:
                        logger.info(f"✅ [TEXT] Response sent successfully to {user_number}")
                    else:
                        logger.error(f"❌ [TEXT] Failed to send response to {user_number}")
                    
                    # Update session
                    session_manager.update_session(user_number, session)
                    
                except Exception as e:
                    logger.error(f"❌ [TEXT] Agent processing error: {e}")
                    
                    # Send error response
                    error_response = "Sorry, I encountered an error processing your request. Please try again."
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
            
            logger.info(f"🔘 [BUTTON] Processing button click from {user_number}: {button_text} (payload: {button_payload})")
            
            if user_number and whatsapp_business_account:
                try:
                    # Get or create session for this user
                    session = session_manager.get_session(user_number)
                    
                    # Create a message based on button click
                    button_message = f"User clicked: {button_text}"
                    if button_payload.startswith("site_visit_"):
                        button_message = "I want to schedule a visit for this property"
                    
                    # Process through agent system
                    agent_response = await agent_system.process_message(
                        message=button_message, 
                        session=session
                    )
                    
                    logger.info(f"🤖 [BUTTON] Agent response generated: {agent_response[:100]}...")
                    
                    # Send response via AiSensy
                    success = await send_message_via_aisensy(
                        to_phone=user_number,
                        message=agent_response,
                        whatsapp_business_account=whatsapp_business_account
                    )
                    
                    if success:
                        logger.info(f"✅ [BUTTON] Response sent successfully to {user_number}")
                    else:
                        logger.error(f"❌ [BUTTON] Failed to send response to {user_number}")
                    
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