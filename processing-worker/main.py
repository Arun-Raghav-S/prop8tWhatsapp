"""
WhatsApp Agent Processing Worker
Pub/Sub based message processor with AiSensy integration
"""

import os
import json
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

async def process_webhook_message(webhook_data: Dict[str, Any]) -> None:
    """
    Process WhatsApp webhook message received from Pub/Sub
    
    This function preserves all existing agent logic and integrates with AiSensy
    """
    try:
        logger.info(f"🔄 [PROCESSOR] Processing webhook message")
        
        # Extract business account from webhook
        business_account = get_business_account_from_webhook(webhook_data)
        logger.info(f"🏢 [PROCESSOR] Business account: {business_account}")
        
        # Extract individual messages from webhook
        messages = extract_whatsapp_messages(webhook_data)
        
        if not messages:
            logger.info("📭 [PROCESSOR] No messages to process")
            return
        
        logger.info(f"📨 [PROCESSOR] Processing {len(messages)} messages")
        
        # Process each message
        for message_data in messages:
            await process_single_message(message_data, business_account)
            
    except Exception as e:
        logger.error(f"❌ [PROCESSOR] Error processing webhook message: {e}")
        raise

async def process_single_message(message_data: Dict[str, Any], business_account: str = None) -> None:
    """
    Process a single WhatsApp message using the existing agent system
    
    Args:
        message_data: Extracted message data
        business_account: WhatsApp business account ID
    """
    try:
        # Handle status updates
        if message_data.get("type") == "status_update":
            logger.info("📊 [PROCESSOR] Processing status update")
            # Status updates can be handled here if needed
            return
        
        # Process regular messages
        message = message_data.get("message", {})
        from_number = message.get("from", "unknown")
        message_id = message.get("id", "unknown")
        message_timestamp = message.get("timestamp")
        message_text = message.get("text", {}).get("body", "")
        
        if not message_text:
            logger.info(f"📭 [PROCESSOR] No text content in message {message_id}")
            return
        
        logger.info(f"💬 [PROCESSOR] Processing message from {from_number}: {message_text}")
        
        # Check for duplicate messages
        if is_duplicate_message(message_id, message_timestamp):
            logger.warning(f"🚨 [PROCESSOR] Skipping duplicate message {message_id}")
            return
        
        # Mark message as read (optional - can improve UX)
        try:
            await mark_message_as_read(message_id, business_account)
        except Exception as e:
            logger.warning(f"⚠️ [PROCESSOR] Failed to mark message as read: {e}")
        
        # Get or create session for this user (PRESERVED LOGIC)
        session = session_manager.get_session(from_number)
        
        # Process through agent system (PRESERVED LOGIC)
        try:
            agent_response = await agent_system.process_message(
                message=message_text, 
                session=session
            )
            
            logger.info(f"🤖 [PROCESSOR] Agent response generated: {agent_response[:100]}...")
            
            # Send response via AiSensy (NEW - replaces logging)
            success = await send_message_via_aisensy(
                to_phone=from_number,
                message=agent_response,
                whatsapp_business_account=business_account
            )
            
            if success:
                logger.info(f"✅ [PROCESSOR] Response sent successfully to {from_number}")
            else:
                logger.error(f"❌ [PROCESSOR] Failed to send response to {from_number}")
            
            # Update session (PRESERVED LOGIC)
            session_manager.update_session(from_number, session)
            
        except Exception as e:
            logger.error(f"❌ [PROCESSOR] Agent processing error: {e}")
            
            # Send error response
            error_response = "Sorry, I encountered an error processing your request. Please try again."
            await send_message_via_aisensy(
                to_phone=from_number,
                message=error_response,
                whatsapp_business_account=business_account
            )
            
    except Exception as e:
        logger.error(f"💥 [PROCESSOR] Error processing single message: {e}")
        raise

async def start_pubsub_listener():
    """
    Start the Pub/Sub listener for processing messages
    """
    global pubsub_processor
    
    try:
        logger.info("🚀 [STARTUP] Starting Pub/Sub message processor...")
        
        # Initialize pub/sub processor
        pubsub_processor = PubSubMessageProcessor(
            message_handler=process_webhook_message
        )
        
        # Start listening for messages
        await pubsub_processor.start_listening()
        
    except Exception as e:
        logger.error(f"❌ [STARTUP] Failed to start Pub/Sub listener: {e}")
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