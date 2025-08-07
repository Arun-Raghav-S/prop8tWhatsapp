# Local Testing Guide for WhatsApp Agent

This guide explains how to test the WhatsApp agent locally without requiring pub/sub services.

## Quick Start

1. **Navigate to the processing worker directory:**
   ```bash
   cd whatsappAgent/processing-worker
   ```

2. **Run the local test client:**
   ```bash
   ./run_local_test.sh
   ```

3. **Start chatting with the agent:**
   ```
   [+1234567890] > Hello, tell me about your properties
   ```

## Manual Setup

If you prefer to set up manually:

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file with:
   ```env
   NEXT_PUBLIC_SUPABASE_URL=https://auth.propzing.com
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
   AISENSY_BASE_URL=https://backend.aisensy.com
   AISENSY_ACCESS_TOKEN=your_aisensy_token
   NEXT_PUBLIC_TOOLS_EDGE_FUNCTION_URL=https://auth.propzing.com/functions/v1/whatsapp_agency_tools
   ```

4. **Run the test client:**
   ```bash
   python local_test_client.py
   ```

## Available Commands

Once the client is running, you can use these commands:

- **`/help`** - Show help menu
- **`/user <phone>`** - Change test user number (e.g., `/user +1987654321`)
- **`/account <id>`** - Change WhatsApp business account ID
- **`/session`** - Show current session information
- **`/org`** - Fetch organization metadata for current user/account
- **`/quit`** - Exit the client
- **`<message>`** - Send any message to test the agent

## Example Session

```
🚀 WhatsApp Agent Local Test Client
==================================================
Test User: +1234567890
Business Account: test_business_account
==================================================

[+1234567890] > Hello
💬 Sending: Hello
🤖 Agent thinking...
🤖 Agent Response:
   Hello! I'm your real estate assistant. I can help you find properties, schedule visits, and answer questions about our available properties. What would you like to know?

[+1234567890] > /org
🏢 Fetching organization metadata...
✅ Organization Data:
  {'org_name': 'Test Organization', 'project_names': ['Project A', 'Project B'], ...}

[+1234567890] > Show me properties in Mumbai
💬 Sending: Show me properties in Mumbai
🤖 Agent thinking...
🤖 Agent Response:
   Here are the available properties in Mumbai: ...

[+1234567890] > /quit
👋 Goodbye!
```

## Testing Different Scenarios

### Test Different Users
```
[+1234567890] > /user +9876543210
✅ Changed user from +1234567890 to +9876543210
[+9876543210] > Hello
```

### Test Different Business Accounts
```
[+1234567890] > /account another_business_account
✅ Changed business account from test_business_account to another_business_account
```

### Test Organization Metadata
```
[+1234567890] > /org
🏢 Fetching organization metadata...
```

## Features

- **No Pub/Sub Required**: Test the agent directly without cloud infrastructure
- **Interactive Chat**: Have real conversations with the agent
- **Session Management**: Full session management like the production system
- **Organization Metadata**: Test org details fetching with real API calls
- **Multiple Users**: Switch between different test users
- **Command Interface**: Special commands for testing and debugging

## Troubleshooting

### Missing Dependencies
If you get import errors:
```bash
pip install -r requirements.txt
```

### Environment Variables
Check that all required environment variables are set:
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
vars = ['NEXT_PUBLIC_SUPABASE_URL', 'NEXT_PUBLIC_SUPABASE_ANON_KEY', 'AISENSY_BASE_URL', 'AISENSY_ACCESS_TOKEN']
for var in vars:
    print(f'{var}: {\"✅\" if os.getenv(var) else \"❌\"}')"
```

### Permission Denied
If the script isn't executable:
```bash
chmod +x run_local_test.sh
```

## Notes

- The local client simulates WhatsApp message processing but doesn't actually send messages via AISensy
- All agent logic, session management, and organization metadata fetching work exactly as in production
- Perfect for testing conversation flows, tool usage, and agent responses
- Great for development and debugging without cloud infrastructure costs