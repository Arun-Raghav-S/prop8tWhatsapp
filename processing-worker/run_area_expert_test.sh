#!/bin/bash

# Area Expert Integration Test Runner
# Runs comprehensive tests for the area expert API integration

echo "=================================="
echo "🧪 Area Expert Integration Tests"
echo "=================================="
echo ""

# Check if we're in the right directory
if [ ! -f "test_area_expert.py" ]; then
    echo "❌ Error: test_area_expert.py not found"
    echo "Please run this script from the processing-worker directory"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "Make sure environment variables are set:"
    echo "  - SUPABASE_ANON_KEY"
    echo "  - SUPABASE_URL"
    echo "  - OPENAI_API_KEY"
    echo ""
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
else
    echo "⚠️  Warning: venv not found, using system Python"
fi

# Run the tests
echo ""
echo "🚀 Running tests..."
echo ""

python3 test_area_expert.py

echo ""
echo "=================================="
echo "✅ Test run complete!"
echo "=================================="

