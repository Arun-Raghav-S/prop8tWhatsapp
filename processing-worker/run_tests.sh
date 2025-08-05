#!/bin/bash

# WhatsApp Agent Test Runner
# Makes it easy to run different types of tests

echo "🚀 WhatsApp Agent Test Runner"
echo "=============================="

# Check if we're in the right directory
if [ ! -f "automated_test_suite.py" ]; then
    echo "❌ Error: Please run this script from the processing-worker directory"
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage:"
    echo "  ./run_tests.sh full          # Run full automated test suite"
    echo "  ./run_tests.sh quick         # Run quick tests (all 10 questions)"
    echo "  ./run_tests.sh quick 1       # Run quick test for question 1"
    echo "  ./run_tests.sh quick 5       # Run quick test for question 5"
    echo "  ./run_tests.sh interactive   # Start interactive test client"
    echo "  ./run_tests.sh help          # Show this help"
}

# Parse arguments
case "$1" in
    "full")
        echo "📊 Running Full Automated Test Suite..."
        python3 automated_test_suite.py
        ;;
    "quick")
        if [ -z "$2" ]; then
            echo "⚡ Running Quick Test (All Questions)..."
            python3 quick_test.py all
        else
            echo "⚡ Running Quick Test (Question $2)..."
            python3 quick_test.py "$2"
        fi
        ;;
    "interactive")
        echo "💬 Starting Interactive Test Client..."
        python3 local_test_client.py
        ;;
    "help"|"--help"|"-h")
        show_usage
        ;;
    "")
        echo "No arguments provided."
        echo ""
        show_usage
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac