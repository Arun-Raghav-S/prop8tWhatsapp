#!/bin/bash

# WhatsApp Agent Local Test Client Runner
# This script runs the local test client for the WhatsApp agent

echo "🚀 Starting WhatsApp Agent Local Test Client..."
echo "================================================"

# Check if we're in the right directory
if [ ! -f "local_test_client.py" ]; then
    echo "❌ Error: local_test_client.py not found"
    echo "Please run this script from the processing-worker directory"
    exit 1
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "You may need to create a .env file with required environment variables:"
    echo "  - NEXT_PUBLIC_SUPABASE_URL"
    echo "  - NEXT_PUBLIC_SUPABASE_ANON_KEY"
    echo "  - AISENSY_BASE_URL"
    echo "  - AISENSY_ACCESS_TOKEN"
    echo ""
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run the local test client
echo "🎯 Launching local test client..."
echo "================================================"
python local_test_client.py

echo "================================================"
echo "👋 Local test client finished"