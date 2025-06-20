"""
Agent CAG API Service

Main FastAPI application that serves as the orchestration layer for the
Context-Aware Graph AI agent system.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client import start_http_server

from database import DatabaseManager
from models import QueryRequest, QueryResponse, HealthResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration')
QUERY_COUNT = Counter('queries_total', 'Total queries processed')
ERROR_COUNT = Counter('errors_total', 'Total errors', ['error_type'])

# Global database manager
db_manager: Optional[DatabaseManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global db_manager
    
    # Startup
    logger.info("Starting Agent CAG API Service...")
    
    # Initialize database manager
    deployment_profile = os.getenv("DEPLOYMENT_PROFILE", "lightweight")
    db_manager = DatabaseManager(deployment_profile)
    await db_manager.initialize()
    
    # Start Prometheus metrics server if enabled
    if os.getenv("METRICS_ENABLED", "false").lower() == "true":
        start_http_server(8080)
        logger.info("Prometheus metrics server started on port 8080")
    
    logger.info(f"API Service started with {deployment_profile} profile")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent CAG API Service...")
    if db_manager:
        await db_manager.close()


# Initialize FastAPI app
app = FastAPI(
    title="Agent CAG API",
    description="Context-Aware Graph AI Agent API",
    version="1.0.0",
    lifespan=lifespan
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect metrics."""
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    
    with REQUEST_DURATION.time():
        response = await call_next(request)
    
    return response


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        if db_manager:
            await db_manager.health_check()
        
        return HealthResponse(
            status="healthy",
            service="agent-api",
            profile=os.getenv("DEPLOYMENT_PROFILE", "lightweight"),
            version="1.0.0"
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a user query through the AI pipeline."""
    try:
        QUERY_COUNT.inc()
        logger.info(f"Processing query: {request.text[:100]}...")
        
        # Store the query in the graph
        query_id = await db_manager.store_query(
            text=request.text,
            user_id=request.user_id or "anonymous",
            input_type=request.input_type
        )
        
        # Process through LLM service
        llm_response = await call_llm_service(request.text)
        
        # Store the response
        response_id = await db_manager.store_response(
            query_id=query_id,
            text=llm_response["text"],
            metadata=llm_response.get("metadata", {})
        )
        
        # Generate speech if requested
        audio_url = None
        if request.generate_speech:
            audio_url = await call_tts_service(
                text=llm_response["text"],
                use_sardaukar=request.use_sardaukar
            )
        
        return QueryResponse(
            query_id=query_id,
            response_id=response_id,
            text=llm_response["text"],
            audio_url=audio_url,
            metadata=llm_response.get("metadata", {})
        )
        
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/speech-to-text")
async def speech_to_text(request: Request):
    """Convert speech to text using ASR service."""
    try:
        # Forward to ASR service
        asr_url = os.getenv("ASR_SERVICE_URL", "http://asr:8001")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{asr_url}/transcribe",
                content=await request.body(),
                headers={"Content-Type": request.headers.get("Content-Type")}
            )
            response.raise_for_status()
            return response.json()
            
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Speech-to-text failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history/{user_id}")
async def get_user_history(user_id: str, limit: int = 10):
    """Get conversation history for a user."""
    try:
        history = await db_manager.get_user_history(user_id, limit)
        return {"user_id": user_id, "history": history}
        
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"History retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def search_knowledge(query: str, limit: int = 5):
    """Search the knowledge base using vector similarity."""
    try:
        results = await db_manager.search_similar(query, limit)
        return {"query": query, "results": results}
        
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Knowledge search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def call_llm_service(text: str) -> Dict[str, Any]:
    """Call the LLM service to generate a response."""
    llm_url = os.getenv("LLM_SERVICE_URL", "http://llm:8002")
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{llm_url}/generate",
            json={"text": text, "max_tokens": 1000}
        )
        response.raise_for_status()
        return response.json()


async def call_tts_service(text: str, use_sardaukar: bool = False) -> str:
    """Call the TTS service to generate speech."""
    tts_url = os.getenv("TTS_SERVICE_URL", "http://tts:8003")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{tts_url}/synthesize",
            json={"text": text, "use_sardaukar": use_sardaukar}
        )
        response.raise_for_status()
        result = response.json()
        return result.get("audio_url")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    ERROR_COUNT.labels(error_type=type(exc).__name__).inc()
    logger.error(f"Unhandled exception: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )