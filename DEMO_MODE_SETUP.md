# Agent CAG Demo Mode Setup Guide

## Overview

Agent CAG now supports a **Demo Mode** that allows you to test the complete system without requiring external API keys or local LLM models. This is perfect for:

- Testing the system architecture
- Demonstrating functionality
- Development and debugging
- Systems with limited memory/resources

## Port Assignments

The system uses the following port mappings:

| Service | Internal Port | External Port | URL |
|---------|---------------|---------------|-----|
| Main API | 8000 | 8000 | http://localhost:8000 |
| ASR Service | 8001 | 8001 | http://localhost:8001 |
| LLM Service | 8002 | 8002 | http://localhost:8002 |
| TTS Service | 8003 | 8003 | http://localhost:8003 |
| Translation Service | 8000 | 8004 | http://localhost:8004 |
| Ollama (disabled in demo) | 11434 | 11434 | N/A |

## Quick Start

### 1. Start Demo Mode

```bash
# Start all services in demo mode
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d

# Check service status
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml ps
```

### 2. Test the System

```bash
# Test the main API endpoint
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is 2+2?",
    "user_id": "demo-user"
  }'

# Expected response:
# {
#   "query_id": "...",
#   "response_id": "...",
#   "text": "2 + 2 = 4. This is a basic arithmetic operation...",
#   "audio_url": null,
#   "metadata": {
#     "provider": "demo",
#     "model": "demo-model",
#     "demo_mode": true,
#     ...
#   }
# }
```

### 3. Check Service Health

```bash
# Check all services are healthy
curl http://localhost:8000/health  # Main API
curl http://localhost:8001/health  # ASR Service
curl http://localhost:8002/health  # LLM Service (Demo)
curl http://localhost:8003/health  # TTS Service
curl http://localhost:8004/health  # Translation Service
```

## Demo Mode Features

### Smart Response System

The demo LLM provides intelligent responses for various types of queries:

#### Math Questions
```bash
curl -X POST "http://localhost:8002/generate" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is 15 * 3?", "temperature": 0.7}'
```

#### Greetings
```bash
curl -X POST "http://localhost:8002/generate" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, who are you?", "temperature": 0.7}'
```

#### Help/Information
```bash
curl -X POST "http://localhost:8002/generate" \
  -H "Content-Type: application/json" \
  -d '{"text": "What can you help me with?", "temperature": 0.7}'
```

#### Programming Questions
```bash
curl -X POST "http://localhost:8002/generate" \
  -H "Content-Type: application/json" \
  -d '{"text": "Can you help with Python code?", "temperature": 0.7}'
```

### Available Endpoints

- **Main API** (Port 8000): `http://localhost:8000`
  - `POST /query` - Process text queries
  - `GET /health` - Service health check
  - `GET /queries/{user_id}` - Get user query history

- **LLM Service** (Port 8002): `http://localhost:8002`
  - `POST /generate` - Direct text generation
  - `POST /chat` - Chat completion
  - `GET /models` - List available models
  - `GET /health` - Service health check

- **ASR Service** (Port 8001): `http://localhost:8001`
  - `POST /transcribe` - Audio transcription
  - `GET /health` - Service health check

- **TTS Service** (Port 8003): `http://localhost:8003`
  - `POST /synthesize` - Text-to-speech
  - `GET /health` - Service health check

- **Translation Service** (Port 8004): `http://localhost:8004`
  - Translation endpoints
  - `GET /api/health` - Service health check

## Configuration

### Demo Mode Environment Variables

The demo mode uses these settings in `docker-compose.demo.yml`:

```yaml
services:
  ollama:
    deploy:
      replicas: 0  # Disable Ollama service
  
  llm:
    environment:
      - LLM_PROVIDER=demo
      - MODEL_NAME=demo-model
      - LLM_API_KEY=demo_key
```

### Switching to Production Mode

To switch from demo mode to a production LLM provider:

#### Option 1: Use Groq (Free API)
```bash
# Stop demo mode
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml down

# Start with Groq
export LLM_API_KEY="your-groq-api-key"
sudo docker-compose -f docker-compose.yml -f docker-compose.remote-llm.yml up -d
```

#### Option 2: Use OpenAI
```bash
# Create custom override file
cat > docker-compose.openai.yml << EOF
version: '3.9'
services:
  ollama:
    deploy:
      replicas: 0
  llm:
    environment:
      - PYTHONPATH=/app
      - LLM_PROVIDER=openai
      - MODEL_NAME=gpt-3.5-turbo
      - LLM_API_KEY=\${LLM_API_KEY}
    depends_on: []
EOF

# Start with OpenAI
export LLM_API_KEY="your-openai-api-key"
sudo docker-compose -f docker-compose.yml -f docker-compose.openai.yml up -d
```

#### Option 3: Use Local Ollama (if you have sufficient memory)
```bash
# Stop demo mode
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml down

# Start with local Ollama
sudo docker-compose up -d
```

## System Requirements

### Demo Mode (Minimal)
- **RAM**: 2GB minimum (all services run with mock/lightweight models)
- **CPU**: 2 cores minimum
- **Storage**: 5GB for Docker images
- **Network**: Internet connection for Docker image downloads
- **Ports**: 8000-8004 must be available

### Production Mode
- **Local Ollama**: 8GB+ RAM (depending on model size)
- **Remote APIs**: 2GB RAM + API keys
- **Full System**: 16GB+ RAM recommended

## Troubleshooting

### Port Conflicts
If ports 8000-8004 are in use, you can modify the port mappings. Create a custom override file:

```yaml
# docker-compose.ports.yml
version: '3.9'
services:
  api:
    ports:
      - "9000:8000"  # Change external port to 9000
  asr:
    ports:
      - "9001:8001"  # Change external port to 9001
  llm:
    ports:
      - "9002:8002"  # Change external port to 9002
  tts:
    ports:
      - "9003:8003"  # Change external port to 9003
  sardaukar-translator:
    ports:
      - "9004:8000"  # Change external port to 9004
```

Then start with:
```bash
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml -f docker-compose.ports.yml up -d
```

### Services Not Starting
```bash
# Check logs
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml logs

# Check specific service
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml logs llm

# Restart specific service
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml restart llm
```

### Memory Issues
Demo mode is designed for low-memory systems, but if you still encounter issues:

```bash
# Check system resources
free -h
docker stats

# Check which ports are in use
netstat -tulpn | grep :800
```

## Development

### Adding Custom Demo Responses

Edit `llm/main.py` and modify the `generate_with_demo()` function to add custom response patterns:

```python
# Add custom patterns in the generate_with_demo function
elif 'your_pattern' in prompt_lower:
    response_text = "Your custom response here"
```

### Testing Changes

```bash
# Rebuild and restart LLM service
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml build llm
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml restart llm
```

### Checking Service Status

```bash
# View all container status
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml ps

# Follow logs in real-time
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml logs -f

# Check resource usage
docker stats
```

## Next Steps

1. **Explore the API**: Try different queries and endpoints using the correct ports
2. **Check Logs**: Monitor service behavior with `docker-compose logs`
3. **Scale Up**: When ready, switch to a production LLM provider
4. **Customize**: Modify the demo responses or add new features
5. **Monitor**: Use the health endpoints to monitor system status

The demo mode provides a complete, working Agent CAG system that showcases all the architectural components and their interactions without external dependencies.