# ingestion-service/main.py
import os
import json
import logging
from flask import Flask, request
from google.cloud import pubsub_v1

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Pub/Sub publisher
publisher = pubsub_v1.PublisherClient()
# Your GCP Project ID will be automatically detected by the Cloud Run environment
PROJECT_ID = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
TOPIC_ID = "prop8t-message-processing"
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

@app.route("/", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "WhatsApp AI Agent Ingestion Service is running",
        "mode": "ingestion_service",
        "topic": topic_path
    }

@app.route("/", methods=["POST"])
def ingest_message():
    """Receive webhooks from AiSensy and publish to Pub/Sub"""
    try:
        # Get the raw request body from AI Sensy
        data = request.get_data()
        if not data:
            logger.error("No data received in webhook")
            return "No data received", 400

        logger.info(f"📥 [INGESTION] Received message, publishing to {topic_path}...")
        logger.info(f"📥 [INGESTION] Data size: {len(data)} bytes")
        
        try:
            # Publish the data as a bytestring to the Pub/Sub topic
            future = publisher.publish(topic_path, data)
            future.result()  # Wait for the publish to complete
            logger.info(f"✅ [INGESTION] Message published successfully to Pub/Sub")
        except Exception as e:
            logger.error(f"❌ [INGESTION] Error publishing to Pub/Sub: {e}")
            return "Error queueing message", 500

        # Immediately return a success response to AI Sensy
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ [INGESTION] Error processing webhook: {e}")
        return "Internal server error", 500

@app.route("/webhook", methods=["GET"])
def webhook_verification():
    """Handle WhatsApp webhook verification"""
    # Get query parameters
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    # Check if this is a verification request
    if mode == "subscribe" and token:
        # You should set a WEBHOOK_VERIFY_TOKEN in your environment
        verify_token = os.getenv("WEBHOOK_VERIFY_TOKEN", "your_verify_token")
        if token == verify_token:
            logger.info("✅ [INGESTION] Webhook verified successfully")
            return str(challenge)
        else:
            logger.error("❌ [INGESTION] Webhook verification failed - invalid token")
            return "Invalid verify token", 403
    
    return "OK", 200

@app.route("/health", methods=["GET"])
def health():
    """Cloud Run health check"""
    return {"status": "healthy", "mode": "ingestion_service"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)