"""
LLM (Large Language Model) Service

Provides text generation capabilities using local LLM models.
"""

import os
import logging
import socket
import subprocess
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import start_http_server
import ollama

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('llm_requests_total', 'Total LLM requests')
REQUEST_DURATION = Histogram('llm_request_duration_seconds', 'LLM request duration')
GENERATION_COUNT = Counter('generations_total', 'Total text generations')
TOKEN_COUNT = Counter('tokens_generated_total', 'Total tokens generated')
ERROR_COUNT = Counter('llm_errors_total', 'Total LLM errors', ['error_type'])

# Global configuration
MODEL_NAME = None
OLLAMA_CLIENT = None


class GenerationRequest(BaseModel):
    """Request model for text generation."""
    text: str
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: Optional[str] = None


class GenerationResponse(BaseModel):
    """Response model for text generation."""
    text: str
    tokens_used: int
    model: str
    metadata: Dict[str, Any]


def get_host_gateway_ip():
    """Dynamically discover the host gateway IP."""
    try:
        # Try to get the default gateway IP from the container
        result = subprocess.run(['ip', 'route', 'show', 'default'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Parse the output to get the gateway IP
            for line in result.stdout.strip().split('\n'):
                if 'default' in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        gateway_ip = parts[2]
                        logger.info(f"Discovered host gateway IP: {gateway_ip}")
                        return gateway_ip
        
        # Fallback: try to resolve host.docker.internal
        try:
            gateway_ip = socket.gethostbyname('host.docker.internal')
            logger.info(f"Resolved host.docker.internal to: {gateway_ip}")
            return gateway_ip
        except socket.gaierror:
            pass
        
        # Final fallback for common Docker gateway
        logger.warning("Could not discover gateway IP, using common Docker gateway: 172.18.0.1")
        return "172.18.0.1"
        
    except Exception as e:
        logger.warning(f"Error discovering gateway IP: {e}, using fallback: 172.18.0.1")
        return "172.18.0.1"


def initialize_llm():
    """Initialize the LLM model."""
    global MODEL_NAME, OLLAMA_CLIENT
    
    MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODE = os.getenv("OLLAMA_MODE", "container")
    
    # For local mode, dynamically detect the host gateway IP
    if OLLAMA_MODE == "local":
        gateway_ip = get_host_gateway_ip()
        OLLAMA_HOST = f"http://{gateway_ip}:11434"
        logger.info(f"Local mode detected, using dynamic host: {OLLAMA_HOST}")
    
    logger.info(f"Initializing LLM service with model: {MODEL_NAME}")
    logger.info(f"Ollama host: {OLLAMA_HOST} (mode: {OLLAMA_MODE})")
    
    try:
        # Initialize Ollama client with custom host
        OLLAMA_CLIENT = ollama.Client(host=OLLAMA_HOST)
        
        # Check if model is available
        try:
            models = OLLAMA_CLIENT.list()
            available_models = [model['name'] for model in models['models']]
            
            if MODEL_NAME not in available_models:
                logger.warning(f"Model {MODEL_NAME} not found. Available models: {available_models}")
                # Try to pull the model
                logger.info(f"Attempting to pull model: {MODEL_NAME}")
                OLLAMA_CLIENT.pull(MODEL_NAME)
                logger.info(f"Successfully pulled model: {MODEL_NAME}")
                
        except Exception as e:
            logger.warning(f"Could not check/pull model: {e}")
        
        logger.info("LLM service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize LLM service: {e}")
        raise


# Initialize FastAPI app
app = FastAPI(
    title="Agent CAG LLM Service",
    description="Large Language Model text generation service",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    logger.info("Starting LLM Service...")
    
    # Initialize LLM
    initialize_llm()
    
    # Start Prometheus metrics server if enabled
    if os.getenv("METRICS_ENABLED", "false").lower() == "true":
        start_http_server(8082)
        logger.info("Prometheus metrics server started on port 8082")
    
    logger.info("LLM Service started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if OLLAMA_CLIENT is None:
            raise Exception("Ollama client not initialized")
        
        # Test connection to Ollama
        models = OLLAMA_CLIENT.list()
        
        return {
            "status": "healthy",
            "service": "agent-llm",
            "model": MODEL_NAME,
            "available_models": [model['name'] for model in models['models']]
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest):
    """Generate text using the LLM."""
    try:
        REQUEST_COUNT.inc()
        
        with REQUEST_DURATION.time():
            # Prepare the prompt
            if request.system_prompt:
                full_prompt = f"System: {request.system_prompt}\n\nUser: {request.text}\n\nAssistant:"
            else:
                full_prompt = request.text
            
            # Generate response using Ollama
            response = await generate_with_ollama(
                prompt=full_prompt,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p
            )
            
            GENERATION_COUNT.inc()
            TOKEN_COUNT.inc(response["tokens_used"])
            
            return GenerationResponse(
                text=response["text"],
                tokens_used=response["tokens_used"],
                model=MODEL_NAME,
                metadata=response.get("metadata", {})
            )
            
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Text generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_with_ollama(
    prompt: str,
    max_tokens: int = 1000,
    temperature: float = 0.7,
    top_p: float = 0.9
) -> Dict[str, Any]:
    """Generate text using Ollama."""
    try:
        if OLLAMA_CLIENT is None:
            raise Exception("Ollama client not initialized")
        
        # Generate response
        response = OLLAMA_CLIENT.generate(
            model=MODEL_NAME,
            prompt=prompt,
            options={
                'num_predict': max_tokens,
                'temperature': temperature,
                'top_p': top_p,
                'stop': ['User:', 'Human:', '\n\n']
            }
        )
        
        generated_text = response['response'].strip()
        
        # Estimate token count (rough approximation)
        tokens_used = len(generated_text.split()) * 1.3  # Rough token estimation
        
        return {
            "text": generated_text,
            "tokens_used": int(tokens_used),
            "metadata": {
                "model": MODEL_NAME,
                "done": response.get('done', True),
                "total_duration": response.get('total_duration', 0),
                "load_duration": response.get('load_duration', 0),
                "prompt_eval_count": response.get('prompt_eval_count', 0),
                "eval_count": response.get('eval_count', 0)
            }
        }
        
    except Exception as e:
        logger.error(f"Ollama generation failed: {e}")
        # Fallback to a simple response
        return {
            "text": "I apologize, but I'm currently unable to process your request. The language model service is experiencing issues.",
            "tokens_used": 20,
            "metadata": {"error": str(e), "fallback": True}
        }


@app.get("/models")
async def list_models():
    """List available models."""
    try:
        if OLLAMA_CLIENT is None:
            raise Exception("Ollama client not initialized")
        
        models = OLLAMA_CLIENT.list()
        return {
            "models": models['models'],
            "current_model": MODEL_NAME
        }
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat_completion(request: GenerationRequest):
    """Chat completion endpoint (alternative interface)."""
    try:
        # Use the same generation logic but with chat formatting
        system_prompt = request.system_prompt or "You are a helpful AI assistant."
        
        chat_request = GenerationRequest(
            text=request.text,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            system_prompt=system_prompt
        )
        
        return await generate_text(chat_request)
        
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    ERROR_COUNT.labels(error_type=type(exc).__name__).inc()
    logger.error(f"Unhandled exception: {exc}")
    
    return {
        "detail": "Internal server error"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=True,
        log_level="info"
    )