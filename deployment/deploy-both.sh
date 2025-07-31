#!/bin/bash

# Prop8t WhatsApp Agent Deployment Script
# Deploys both ingestion service and processing worker

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT:-"propzing-bot"}
REGION=${REGION:-"asia-south1"}

echo "🚀 Deploying both Prop8t WhatsApp services..."
echo "📍 Project: $PROJECT_ID"
echo "📍 Region: $REGION"

# Get script directory
SCRIPT_DIR="$(dirname "$0")"

# Deploy ingestion service
echo "1️⃣  Deploying Ingestion Service..."
bash "$SCRIPT_DIR/deploy-ingestion.sh"

echo ""
echo "2️⃣  Deploying Processing Worker..."
bash "$SCRIPT_DIR/deploy-processing.sh"

# Get service URLs
echo ""
echo "🌐 Getting final service URLs..."
INGESTION_URL=$(gcloud run services describe prop8t-whatsapp-ingestion-service --region=$REGION --format="value(status.url)")
PROCESSING_URL=$(gcloud run services describe prop8t-whatsapp-processing-worker --region=$REGION --format="value(status.url)")

echo ""
echo "✅ All Prop8t WhatsApp services deployed successfully!"
echo ""
echo "🔗 Service URLs:"
echo "   Ingestion Service:  $INGESTION_URL"
echo "   Processing Worker:  $PROCESSING_URL (Private)"
echo ""
echo "🔧 Webhook URL for AiSensy: $INGESTION_URL"