# WhatsApp Agent Deployment Guide

Complete step-by-step guide for deploying the scalable WhatsApp agent architecture.

## 🎯 Prerequisites

### 1. Google Cloud Setup

```bash
# Install gcloud CLI (if not already installed)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Authenticate
gcloud auth login
gcloud auth application-default login

# Set project
export GCP_PROJECT="your-project-id"
gcloud config set project $GCP_PROJECT
```

### 2. Enable Required APIs

```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com  
gcloud services enable pubsub.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 3. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create whatsapp-agent \
    --description="WhatsApp Agent Service Account" \
    --display-name="WhatsApp Agent"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:whatsapp-agent@$GCP_PROJECT.iam.gserviceaccount.com" \
    --role="roles/pubsub.subscriber"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:whatsapp-agent@$GCP_PROJECT.iam.gserviceaccount.com" \
    --role="roles/pubsub.publisher"

gcloud projects add-iam-policy-binding $GCP_PROJECT \
    --member="serviceAccount:whatsapp-agent@$GCP_PROJECT.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

## 🔐 Environment Setup

### 1. Create Secrets

```bash
# OpenAI API Key
echo "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-

# AiSensy Access Token
echo "your-aisensy-token" | gcloud secrets create aisensy-access-token --data-file=-

# Webhook Verify Token
echo "your-webhook-verify-token" | gcloud secrets create webhook-verify-token --data-file=-

# Supabase URL
echo "your-supabase-url" | gcloud secrets create supabase-url --data-file=-

# Supabase Anon Key
echo "your-supabase-anon-key" | gcloud secrets create supabase-anon-key --data-file=-

# Supabase Service Role Key
echo "your-supabase-service-key" | gcloud secrets create supabase-service-role-key --data-file=-
```

### 2. Grant Secret Access

```bash
for secret in openai-api-key aisensy-access-token webhook-verify-token supabase-url supabase-anon-key supabase-service-role-key; do
    gcloud secrets add-iam-policy-binding $secret \
        --member="serviceAccount:whatsapp-agent@$GCP_PROJECT.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
done
```

## 🏗️ Infrastructure Setup

### 1. Create Pub/Sub Resources

```bash
# Create topic
gcloud pubsub topics create whatsapp-prop8t-message-processing

# Create subscription
gcloud pubsub subscriptions create whatsapp-prop8t-message-processing-sub \
    --topic=whatsapp-prop8t-message-processing \
    --message-retention-duration=7d \
    --ack-deadline=60s \
    --max-delivery-attempts=5
```

### 2. Create Artifact Registry

```bash
gcloud artifacts repositories create whatsapp-agent \
    --repository-format=docker \
    --location=asia-south1 \
    --description="WhatsApp Agent containers"
```

## 🚀 Service Deployment

### 1. Deploy Ingestion Service

```bash
# Build and deploy
gcloud builds submit --config=deployment/cloudbuild-ingestion.yaml \
    --substitutions=_REGION=asia-south1

# Update environment variables
gcloud run services update whatsapp-agent-ingestion-service \
    --region=asia-south1 \
    --set-env-vars="WEBHOOK_VERIFY_TOKEN=$(gcloud secrets versions access latest --secret=webhook-verify-token)"
```

### 2. Deploy Processing Worker

```bash
# Build and deploy
gcloud builds submit --config=deployment/cloudbuild-processing.yaml \
    --substitutions=_REGION=asia-south1

# Update environment variables
gcloud run services update whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --set-env-vars="OPENAI_API_KEY=$(gcloud secrets versions access latest --secret=openai-api-key),AISENSY_ACCESS_TOKEN=$(gcloud secrets versions access latest --secret=aisensy-access-token),NEXT_PUBLIC_SUPABASE_URL=$(gcloud secrets versions access latest --secret=supabase-url),NEXT_PUBLIC_SUPABASE_ANON_KEY=$(gcloud secrets versions access latest --secret=supabase-anon-key),SUPABASE_SERVICE_ROLE_KEY=$(gcloud secrets versions access latest --secret=supabase-service-role-key)"
```

### 3. Get Service URLs

```bash
# Ingestion service URL
INGESTION_URL=$(gcloud run services describe whatsapp-agent-ingestion-service \
    --region=asia-south1 --format="value(status.url)")

# Processing worker URL  
PROCESSING_URL=$(gcloud run services describe whatsapp-agent-processing-worker \
    --region=asia-south1 --format="value(status.url)")

echo "Ingestion Service: $INGESTION_URL"
echo "Processing Worker: $PROCESSING_URL"
```

## ✅ Verification

### 1. Health Checks

```bash
# Check ingestion service
curl $INGESTION_URL/health

# Check processing worker
curl $PROCESSING_URL/health
```

### 2. Test Flow

```bash
# Test ingestion (should return "OK")
curl -X POST $INGESTION_URL \
    -H "Content-Type: application/json" \
    -d '{"test": "webhook"}'

# Test processing worker directly
curl -X POST $PROCESSING_URL/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello", "userId": "test"}'
```

### 3. Monitor Pub/Sub

```bash
# Check if messages are being published/consumed
gcloud pubsub topics list
gcloud pubsub subscriptions describe whatsapp-message-processing-sub
```

## 🔧 Configuration

### 1. Webhook Setup

Configure your WhatsApp/AiSensy webhook URL to:
```
https://your-ingestion-service-url
```

### 2. Verification Token

Use the same token you stored in Secret Manager for webhook verification.

### 3. Environment-specific Settings

For different environments:

```bash
# Development
gcloud run services update whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --set-env-vars="DEBUG=true,LOG_LEVEL=DEBUG"

# Production
gcloud run services update whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --set-env-vars="DEBUG=false,LOG_LEVEL=INFO"
```

## 📊 Monitoring Setup

### 1. Logging

```bash
# View ingestion logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-agent-ingestion-service"

# View processing logs
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=whatsapp-agent-processing-worker"
```

### 2. Alerts

Create alerting policies:

```bash
# Example: High error rate alert
gcloud alpha monitoring policies create \
    --policy-from-file=monitoring/error-rate-alert.yaml
```

### 3. Dashboards

Import monitoring dashboards for:
- Message processing rates
- Error rates
- Response times
- Resource utilization

## 🔄 Updates and Maintenance

### 1. Rolling Updates

```bash
# Deploy new version
gcloud builds submit --config=deployment/cloudbuild-processing.yaml \
    --substitutions=_REGION=asia-south1

# Traffic gradually migrates to new version
```

### 2. Rollback

```bash
# List revisions
gcloud run revisions list --service=whatsapp-agent-processing-worker --region=asia-south1

# Rollback to previous revision
gcloud run services update-traffic whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --to-revisions=REVISION_NAME=100
```

### 3. Scaling Adjustments

```bash
# Adjust scaling limits
gcloud run services update whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --max-instances=30 \
    --min-instances=2
```

## 🛠️ Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   gcloud logs read "resource.type=cloud_run_revision" --limit=50
   ```

2. **Environment variables not loading**
   ```bash
   # Verify secrets
   gcloud secrets versions access latest --secret=openai-api-key
   ```

3. **Pub/Sub messages not processing**
   ```bash
   # Check subscription status
gcloud pubsub subscriptions describe whatsapp-prop8t-message-processing-sub
   ```

### Debug Mode

Enable debug mode for detailed logging:

```bash
gcloud run services update whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --set-env-vars="DEBUG=true,LOG_LEVEL=DEBUG"
```

## 🔒 Security Checklist

- [ ] Service accounts use minimal permissions
- [ ] Secrets stored in Secret Manager
- [ ] HTTPS enforced on all endpoints
- [ ] Webhook verification enabled
- [ ] Access logs enabled
- [ ] Network security configured

## 📈 Performance Optimization

### 1. Resource Allocation

```bash
# Optimize for high throughput
gcloud run services update whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --memory=2Gi \
    --cpu=4 \
    --concurrency=1000
```

### 2. Cold Start Optimization

```bash
# Keep minimum instances warm
gcloud run services update whatsapp-agent-processing-worker \
    --region=asia-south1 \
    --min-instances=3
```

## 🎉 Deployment Complete

Your WhatsApp agent is now deployed with:

✅ **Scalable architecture** with pub/sub messaging  
✅ **AiSensy integration** for WhatsApp Business API  
✅ **Preserved agent logic** from original system  
✅ **Production-ready** monitoring and logging  
✅ **Auto-scaling** based on demand  

**Next steps:**
1. Configure your webhook URL
2. Test with real WhatsApp messages
3. Monitor performance and adjust scaling
4. Set up alerting and dashboards