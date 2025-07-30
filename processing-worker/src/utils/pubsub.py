import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from google.cloud import pubsub_v1
from google.cloud.pubsub_v1.subscriber.message import Message
from src.config import config

logger = logging.getLogger(__name__)

class PubSubMessageProcessor:
    """
    Handles Google Cloud Pub/Sub message processing for WhatsApp messages
    """
    
    def __init__(self, message_handler: Callable[[Dict[str, Any]], None]):
        """
        Initialize the Pub/Sub processor
        
        Args:
            message_handler: Async function to handle processed messages
        """
        self.message_handler = message_handler
        self.subscriber = pubsub_v1.SubscriberClient()
        self.project_id = config.GCP_PROJECT
        self.subscription_name = config.PUBSUB_SUBSCRIPTION
        self.subscription_path = self.subscriber.subscription_path(
            self.project_id, self.subscription_name
        )
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        logger.info(f"Initialized Pub/Sub processor for subscription: {self.subscription_path}")
    
    async def start_listening(self):
        """
        Start listening to Pub/Sub messages
        """
        logger.info(f"📡 [PUBSUB] Starting to listen on subscription: {self.subscription_path}")
        
        # Configure subscriber settings for optimal performance
        flow_control = pubsub_v1.types.FlowControl(max_messages=100)
        
        try:
            # Start pulling messages
            pull_future = self.subscriber.pull(
                request={
                    "subscription": self.subscription_path,
                    "max_messages": 10,
                },
                timeout=300.0  # 5 minutes timeout
            )
            
            logger.info("✅ [PUBSUB] Successfully started listening for messages")
            
            # Keep listening in a loop
            while True:
                try:
                    # Pull messages
                    response = self.subscriber.pull(
                        request={
                            "subscription": self.subscription_path,
                            "max_messages": 10,
                        },
                        timeout=30.0
                    )
                    
                    if response.received_messages:
                        logger.info(f"📨 [PUBSUB] Received {len(response.received_messages)} messages")
                        
                        # Process messages concurrently
                        tasks = []
                        for received_message in response.received_messages:
                            task = asyncio.create_task(self._process_message(received_message))
                            tasks.append(task)
                        
                        # Wait for all messages to be processed
                        await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Small delay to prevent overwhelming
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"❌ [PUBSUB] Error in listening loop: {e}")
                    await asyncio.sleep(5)  # Wait before retrying
                    
        except Exception as e:
            logger.error(f"❌ [PUBSUB] Failed to start listening: {e}")
            raise
    
    async def _process_message(self, received_message: Any):
        """
        Process a single Pub/Sub message
        
        Args:
            received_message: The received Pub/Sub message
        """
        try:
            # Extract message data
            message_data = received_message.message.data
            message_id = received_message.message.message_id
            
            logger.info(f"🔄 [PUBSUB] Processing message {message_id}, size: {len(message_data)} bytes")
            
            # Parse the webhook data
            try:
                webhook_data = json.loads(message_data.decode('utf-8'))
                logger.info(f"📥 [PUBSUB] Parsed webhook data: {json.dumps(webhook_data, indent=2)[:500]}...")
            except json.JSONDecodeError as e:
                logger.error(f"❌ [PUBSUB] Failed to parse webhook data as JSON: {e}")
                # Acknowledge the message even if it's malformed
                received_message.ack()
                return
            
            # Process the webhook data through our message handler
            try:
                await self.message_handler(webhook_data)
                logger.info(f"✅ [PUBSUB] Successfully processed message {message_id}")
            except Exception as e:
                logger.error(f"❌ [PUBSUB] Error in message handler for {message_id}: {e}")
                # Don't ack the message if processing failed - it will be retried
                received_message.nack()
                return
            
            # Acknowledge the message after successful processing
            received_message.ack()
            logger.info(f"✅ [PUBSUB] Acknowledged message {message_id}")
            
        except Exception as e:
            logger.error(f"💥 [PUBSUB] Unexpected error processing message: {e}")
            # Nack the message to retry later
            received_message.nack()
    
    def stop_listening(self):
        """
        Stop listening to Pub/Sub messages
        """
        logger.info("🛑 [PUBSUB] Stopping Pub/Sub listener")
        self.subscriber.close()
        self.executor.shutdown(wait=True)

def extract_whatsapp_messages(webhook_data: Dict[str, Any]) -> list:
    """
    Extract WhatsApp messages from webhook data
    
    Args:
        webhook_data: Raw webhook data from WhatsApp/AiSensy
        
    Returns:
        List of message objects to process
    """
    messages = []
    
    try:
        # Handle WhatsApp webhook format
        if "entry" in webhook_data:
            for entry in webhook_data["entry"]:
                if "changes" in entry:
                    for change in entry["changes"]:
                        if change.get("field") == "messages":
                            value = change.get("value", {})
                            
                            # Extract messages
                            if "messages" in value:
                                for message in value["messages"]:
                                    messages.append({
                                        "message": message,
                                        "value": value,
                                        "change": change,
                                        "entry": entry
                                    })
                            
                            # Extract status updates
                            if "statuses" in value:
                                for status in value["statuses"]:
                                    messages.append({
                                        "status": status,
                                        "value": value,
                                        "change": change,
                                        "entry": entry,
                                        "type": "status_update"
                                    })
        
        logger.info(f"📨 [EXTRACT] Extracted {len(messages)} messages from webhook data")
        return messages
        
    except Exception as e:
        logger.error(f"❌ [EXTRACT] Error extracting messages from webhook: {e}")
        return []

def get_business_account_from_webhook(webhook_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract WhatsApp business account ID from webhook data
    
    Args:
        webhook_data: Raw webhook data
        
    Returns:
        Business account ID if found, None otherwise
    """
    try:
        # Try to extract from entry metadata
        if "entry" in webhook_data and len(webhook_data["entry"]) > 0:
            entry = webhook_data["entry"][0]
            
            # Check for business account ID in entry
            if "id" in entry:
                return entry["id"]
            
            # Check in changes
            if "changes" in entry and len(entry["changes"]) > 0:
                change = entry["changes"][0]
                if "value" in change:
                    value = change["value"]
                    
                    # Check for whatsapp_business_account_id
                    if "metadata" in value and "whatsapp_business_account_id" in value["metadata"]:
                        return value["metadata"]["whatsapp_business_account_id"]
                    
                    # Check for phone_number_id which might be used as business account
                    if "metadata" in value and "phone_number_id" in value["metadata"]:
                        return value["metadata"]["phone_number_id"]
        
        logger.warning("⚠️ [EXTRACT] Could not find business account ID in webhook data")
        return None
        
    except Exception as e:
        logger.error(f"❌ [EXTRACT] Error extracting business account from webhook: {e}")
        return None