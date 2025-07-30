# WhatsApp Agent - Scalable Architecture v2.0

**Pub/Sub based WhatsApp agent with AiSensy integration for enterprise scale**

## 🏗️ Architecture Overview

```
WhatsApp/AiSensy → Ingestion Service → Pub/Sub → Processing Worker → AiSensy → WhatsApp
```

### Components

1. **Ingestion Service** - Lightweight webhook receiver
2. **Processing Worker** - Agent system with pub/sub integration
3. **Pub/Sub** - Google Cloud Pub/Sub for reliable messaging
4. **AiSensy** - WhatsApp Business API integration

## 🚀 Quick Start

### Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Docker (for local development)

### Deployment

```bash
# Set your project ID
export GCP_PROJECT="your-project-id"

# Deploy both services
cd whatsappAgent
./deployment/deploy.sh
```

### Environment Variables

Set these environment variables for both services:

```bash
# Required for Processing Worker
OPENAI_API_KEY="your-openai-key"
AISENSY_ACCESS_TOKEN="your-aisensy-token"
NEXT_PUBLIC_SUPABASE_URL="your-supabase-url"
NEXT_PUBLIC_SUPABASE_ANON_KEY="your-supabase-anon-key"
SUPABASE_SERVICE_ROLE_KEY="your-supabase-service-key"

# Optional
WEBHOOK_VERIFY_TOKEN="your-webhook-token"
DEBUG="false"
LOG_LEVEL="INFO"
```

## 📁 Project Structure

```
whatsappAgent/
├── ingestion-service/          # Webhook receiver
│   ├── main.py                 # Flask app for webhooks
│   ├── Dockerfile              # Container config
│   └── requirements.txt        # Dependencies
├── processing-worker/          # Message processor
│   ├── main.py                 # FastAPI app with pub/sub
│   ├── agents/                 # Agent system (preserved) 
│   ├── tools/                  # Agent tools (preserved)
│   ├── utils/                  # Utilities (preserved)
│   ├── src/
│   │   ├── config.py           # Configuration
│   │   ├── services/           # AiSensy integration
│   │   └── utils/              # Pub/sub utilities
│   ├── Dockerfile              # Container config
│   └── requirements.txt        # Dependencies
├── deployment/                 # Deployment configs
│   ├── cloudbuild-ingestion.yaml
│   ├── cloudbuild-processing.yaml
│   └── deploy.sh               # Deployment script
└── README.md                   # This file
```

## 🔧 Configuration

### Ingestion Service

- **Purpose**: Receive webhooks, publish to pub/sub
- **Topic**: `whatsapp-prop8t-message-processing`
- **Endpoint**: `/` (POST) for webhooks
- **Health**: `/health` (GET)
- **Memory**: 512Mi
- **CPU**: 1 core

### Processing Worker

- **Purpose**: Process messages with agents, send via AiSensy
- **Subscription**: `whatsapp-prop8t-message-processing-sub`
- **Endpoints**: `/health`, `/chat` (for testing)
- **Memory**: 1Gi
- **CPU**: 2 cores
- **Timeout**: 15 minutes

## 🧪 Testing

### Test Ingestion Service

```bash
curl -X POST https://your-ingestion-url \
  -H "Content-Type: application/json" \
  -d '{"test": "message"}'
```

### Test Processing Worker

```bash
curl -X POST https://your-processing-url/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "userId": "test-user"}'
```

## 🌐 Production Setup

### 1. Webhook Configuration

Point your WhatsApp/AiSensy webhook to:
```
https://your-ingestion-service-url
```

### 2. Environment Variables

Use Google Cloud Secret Manager for production:

```bash
# Create secrets
gcloud secrets create aisensy-token --data-file=token.txt
gcloud secrets create openai-api-key --data-file=key.txt

# Grant access to service account
gcloud secrets add-iam-policy-binding aisensy-token \
    --member="serviceAccount:whatsapp-agent@your-project.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Monitoring

- **Logs**: Cloud Logging automatically enabled
- **Metrics**: Cloud Monitoring for both services
- **Alerts**: Set up on pub/sub queue depth and error rates

## 🔍 Troubleshooting

### Common Issues

1. **Messages not processing**
   - Check pub/sub subscription has messages
   - Verify processing worker is running
   - Check logs for errors

2. **AiSensy authentication errors**
   - Verify access token is valid
   - Check token refresh logic
   - Ensure business account ID is correct

3. **Agent responses not working**
   - Verify OpenAI API key
   - Check agent system logs
   - Test with `/chat` endpoint

### Debugging

```bash
# View ingestion service logs
gcloud logs read "projects/YOUR_PROJECT/logs/whatsapp-agent-ingestion-service"

# View processing worker logs  
gcloud logs read "projects/YOUR_PROJECT/logs/whatsapp-agent-processing-worker"

# Check pub/sub metrics
gcloud pubsub topics list
gcloud pubsub subscriptions list
```

## 🔄 Migration from v1.0

The agent system logic is **100% preserved**. Only the input/output mechanisms changed:

- **Before**: Direct webhook → Agent → Log response
- **After**: Webhook → Pub/Sub → Agent → AiSensy response

All existing agents, tools, and session management work identically.

## 📈 Scaling

### Auto-scaling Configuration

- **Ingestion**: Up to 20 instances, min 1
- **Processing**: Up to 15 instances, min 1
- **Pub/Sub**: Unlimited throughput

### Performance Optimization

1. **Ingestion Service**: Optimized for fast webhook response
2. **Processing Worker**: Optimized for AI processing
3. **Pub/Sub**: Reliable message queuing with retries

## 🛡️ Security

- Service accounts with minimal permissions
- Secret Manager for sensitive data
- HTTPS/TLS for all communications
- VPC connector for internal communication (optional)

## 📊 Monitoring & Alerts

### Key Metrics

- Message processing rate
- Error rates
- Response times
- Pub/sub queue depth
- Memory/CPU usage

### Recommended Alerts

```bash
# High error rate
error_rate > 5%

# Queue backup
pubsub_queue_depth > 100

# High latency
response_time > 10s
```

## 🚀 Advanced Features

### Multi-tenant Support

Each WhatsApp business account gets isolated processing with separate tokens and configurations.

### Horizontal Scaling

Both services scale independently based on load:
- Ingestion scales with webhook volume
- Processing scales with message complexity

### Fault Tolerance

- Pub/sub message retries
- Graceful error handling
- Health checks and auto-recovery

## 📚 Documentation Links

- [Architecture Refactor Plan](./ARCHITECTURE_REFACTOR.md)
- [Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [Google Cloud Pub/Sub](https://cloud.google.com/pubsub/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [AiSensy API Documentation](https://docs.aisensy.com/)

---

**Version**: 2.0.0  
**Last Updated**: December 2024  
**Architecture**: Pub/Sub + Cloud Run  
**Agent System**: Fully Preserved from v1.0