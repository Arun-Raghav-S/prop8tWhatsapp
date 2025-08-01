#!/bin/bash

# Prop8t WhatsApp Processing Worker Deployment Script
# Only builds and deploys the processing worker

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT:-"propzing-bot"}
REGION=${REGION:-"asia-south1"}

echo "🚀 Deploying Prop8t WhatsApp Processing Worker..."
echo "📍 Project: $PROJECT_ID"
echo "📍 Region: $REGION"

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Set project
echo "🔧 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Deploy Processing Worker (Private)
echo "🏗️  Building and deploying Prop8t WhatsApp Processing Worker..."
cd processing-worker

gcloud run deploy prop8t-whatsapp-processing-worker \
  --source . \
  --platform managed \
  --region $REGION \
  --no-allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --max-instances 100 \
  --port 8080 \
  --timeout 900 \
  --execution-environment gen2 \

cd ..

# Get service URL
echo "🌐 Getting service URL..."
PROCESSING_URL=$(gcloud run services describe prop8t-whatsapp-processing-worker --region=$REGION --format="value(status.url)")

echo "✅ Prop8t WhatsApp Processing Worker deployment completed!"
echo ""
echo "🔗 Service URL: $PROCESSING_URL (Private)"