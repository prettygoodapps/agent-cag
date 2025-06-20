# Agent CAG Speech Tools

Two convenient command-line tools for generating speech from text using the Agent CAG system with optional Sardaukar translation.

## Prerequisites

- Agent CAG services running (use `sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d`)
- Sox audio player installed (`sudo apt install sox`)
- Python 3 with requests library (for Python tool)

## Tools

### 1. Shell Script: `agent_speak.sh`

A bash script for quick speech generation.

#### Usage
```bash
# Basic usage
./agent_speak.sh "Hello, how are you?"

# With Sardaukar translation
./agent_speak.sh "Welcome to Agent CAG" --sardaukar
./agent_speak.sh "Tell me about the weather" -s

# Help
./agent_speak.sh --help
```

#### Features
- ✅ Simple command-line interface
- ✅ Sardaukar translation support
- ✅ Automatic audio playback
- ✅ Service health checking
- ✅ Error handling and cleanup

### 2. Python Script: `agent_speak.py`

A more advanced Python tool with additional features.

#### Usage
```bash
# Basic usage
python3 agent_speak.py "Hello, how are you?"

# With Sardaukar translation
python3 agent_speak.py "Welcome to Agent CAG" --sardaukar
python3 agent_speak.py "Tell me about the weather" -s

# Custom user ID
python3 agent_speak.py "Hello" --user-id my-user

# JSON output only (no audio playback)
python3 agent_speak.py "Hello" --json

# Custom service URLs
python3 agent_speak.py "Hello" --api-url http://localhost:8000 --tts-url http://localhost:8003

# Help
python3 agent_speak.py --help
```

#### Features
- ✅ Advanced command-line interface with argparse
- ✅ Sardaukar translation support
- ✅ Custom user ID support
- ✅ JSON-only output mode
- ✅ Configurable service URLs
- ✅ Comprehensive error handling
- ✅ Automatic cleanup

## Examples

### Basic Speech Generation
```bash
# Shell script
./agent_speak.sh "What is the weather like today?"

# Python script
python3 agent_speak.py "What is the weather like today?"
```

### Sardaukar Translation
```bash
# Shell script
./agent_speak.sh "Hello, welcome to our system" --sardaukar

# Python script
python3 agent_speak.py "Hello, welcome to our system" --sardaukar
```

### Advanced Python Usage
```bash
# Get JSON response without playing audio
python3 agent_speak.py "Hello world" --json

# Use custom user ID
python3 agent_speak.py "Hello world" --user-id test-user-123
```

## How It Works

1. **Text Input**: You provide text to be converted to speech
2. **API Request**: The tool sends a request to the Agent CAG API (`/query` endpoint)
3. **LLM Processing**: The LLM service processes the text and generates a response
4. **Translation** (optional): If `--sardaukar` is used, the response is translated to Sardaukar language
5. **Speech Generation**: The TTS service converts the text to speech using espeak-ng
6. **Audio Playback**: The generated WAV file is automatically downloaded and played
7. **Cleanup**: Temporary files are automatically removed

## Output Format

Both tools provide colorful, emoji-enhanced output:
- 🎤 Text being processed
- 🌌 Sardaukar translation indicator
- 📡 API request status
- 💬 AI response text
- 🔊 Audio processing status
- ▶️ Audio playback indicator
- ✅ Success confirmation

## Error Handling

Both tools include comprehensive error handling:
- Service availability checking
- Network error handling
- Audio file validation
- Automatic cleanup on failure
- Clear error messages with troubleshooting hints

## Service Dependencies

The tools automatically check that these services are running:
- **Agent CAG API** (port 8000): Main orchestration service
- **TTS Service** (port 8003): Text-to-speech conversion
- **Sardaukar Translator** (port 8004): Language translation (when using --sardaukar)

## Troubleshooting

### Services Not Running
```bash
# Start the services
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d

# Check service status
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml ps
```

### Audio Playback Issues
```bash
# Install sox if missing
sudo apt install sox

# Test audio playback manually
play /path/to/audio/file.wav
```

### Python Dependencies
```bash
# Install requests if missing
pip3 install requests