#!/bin/bash

# Prop8t WhatsApp Agent Deployment Script
# Deploys both ingestion service and processing worker to Cloud Run
# Follows the Reference deployment pattern

set -e

# Configuration
PROJECT_ID=${GCP_PROJECT:-"propzing-bot"}
REGION=${REGION:-"asia-south1"}

echo "🚀 Starting Prop8t WhatsApp Agent deployment..."
echo "📍 Project: $PROJECT_ID"
echo "📍 Region: $REGION"

# Ensure we're in the right directory
cd "$(dirname "$0")/.."

# Check if gcloud is authenticated
echo "🔐 Checking authentication..."
gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1
if [ $? -ne 0 ]; then
    echo "❌ Please authenticate with gcloud first:"
    echo "   gcloud auth login"
    exit 1
fi

# Set project
echo "🔧 Setting project to $PROJECT_ID..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable pubsub.googleapis.com

# Create Pub/Sub topic if it doesn't exist (simple name like Reference)
echo "📡 Setting up Pub/Sub infrastructure..."
gcloud pubsub topics create prop8t-message-processing || echo "Topic already exists"

# Deploy Processing Worker (Private) - following Reference pattern
echo "🏗️  Deploying Prop8t WhatsApp Processing Worker..."
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
  --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID,GCP_PROJECT=$PROJECT_ID,PUBSUB_SUBSCRIPTION=prop8t-message-processing-sub,MODE=pub_sub_processing_worker"

cd ..

# Deploy Ingestion Service (Public) - following Reference pattern  
echo "🏗️  Deploying Prop8t WhatsApp Ingestion Service..."
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

# Create Service Account for Pub/Sub
echo "🔐 Setting up Pub/Sub service account..."
gcloud iam service-accounts create prop8t-pubsub-invoker \
  --display-name="Prop8t Pub/Sub to Cloud Run Invoker" \
  || echo "Service account already exists"

# Grant permissions
echo "🔑 Granting permissions..."
gcloud run services add-iam-policy-binding prop8t-whatsapp-processing-worker \
  --member="serviceAccount:prop8t-pubsub-invoker@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --platform managed \
  --region $REGION \
  || echo "Permission already granted"

# Get processing worker URL and create subscription
echo "📡 Creating Pub/Sub subscription..."
WORKER_URL=$(gcloud run services describe prop8t-whatsapp-processing-worker --platform managed --region $REGION --format 'value(status.url)')

gcloud pubsub subscriptions create prop8t-message-processing-sub \
  --topic=prop8t-message-processing \
  --push-endpoint=$WORKER_URL \
  --push-auth-service-account="prop8t-pubsub-invoker@$PROJECT_ID.iam.gserviceaccount.com" \
  || echo "Subscription already exists"

# Get service URLs
echo "🌐 Getting service URLs..."
INGESTION_URL=$(gcloud run services describe prop8t-whatsapp-ingestion-service --region=$REGION --format="value(status.url)")
PROCESSING_URL=$(gcloud run services describe prop8t-whatsapp-processing-worker --region=$REGION --format="value(status.url)")

echo "✅ Prop8t WhatsApp Agent deployment completed successfully!"
echo ""
echo "🔗 Service URLs:"
echo "   Ingestion Service:  $INGESTION_URL"
echo "   Processing Worker:  $PROCESSING_URL (Private)"
echo ""
echo "📋 Next steps:"
echo "   1. Set up environment variables in Cloud Run console"
echo "   2. Configure AiSensy webhook URL to: $INGESTION_URL"
echo "   3. Test the complete flow"
echo ""
echo "🔧 Webhook URL for AiSensy:"
echo "   $INGESTION_URL"