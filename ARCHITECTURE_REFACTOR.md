# WhatsApp Agent Architecture Refactoring

## Overview
Transforming the current WhatsApp agent from a simple webhook handler to a scalable pub/sub architecture with AISensy integration, following the reference implementation in `/Reference/`.

## Current vs Target Architecture

### Current Architecture (whatsappAgent/)
```
WhatsApp → FastAPI Webhook → Agent System → Response (Log Only)
```
- Single service handling everything
- Direct webhook processing
- No external messaging integration
- Limited scalability

### Target Architecture (After Refactoring)
```
WhatsApp → Ingestion Service → Pub/Sub → Processing Worker → AISensy → WhatsApp
```
- **Ingestion Service**: Receives webhooks, publishes to pub/sub
- **Processing Worker**: Subscribes to pub/sub, processes with agents, sends via AISensy
- **Pub/Sub**: Google Cloud Pub/Sub for reliable message queuing
- **AISensy**: External messaging service for WhatsApp API

## Key Components to Refactor

### 1. Ingestion Service (NEW)
- **Purpose**: Lightweight webhook receiver
- **Responsibilities**:
  - Accept WhatsApp webhooks
  - Validate webhook tokens
  - Publish raw messages to pub/sub topic
  - Return immediate response to WhatsApp
- **Technology**: Flask (like reference)
- **Deployment**: Cloud Run

### 2. Processing Worker (REFACTORED)
- **Purpose**: Message processing with agents
- **Responsibilities**:
  - Subscribe to pub/sub messages
  - Parse WhatsApp message format
  - Route to appropriate agent (existing logic preserved)
  - Send responses via AISensy
  - Handle message status updates
  - Manage conversation sessions
- **Technology**: FastAPI (current) + Pub/Sub
- **Deployment**: Cloud Run

### 3. AISensy Integration (NEW)
- **Services Required**:
  - Message sending (text, images, documents)
  - Token authentication and refresh
  - Message status tracking
  - Error handling and retries
- **Based on**: Reference implementation

### 4. Configuration Management (NEW)
- Centralized config like reference
- Environment-based settings
- Token management
- Database connections

## Agent System Preservation

### ✅ PRESERVE COMPLETELY
- **Agent Logic**: All existing agent routing and processing
- **Tool Systems**: Property search, statistics, follow-up tools
- **Session Management**: User sessions and conversation history
- **Multi-Agent System**: Triage, conversation, property, statistics, follow-up agents

### 🔄 ADAPT ONLY
- **Input Source**: From FastAPI request → From pub/sub message
- **Output Target**: From log response → To AISensy API
- **Error Handling**: Enhanced for pub/sub failures

## Implementation Plan

### Phase 1: Foundation Setup
1. Create ingestion service structure
2. Add configuration management
3. Setup pub/sub topic and subscription

### Phase 2: Service Implementation
1. Implement ingestion service (webhook → pub/sub)
2. Refactor processing worker (pub/sub → agents → AISensy)
3. Add AISensy integration services

### Phase 3: Deployment & Testing
1. Dockerize both services
2. Setup Cloud Run deployment
3. Test complete flow
4. Performance optimization

## Directory Structure (After Refactoring)

```
whatsappAgent/
├── ingestion-service/          # NEW: Webhook receiver
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── processing-worker/          # REFACTORED: Agent processor
│   ├── main.py
│   ├── agents/                 # PRESERVED: All agent logic
│   ├── tools/                  # PRESERVED: All tools
│   ├── utils/                  # PRESERVED: Utilities
│   ├── src/
│   │   ├── config.py           # NEW: Configuration
│   │   ├── services/           # NEW: AISensy integration
│   │   └── utils/              # NEW: Pub/sub utilities
│   ├── Dockerfile
│   └── requirements.txt
├── deployment/                 # NEW: Deployment configs
│   ├── cloudbuild-ingestion.yaml
│   ├── cloudbuild-processing.yaml
│   └── deploy.sh
└── README.md                   # UPDATED: New architecture docs
```

## Key Features to Implement

### Ingestion Service Features
- ✅ Webhook verification
- ✅ Message validation
- ✅ Pub/Sub publishing
- ✅ Health checks
- ✅ Error handling

### Processing Worker Features
- ✅ Pub/Sub subscription
- ✅ Agent system integration (preserved)
- ✅ AISensy message sending
- ✅ Token management
- ✅ Message status tracking
- ✅ Session persistence
- ✅ Error retry logic

### AISensy Integration Features
- ✅ Text message sending
- ✅ Image message sending
- ✅ Document message sending
- ✅ Authentication & token refresh
- ✅ Message read receipts
- ✅ Status update handling

## Risk Mitigation

### Agent Logic Protection
- **No Changes**: Agent system remains completely intact
- **Interface Adaptation**: Only input/output adapters change
- **Testing**: Extensive testing of agent responses

### Deployment Safety
- **Staged Rollout**: Deploy ingestion first, then processing
- **Fallback**: Keep current system running during transition
- **Monitoring**: Comprehensive logging and monitoring

### Data Consistency
- **Session Persistence**: Maintain user sessions across services
- **Message Ordering**: Ensure message processing order
- **Duplicate Handling**: Prevent duplicate message processing

## Success Criteria

1. **Functional**: All current agent features work identically
2. **Scalable**: Can handle multiple concurrent conversations
3. **Reliable**: Messages are not lost, proper error handling
4. **Performance**: Response times comparable to current system
5. **Deployable**: Automated deployment to Cloud Run
6. **Maintainable**: Clean separation of concerns

## Next Steps

1. ✅ Create this documentation
2. ✅ Setup ingestion service
3. ✅ Refactor processing worker
4. ✅ Implement AISensy integration
5. ✅ Setup deployment pipeline
6. ✅ Test and validate

---

**Note**: This refactoring maintains 100% backward compatibility for agent logic while adding enterprise-grade scalability and external messaging integration.