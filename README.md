# Agent CAG - Context-Aware Graph AI Agent

A sophisticated local AI agent system with Context-Aware Graph capabilities, featuring modular microservices architecture, multi-modal input/output, and persistent memory. The system supports both local and cloud-based LLM providers with a comprehensive demo mode for testing and development.

---

## 🚀 Features

### Core Capabilities
- **Multi-modal Input**: Text queries and voice input via Whisper ASR
- **Intelligent Processing**: Local or cloud-based LLM integration (Ollama, OpenAI, Groq)
- **Speech Synthesis**: High-quality text-to-speech with Piper TTS
- **Persistent Memory**: DuckDB-based storage with vector embeddings
- **Context-Aware Graph**: Semantic relationship tracking and knowledge retention
- **Sardaukar Translation**: Fictional language translation integration

### System Features
- **Demo Mode**: Complete system testing without external dependencies
- **Monitoring**: Prometheus metrics and health checks
- **Containerized**: Full Docker Compose orchestration
- **Scalable**: Modular microservices architecture
- **API-First**: RESTful APIs for all services

---

## 🏗️ Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Web UI    │    │  Voice UI   │    │  CLI Tools  │
│  (Future)   │    │    (ASR)    │    │ (External)  │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       └──────────────────┼──────────────────┘
                          ▼
              ┌─────────────────────┐
              │    API Gateway      │ :8000
              │   (FastAPI + DB)    │
              └──────────┬──────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ ASR Service │  │ LLM Service │  │ TTS Service │
│  (Whisper)  │  │(Ollama/API) │  │   (Piper)   │
│    :8001    │  │    :8002    │  │    :8003    │
└─────────────┘  └─────────────┘  └──────┬──────┘
                         │               │
                         ▼               ▼
                ┌─────────────┐  ┌─────────────┐
                │   Ollama    │  │ Sardaukar   │
                │  (Local)    │  │ Translator  │
                │   :11434    │  │    :8004    │
                └─────────────┘  └─────────────┘
```

---

## 🛠️ Core Components

| Service | Technology | Port | Description |
|---------|------------|------|-------------|
| **API Gateway** | FastAPI + DuckDB | 8000 | Main orchestration and data persistence |
| **ASR Service** | OpenAI Whisper | 8001 | Speech-to-text conversion |
| **LLM Service** | Ollama/OpenAI/Groq | 8002 | Language model processing |
| **TTS Service** | Piper TTS | 8003 | Text-to-speech synthesis |
| **Translation** | Sardaukar | 8004 | Fictional language translation |
| **Ollama** | Ollama Server | 11434 | Local LLM backend (optional) |

### Supported LLM Providers
- **Local**: Ollama (Phi3, LLaMA, Mistral models)
- **Cloud**: OpenAI GPT models, Groq (free tier)
- **Demo**: Built-in mock responses for testing

---

## 📁 Project Structure

```bash
agent-cag/
├── docker-compose.yml           # Main service definitions
├── docker-compose.demo.yml      # Demo mode overrides
├── docker-compose.remote-llm.yml # Cloud LLM configuration
├── api/                         # FastAPI gateway service
│   ├── main.py                  # Main API application
│   ├── database.py              # DuckDB integration
│   └── models.py                # Pydantic models
├── llm/                         # LLM service
│   └── main.py                  # LLM provider abstraction
├── asr/                         # Whisper ASR service
├── tts/                         # Piper TTS service
├── tests/                       # Comprehensive test suite
├── monitoring/                  # Prometheus monitoring
└── DEMO_MODE_SETUP.md          # Demo mode documentation
```

---

## Context-Aware Graph (CAG)

Each interaction is decomposed into a knowledge graph capturing semantic relationships between actors, queries, responses, and underlying intent.

### Node Types

- `Operator`: The human user issuing prompts
- `Query`: Normalized textual input from Operator
- `Response`: Textual output from the LLM
- `Entity`: Concepts or objects mentioned
- `Intent`: Inferred purpose or function of the query

### Example Relationships

- `(Operator)-[:ASKED]->(Query)`
- `(Response)-[:ANSWERS]->(Query)`
- `(Response)-[:MENTIONS]->(Entity)`
- `(Query)-[:HAS_INTENT]->(Intent)`

Embeddings may be stored as node properties for hybrid semantic‑graph retrieval.

---

## File Structure

```bash
agent/
├── docker-compose.yml
├── api/                 # FastAPI gateway
│   └── app.py
├── llm/                 # Local LLM service
├── asr/                 # Whisper service
├── tts/                 # Piper service
├── vector_db/           # Chroma volumes
├── graph_db/            # Neo4j/TerminusDB volumes
├── orchestration/       # LangChain pipelines
```

---

## 🚀 Quick Start

### Prerequisites
- **Docker & Docker Compose** (required)
- **2GB+ RAM** for demo mode, 8GB+ for local LLM
- **Linux/macOS/Windows** with Docker support
- **Ports 8000-8004** available

### Option 1: Demo Mode (Recommended for Testing)
Perfect for testing without external dependencies or high memory requirements:

```bash
git clone https://github.com/prettygoodapps/agent-cag
cd agent-cag

# Start in demo mode
sudo docker-compose -f docker-compose.yml -f docker-compose.demo.yml up -d

# Test the system
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, what can you do?", "user_id": "demo-user"}'
```

### Option 2: Cloud LLM (Production Ready)
Using Groq (free) or OpenAI API:

```bash
# Set your API key
export LLM_API_KEY="your-groq-or-openai-key"

# Start with cloud LLM
sudo docker-compose -f docker-compose.yml -f docker-compose.remote-llm.yml up -d
```

### Option 3: Local LLM (High Memory)
For completely local operation:

```bash
# Requires 8GB+ RAM
sudo docker-compose up -d

# Wait for Ollama to download models (first run)
docker-compose logs -f ollama
```

---

## 📖 Usage

### API Endpoints

**Main API (Port 8000)**
```bash
# Process text query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Explain quantum computing",
    "user_id": "user123",
    "generate_speech": true,
    "use_sardaukar": false
  }'

# Get conversation history
curl "http://localhost:8000/history/user123"

# Search knowledge base
curl "http://localhost:8000/search?query=quantum&limit=5"

# Health check
curl "http://localhost:8000/health"
```

**Direct Service Access**
```bash
# LLM Service (Port 8002)
curl -X POST "http://localhost:8002/generate" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is AI?", "temperature": 0.7}'

# TTS Service (Port 8003)
curl -X POST "http://localhost:8003/synthesize" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "use_sardaukar": false}'

# ASR Service (Port 8001) - requires audio file
curl -X POST "http://localhost:8001/transcribe" \
  -H "Content-Type: audio/wav" \
  --data-binary @audio.wav
```

### Speech Tools
The system includes command-line speech tools (moved to separate repository):
- **Bash Script**: Quick speech generation
- **Python CLI**: Advanced options with Sardaukar translation

---

## 🔧 Configuration

### Environment Variables
```bash
# LLM Configuration
LLM_PROVIDER=ollama|openai|groq|demo
LLM_API_KEY=your-api-key
MODEL_NAME=phi3:mini|gpt-3.5-turbo|llama3-8b-8192

# Service URLs (auto-configured in Docker)
ASR_SERVICE_URL=http://asr:8001
LLM_SERVICE_URL=http://llm:8002
TTS_SERVICE_URL=http://tts:8003
SARDAUKAR_TRANSLATOR_URL=http://sardaukar-translator:8000

# Features
SARDAUKAR_ENABLED=true|false
METRICS_ENABLED=true|false
DEPLOYMENT_PROFILE=lightweight|full
```

### Docker Compose Files
- **`docker-compose.yml`**: Base configuration
- **`docker-compose.demo.yml`**: Demo mode overrides
- **`docker-compose.remote-llm.yml`**: Cloud LLM configuration
- **`docker-compose.local.yml`**: Local development
- **`docker-compose.monitoring.yml`**: Prometheus monitoring

---

## 🧪 Testing & Development

### Run Tests
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run all tests
python run_tests.py

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/security/
```

### Monitor System
```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f

# Monitor resources
docker stats

# Health checks
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

---

## 🗺️ Roadmap

### Current Features ✅
- Multi-modal input/output (text, voice)
- Multiple LLM provider support
- Persistent conversation memory
- Sardaukar fictional language translation
- Comprehensive monitoring and testing
- Demo mode for easy testing

### Planned Features 🚧
- **Web UI**: Real-time chat interface with voice controls
- **Plugin System**: Tool use and code execution capabilities
- **Advanced RAG**: Vector similarity search and context retrieval
- **Fine-tuning**: LoRA adaptation from conversation history
- **Graph Visualization**: Interactive knowledge graph explorer
- **Mobile App**: iOS/Android companion apps

---

## 📄 License

This project is released under the **MIT License**.

### Third-Party Licenses
- **OpenAI Whisper**: MIT License
- **Piper TTS**: MIT License
- **Ollama**: MIT License
- **Model Weights**: Subject to respective model licenses
  - Phi3: MIT License
  - LLaMA models: Meta License
  - Mistral models: Apache 2.0

---

## 🙏 Acknowledgments

- **OpenAI**: Whisper ASR model
- **Microsoft**: Phi3 language model
- **Meta AI**: LLaMA model family
- **Mistral AI**: Mistral model family
- **Rhasspy Project**: Piper TTS engine
- **Ollama Team**: Local LLM serving platform
- **FastAPI**: Modern Python web framework

---

## 🎯 Design Philosophy

Agent CAG is built on the principle that **"everything is text"** - all human-computer interactions can be captured, structured, and leveraged to create long-lived, self-improving AI systems. The Context-Aware Graph enables persistent memory and relationship understanding across conversations.

### Key Principles
- **Modularity**: Each service is independent and replaceable
- **Flexibility**: Support for multiple LLM providers and deployment modes
- **Persistence**: All interactions contribute to long-term knowledge
- **Privacy**: Local-first design with optional cloud integration
- **Extensibility**: Plugin architecture for future capabilities

---

## 📚 Documentation

- **[Demo Mode Setup](DEMO_MODE_SETUP.md)**: Complete demo mode guide
- **[Testing Guide](TESTING.md)**: Comprehensive testing documentation
- **[Build Documentation](README_BUILD.md)**: Development and build instructions
- **[Speech Tools](../agent-cag-speech-tools/)**: Command-line speech utilities

---

*Last updated: December 2024 - Complete system with demo mode, cloud LLM support, and comprehensive testing*
