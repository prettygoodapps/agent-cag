#!/bin/bash

# Agent CAG Speech Generator
# Usage: ./agent_speak.sh "Your text here" [--sardaukar]

set -e

# Configuration
API_URL="http://localhost:8000"
TTS_URL="http://localhost:8003"
TEMP_DIR="/tmp"

# Default parameters
TEXT=""
USE_SARDAUKAR=false
USER_ID="cli-user-$(date +%s)"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --sardaukar|-s)
            USE_SARDAUKAR=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 \"Your text here\" [--sardaukar]"
            echo ""
            echo "Options:"
            echo "  --sardaukar, -s    Translate to Sardaukar language"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 \"Hello, how are you?\""
            echo "  $0 \"Tell me about the weather\" --sardaukar"
            exit 0
            ;;
        *)
            if [[ -z "$TEXT" ]]; then
                TEXT="$1"
            else
                echo "Error: Multiple text arguments provided. Use quotes for multi-word text."
                exit 1
            fi
            shift
            ;;
    esac
done

# Check if text is provided
if [[ -z "$TEXT" ]]; then
    echo "Error: No text provided."
    echo "Usage: $0 \"Your text here\" [--sardaukar]"
    exit 1
fi

# Check if services are running
if ! curl -s "$API_URL/health" > /dev/null; then
    echo "Error: Agent CAG API service is not running on $API_URL"
    echo "Please start the services with: sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d"
    exit 1
fi

echo "🎤 Generating speech for: \"$TEXT\""
if [[ "$USE_SARDAUKAR" == "true" ]]; then
    echo "🌌 Using Sardaukar translation"
fi

# Create JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
    "text": "$TEXT",
    "user_id": "$USER_ID",
    "generate_speech": true,
    "use_sardaukar": $USE_SARDAUKAR
}
EOF
)

# Make API request
echo "📡 Sending request to Agent CAG..."
RESPONSE=$(curl -s -X POST "$API_URL/query" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD")

# Check if request was successful
if [[ $? -ne 0 ]]; then
    echo "❌ Error: Failed to connect to Agent CAG API"
    exit 1
fi

# Extract response text and audio URL
RESPONSE_TEXT=$(echo "$RESPONSE" | grep -o '"text":"[^"]*"' | sed 's/"text":"//' | sed 's/"$//')
AUDIO_URL=$(echo "$RESPONSE" | grep -o '"/audio/[^"]*"' | tr -d '"')

if [[ -z "$AUDIO_URL" ]]; then
    echo "❌ Error: No audio URL received from API"
    echo "Response: $RESPONSE"
    exit 1
fi

echo "💬 AI Response: $RESPONSE_TEXT"

# Download and play audio
AUDIO_FILE="$TEMP_DIR/agent_speech_$(date +%s).wav"
echo "🔊 Downloading and playing audio..."

curl -s "$TTS_URL$AUDIO_URL" -o "$AUDIO_FILE"

if [[ $? -eq 0 && -f "$AUDIO_FILE" ]]; then
    echo "▶️  Playing audio..."
    play "$AUDIO_FILE" 2>/dev/null
    
    # Clean up
    rm -f "$AUDIO_FILE"
    echo "✅ Done!"
else
    echo "❌ Error: Failed to download audio file"
    exit 1
fi