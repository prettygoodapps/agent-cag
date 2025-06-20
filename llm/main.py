"""
LLM (Large Language Model) Service

Provides text generation capabilities using local LLM models or remote APIs.
Supports Ollama (local), OpenAI, Groq, and other OpenAI-compatible APIs.
"""

import os
import logging
import socket
import subprocess
from typing import Dict, Any, Optional
from enum import Enum

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import start_http_server
import ollama
import openai
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter("llm_requests_total", "Total LLM requests")
REQUEST_DURATION = Histogram("llm_request_duration_seconds", "LLM request duration")
GENERATION_COUNT = Counter("generations_total", "Total text generations")
TOKEN_COUNT = Counter("tokens_generated_total", "Total tokens generated")
ERROR_COUNT = Counter("llm_errors_total", "Total LLM errors", ["error_type"])

# Global configuration
MODEL_NAME = None
LLM_PROVIDER = None
OLLAMA_CLIENT = None
OPENAI_CLIENT = None


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"
    GROQ = "groq"
    ANTHROPIC = "anthropic"
    GENERIC_OPENAI = "generic_openai"
    DEMO = "demo"


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
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Parse the output to get the gateway IP
            for line in result.stdout.strip().split("\n"):
                if "default" in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        gateway_ip = parts[2]
                        logger.info(f"Discovered host gateway IP: {gateway_ip}")
                        return gateway_ip

        # Fallback: try to resolve host.docker.internal
        try:
            gateway_ip = socket.gethostbyname("host.docker.internal")
            logger.info(f"Resolved host.docker.internal to: {gateway_ip}")
            return gateway_ip
        except socket.gaierror:
            pass

        # Final fallback for common Docker gateway
        logger.warning(
            "Could not discover gateway IP, using common Docker gateway: 172.18.0.1"
        )
        return "172.18.0.1"

    except Exception as e:
        logger.warning(f"Error discovering gateway IP: {e}, using fallback: 172.18.0.1")
        return "172.18.0.1"


def initialize_llm():
    """Initialize the LLM model."""
    global MODEL_NAME, LLM_PROVIDER, OLLAMA_CLIENT, OPENAI_CLIENT

    MODEL_NAME = os.getenv("MODEL_NAME", "llama3")
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()
    
    logger.info(f"Initializing LLM service with provider: {LLM_PROVIDER}")
    logger.info(f"Model: {MODEL_NAME}")

    if LLM_PROVIDER == LLMProvider.OLLAMA:
        initialize_ollama()
    elif LLM_PROVIDER in [LLMProvider.OPENAI, LLMProvider.GROQ, LLMProvider.ANTHROPIC, LLMProvider.GENERIC_OPENAI]:
        initialize_openai_compatible()
    elif LLM_PROVIDER == LLMProvider.DEMO:
        logger.info("Demo mode enabled - no external API required")
    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

    logger.info("LLM service initialized successfully")


def initialize_ollama():
    """Initialize Ollama client."""
    global OLLAMA_CLIENT
    
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODE = os.getenv("OLLAMA_MODE", "container")

    # For local mode, dynamically detect the host gateway IP
    if OLLAMA_MODE == "local":
        gateway_ip = get_host_gateway_ip()
        OLLAMA_HOST = f"http://{gateway_ip}:11434"
        logger.info(f"Local mode detected, using dynamic host: {OLLAMA_HOST}")

    logger.info(f"Ollama host: {OLLAMA_HOST} (mode: {OLLAMA_MODE})")

    try:
        # Initialize Ollama client with custom host
        OLLAMA_CLIENT = ollama.Client(host=OLLAMA_HOST)

        # Check if model is available
        try:
            models = OLLAMA_CLIENT.list()
            available_models = [model["name"] for model in models["models"]]

            if MODEL_NAME not in available_models:
                logger.warning(
                    f"Model {MODEL_NAME} not found. Available models: {available_models}"
                )
                # Try to pull the model
                logger.info(f"Attempting to pull model: {MODEL_NAME}")
                OLLAMA_CLIENT.pull(MODEL_NAME)
                logger.info(f"Successfully pulled model: {MODEL_NAME}")

        except Exception as e:
            logger.warning(f"Could not check/pull model: {e}")

    except Exception as e:
        logger.error(f"Failed to initialize Ollama: {e}")
        raise


def initialize_openai_compatible():
    """Initialize OpenAI-compatible client."""
    global OPENAI_CLIENT, MODEL_NAME
    
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY environment variable is required for remote APIs")
    
    base_url = None
    
    # Set provider-specific configurations
    if LLM_PROVIDER == LLMProvider.OPENAI:
        base_url = "https://api.openai.com/v1"
        if not MODEL_NAME or MODEL_NAME == "llama3":
            MODEL_NAME = "gpt-3.5-turbo"
    elif LLM_PROVIDER == LLMProvider.GROQ:
        base_url = "https://api.groq.com/openai/v1"
        if not MODEL_NAME or MODEL_NAME in ["llama3", "phi3:mini"]:
            MODEL_NAME = "llama3-8b-8192"  # Free Groq model
    elif LLM_PROVIDER == LLMProvider.GENERIC_OPENAI:
        base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    
    logger.info(f"Using API endpoint: {base_url}")
    logger.info(f"Model: {MODEL_NAME}")
    
    OPENAI_CLIENT = openai.OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    # Test the connection
    try:
        # Try to list models or make a simple request
        logger.info("Testing API connection...")
        # This will raise an exception if the API key is invalid
        models = OPENAI_CLIENT.models.list()
        logger.info("API connection successful")
    except Exception as e:
        logger.warning(f"Could not test API connection: {e}")


# Initialize FastAPI app
app = FastAPI(
    title="Agent CAG LLM Service",
    description="Large Language Model text generation service",
    version="1.0.0",
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
        if LLM_PROVIDER == LLMProvider.OLLAMA:
            if OLLAMA_CLIENT is None:
                raise Exception("Ollama client not initialized")
            
            # Test connection to Ollama
            models = OLLAMA_CLIENT.list()
            available_models = [model["name"] for model in models["models"]]
        elif LLM_PROVIDER == LLMProvider.DEMO:
            # Demo mode - always healthy
            available_models = ["demo-model"]
        else:
            if OPENAI_CLIENT is None:
                raise Exception("OpenAI client not initialized")
            
            # For API providers, we assume the model is available
            available_models = [MODEL_NAME]

        return {
            "status": "healthy",
            "service": "agent-llm",
            "provider": LLM_PROVIDER,
            "model": MODEL_NAME,
            "available_models": available_models,
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
            if LLM_PROVIDER == LLMProvider.OLLAMA:
                response = await generate_with_ollama(
                    prompt=request.text,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    system_prompt=request.system_prompt,
                )
            elif LLM_PROVIDER == LLMProvider.DEMO:
                response = await generate_with_demo(
                    prompt=request.text,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    system_prompt=request.system_prompt,
                )
            else:
                response = await generate_with_openai_compatible(
                    prompt=request.text,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    top_p=request.top_p,
                    system_prompt=request.system_prompt,
                )

            GENERATION_COUNT.inc()
            TOKEN_COUNT.inc(response["tokens_used"])

            return GenerationResponse(
                text=response["text"],
                tokens_used=response["tokens_used"],
                model=MODEL_NAME,
                metadata=response.get("metadata", {}),
            )

    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Text generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def generate_with_ollama(
    prompt: str, max_tokens: int = 1000, temperature: float = 0.7, 
    top_p: float = 0.9, system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Generate text using Ollama."""
    try:
        if OLLAMA_CLIENT is None:
            raise Exception("Ollama client not initialized")

        # Prepare the prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        else:
            full_prompt = prompt

        # Generate response
        response = OLLAMA_CLIENT.generate(
            model=MODEL_NAME,
            prompt=full_prompt,
            options={
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stop": ["User:", "Human:", "\n\n"],
            },
        )

        generated_text = response["response"].strip()

        # Estimate token count (rough approximation)
        tokens_used = len(generated_text.split()) * 1.3  # Rough token estimation

        return {
            "text": generated_text,
            "tokens_used": int(tokens_used),
            "metadata": {
                "provider": "ollama",
                "model": MODEL_NAME,
                "done": response.get("done", True),
                "total_duration": response.get("total_duration", 0),
                "load_duration": response.get("load_duration", 0),
                "prompt_eval_count": response.get("prompt_eval_count", 0),
                "eval_count": response.get("eval_count", 0),
            },
        }

    except Exception as e:
        logger.error(f"Ollama generation failed: {e}")
        # Fallback to a simple response
        return {
            "text": "I apologize, but I'm currently unable to process your request. The language model service is experiencing issues.",
            "tokens_used": 20,
            "metadata": {"error": str(e), "fallback": True, "provider": "ollama"},
        }


async def generate_with_demo(
    prompt: str, max_tokens: int = 1000, temperature: float = 0.7,
    top_p: float = 0.9, system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Generate text using demo mode (no external API required)."""
    import re
    import random
    
    # Simple rule-based responses for demo purposes
    prompt_lower = prompt.lower()
    
    # Math questions
    math_pattern = r'(\d+)\s*[\+\-\*\/]\s*(\d+)'
    math_match = re.search(math_pattern, prompt)
    if math_match or any(word in prompt_lower for word in ['calculate', 'math', 'add', 'subtract', 'multiply', 'divide']):
        if '2+2' in prompt or '2 + 2' in prompt:
            response_text = "2 + 2 = 4. This is a basic arithmetic operation where we add two numbers together."
        elif math_match:
            try:
                # Simple calculator for demo
                expr = math_match.group(0)
                result = eval(expr)  # Safe for demo with simple expressions
                response_text = f"The answer to {expr} is {result}."
            except:
                response_text = "I can help with basic math operations. Could you please rephrase your question?"
        else:
            response_text = "I can help with basic math operations like addition, subtraction, multiplication, and division."
    
    # Greeting responses
    elif any(word in prompt_lower for word in ['hello', 'hi', 'hey', 'greetings']):
        greetings = [
            "Hello! I'm a demo AI assistant. How can I help you today?",
            "Hi there! I'm running in demo mode. What would you like to know?",
            "Greetings! I'm here to help with your questions in demo mode."
        ]
        response_text = random.choice(greetings)
    
    # Help/about responses
    elif any(word in prompt_lower for word in ['help', 'what can you do', 'about', 'who are you']):
        response_text = ("I'm a demo AI assistant running in Agent CAG. I can help with basic questions, "
                        "simple math, and provide information. This is a demonstration mode that doesn't "
                        "require external API keys.")
    
    # Weather (mock response)
    elif any(word in prompt_lower for word in ['weather', 'temperature', 'forecast']):
        response_text = ("I'm in demo mode and don't have access to real weather data. "
                        "For actual weather information, you'd need to configure a real LLM provider.")
    
    # Programming questions
    elif any(word in prompt_lower for word in ['code', 'programming', 'python', 'javascript', 'function']):
        response_text = ("I can discuss programming concepts in demo mode. For detailed code assistance, "
                        "consider using a full LLM provider like OpenAI or Groq.")
    
    # Default response
    else:
        responses = [
            f"Thank you for your question: '{prompt}'. I'm running in demo mode, so my responses are limited.",
            f"I understand you're asking about '{prompt}'. In demo mode, I provide basic responses.",
            f"Your question '{prompt}' is interesting. This is a demo response to show the system is working.",
        ]
        response_text = random.choice(responses)
    
    # Add some variation based on temperature
    if temperature > 0.8:
        response_text += " (High creativity mode enabled!)"
    elif temperature < 0.3:
        response_text += " (Focused response mode.)"
    
    # Estimate token count
    tokens_used = len(response_text.split()) + len(prompt.split())
    
    return {
        "text": response_text,
        "tokens_used": tokens_used,
        "metadata": {
            "provider": "demo",
            "model": "demo-model",
            "temperature": temperature,
            "top_p": top_p,
            "demo_mode": True,
            "prompt_length": len(prompt),
            "response_length": len(response_text),
        },
    }


async def generate_with_openai_compatible(
    prompt: str, max_tokens: int = 1000, temperature: float = 0.7,
    top_p: float = 0.9, system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Generate text using OpenAI-compatible API."""
    try:
        if OPENAI_CLIENT is None:
            raise Exception("OpenAI client not initialized")

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({"role": "system", "content": "You are a helpful AI assistant."})
        
        messages.append({"role": "user", "content": prompt})

        # Generate response
        response = OPENAI_CLIENT.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
        )

        generated_text = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens if response.usage else len(generated_text.split()) * 1.3

        return {
            "text": generated_text,
            "tokens_used": int(tokens_used),
            "metadata": {
                "provider": LLM_PROVIDER,
                "model": MODEL_NAME,
                "finish_reason": response.choices[0].finish_reason,
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens if response.usage else 0,
            },
        }

    except Exception as e:
        logger.error(f"OpenAI-compatible generation failed: {e}")
        # Fallback to a simple response
        return {
            "text": "I apologize, but I'm currently unable to process your request. The language model service is experiencing issues.",
            "tokens_used": 20,
            "metadata": {"error": str(e), "fallback": True, "provider": LLM_PROVIDER},
        }


@app.get("/models")
async def list_models():
    """List available models."""
    try:
        if LLM_PROVIDER == LLMProvider.OLLAMA:
            if OLLAMA_CLIENT is None:
                raise Exception("Ollama client not initialized")
            
            models = OLLAMA_CLIENT.list()
            return {"models": models["models"], "current_model": MODEL_NAME, "provider": LLM_PROVIDER}
        elif LLM_PROVIDER == LLMProvider.DEMO:
            # Demo mode - return demo model info
            return {
                "models": [{"name": "demo-model", "size": "0B", "digest": "demo", "modified_at": "2024-01-01T00:00:00Z"}],
                "current_model": "demo-model",
                "provider": LLM_PROVIDER
            }
        else:
            # For API providers, return the current model
            return {
                "models": [{"name": MODEL_NAME}],
                "current_model": MODEL_NAME,
                "provider": LLM_PROVIDER
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
            system_prompt=system_prompt,
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

    return {"detail": "Internal server error"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True, log_level="info")
