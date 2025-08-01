#!/bin/bash

# Script to extract textPayload and jsonPayload from logs.json
# It saves the output to a single file, preserving the order.
# Usage: ./extract_all_payloads.sh

# Define file paths
LOGS_FILE="../logs/logs.json"
OUTPUT_FILE="../logs/extracted_payloads.log"

# Check if logs.json exists
if [ ! -f "$LOGS_FILE" ]; then
    echo "❌ Error: $LOGS_FILE file not found!"
    echo "Make sure the logs.json file exists in the ../logs/ directory."
    exit 1
fi

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is not installed. Please install jq to parse JSON."
    echo "You can install it with 'brew install jq' on macOS or 'sudo apt-get install jq' on Debian/Ubuntu."
    exit 1
fi

echo "🚀 Extracting textPayload and jsonPayload from $LOGS_FILE..."

# Use jq to process the log file.
# For each entry in the array (.[]):
# - Check if .textPayload is not null. If so, use it.
# - Otherwise, take the .jsonPayload and convert it to a compact string (tostring).
# - This ensures each payload appears on a single line in the output file.
jq -r '.[] | if .textPayload != null then .textPayload else .jsonPayload | tostring end' "$LOGS_FILE" > "$OUTPUT_FILE"


# Check if the extraction was successful
if [ $? -eq 0 ]; then
    # Count how many entries were extracted
    ENTRY_COUNT=$(wc -l < "$OUTPUT_FILE")
    echo "✅ Extraction complete!"
    echo "📄 Output saved to: $OUTPUT_FILE"
    echo "📊 Extracted $ENTRY_COUNT total log payloads."

    # Show a preview of the extracted logs
    if [ "$ENTRY_COUNT" -gt 0 ]; then
        echo ""
        echo "📝 Preview of the first 5 extracted payloads:"
        head -5 "$OUTPUT_FILE"
        if [ "$ENTRY_COUNT" -gt 5 ]; then
            echo "... (and $((ENTRY_COUNT - 5)) more entries)"
        fi
    else
        echo "⚠️ No textPayload or jsonPayload entries were found in the logs."
    fi
else
    echo "❌ Error: Failed to extract payloads. Please check the JSON format in $LOGS_FILE."
    exit 1
fi