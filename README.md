# Local AI Agent with Context-Aware Graph (CAG)

This project defines a modular, fully local AI agent capable of accepting natural language queries through keyboard or voice, processing them using a local LLM pipeline, and recording the semantic content of each interaction in a **Context-Aware Graph (CAG)**. The system is optimized for long-term interaction and memory retention under the philosophy that **"everything is text."**

---

## Features

- Dual input support (keyboard and microphone)
- Embedded local large language model (LLM) for reasoning
- Persistent memory via hybrid vector and graph databases
- Text-to-speech output for spoken responses
- Context-Aware Graph for structured knowledge retention
- Modular, containerized architecture using Docker Compose

---

## Architecture Overview

```
┌────────────┐       ┌───────────┐
│ Keyboard    │       │  Mic/ASR │ (Whisper)
└──────┬─────┘       └──────┬────┘
       ▼                   ▼
              (text-normalized input)
                         ▼
              ┌────────────────────┐
              │   Query Router     │
              └────────┬───────────┘
                       ▼
      ┌────────────────────────────────────┐
      │  Retrieval-Augmented Generation    │
      └────────┬───────────────────────────┘
               ▼
      ┌───────────────────────┐
      │     Post-processor    │
      └────────┬──────────────┘
               ▼
         Voice? ──► (Piper TTS)
               ▼
        Return to Operator
```

---

## Core Components

| Component     | Technology                                    | Description                              |
|---------------|-----------------------------------------------|------------------------------------------|
| LLM           | LLaMA 3 (Meta) or Mixtral (Mistral)           | Local instruction‑tuned language models  |
| ASR           | [Whisper](https://github.com/openai/whisper)  | Converts speech to text                  |
| TTS           | [Piper](https://github.com/rhasspy/piper)     | Converts text to voice                   |
| Vector DB     | [ChromaDB](https://www.trychroma.com/)        | Embedding search for contextual recall   |
| Graph DB      | [Neo4j](https://neo4j.com/) or TerminusDB     | Semantic memory and relationship storage |
| Orchestration | LangChain or FastAPI                          | Pipeline and agent workflow management   |

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

## Getting Started

### Prerequisites

- Linux‑based host system (recommended)
- CUDA‑compatible GPU or high‑performance CPU
- Docker and Docker Compose
- Python 3.10 or higher

### Installation

```bash
git clone https://github.com/prettygoodapps/agent-cag
cd agent-cag
docker-compose up --build
```

---

## Usage

Once running, the system supports:

- Text input via terminal or web UI (in development)
- Voice input via microphone using Whisper
- Spoken output using Piper
- Automatic population of the CAG with semantic relationships
- Persistent embedding and graph-based storage for recall

---

## Roadmap

- Web front-end with real-time streaming and voice control
- Agent plugin system for tool use and code execution
- LoRA fine‑tuning from historical conversations
- Context‑aware summarization and graph visualization

---

## License

This project is released under the MIT License.  
Model weights are subject to their respective licenses:

- Meta LLaMA 3 – LLaMA License
- Mistral Mixtral – Apache 2.0
- OpenAI Whisper – MIT
- Piper TTS – MIT

---

## Acknowledgments

- Meta AI – LLaMA 3
- Mistral AI – Mixtral
- OpenAI – Whisper
- Rhasspy Project – Piper TTS
- LangChain, Neo4j, ChromaDB

---

## Design Philosophy

This system is founded on the principle that **all human‑computer interaction can be captured as structured text**, enabling the development of long‑lived, self‑improving AI systems.

*Last updated: June 2025 - Git hook test*
