#!/bin/bash

# Prop8t WhatsApp Ingestion Service Deployment Script
# Only builds and deploys the ingestion service

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT:-"propzing-bot"}
REGION=${REGION:-"asia-south1"}

echo "🚀 Deploying Prop8t WhatsApp Ingestion Service..."
echo "📍 Project: $PROJECT_ID"
echo "📍 Region: $REGION"

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Set project
echo "🔧 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Deploy Ingestion Service (Public)
echo "🏗️  Building and deploying Prop8t WhatsApp Ingestion Service..."
cd ingestion-service

gcloud run deploy prop8t-whatsapp-ingestion-service \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --max-instances 50 \
  --port 8080 \
  --timeout 300 \
  --execution-environment gen2 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCP_PROJECT=$PROJECT_ID,MODE=ingestion_service"

cd ..

# Get service URL
echo "🌐 Getting service URL..."
INGESTION_URL=$(gcloud run services describe prop8t-whatsapp-ingestion-service --region=$REGION --format="value(status.url)")

echo "✅ Prop8t WhatsApp Ingestion Service deployment completed!"
echo ""
echo "🔗 Service URL: $INGESTION_URL"
echo ""
echo "🔧 Webhook URL for AiSensy: $INGESTION_URL"