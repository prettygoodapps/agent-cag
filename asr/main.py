"""
ASR (Automatic Speech Recognition) Service

Uses OpenAI Whisper for speech-to-text conversion.
"""

import os
import logging
import tempfile
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import whisper
import torch
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import start_http_server
import soundfile as sf
import librosa

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('asr_requests_total', 'Total ASR requests')
REQUEST_DURATION = Histogram('asr_request_duration_seconds', 'ASR request duration')
TRANSCRIPTION_COUNT = Counter('transcriptions_total', 'Total transcriptions')
ERROR_COUNT = Counter('asr_errors_total', 'Total ASR errors', ['error_type'])

# Global Whisper model
whisper_model = None


def load_whisper_model():
    """Load Whisper model."""
    global whisper_model
    
    model_name = os.getenv("WHISPER_MODEL", "base")
    logger.info(f"Loading Whisper model: {model_name}")
    
    try:
        # Check if CUDA is available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")
        
        whisper_model = whisper.load_model(model_name, device=device)
        logger.info("Whisper model loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load Whisper model: {e}")
        raise


# Initialize FastAPI app
app = FastAPI(
    title="Agent CAG ASR Service",
    description="Automatic Speech Recognition using OpenAI Whisper",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    logger.info("Starting ASR Service...")
    
    # Load Whisper model
    load_whisper_model()
    
    # Start Prometheus metrics server if enabled
    if os.getenv("METRICS_ENABLED", "false").lower() == "true":
        start_http_server(8081)
        logger.info("Prometheus metrics server started on port 8081")
    
    logger.info("ASR Service started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if whisper_model is None:
            raise Exception("Whisper model not loaded")
        
        return {
            "status": "healthy",
            "service": "agent-asr",
            "model": os.getenv("WHISPER_MODEL", "base"),
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    language: Optional[str] = None
):
    """Transcribe audio file to text."""
    try:
        REQUEST_COUNT.inc()
        
        with REQUEST_DURATION.time():
            # Validate file type
            if not audio_file.content_type.startswith('audio/'):
                raise HTTPException(
                    status_code=400,
                    detail="File must be an audio file"
                )
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                content = await audio_file.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Load and preprocess audio
                audio_data = preprocess_audio(temp_file_path)
                
                # Transcribe using Whisper
                result = transcribe_with_whisper(audio_data, language)
                
                TRANSCRIPTION_COUNT.inc()
                
                return {
                    "text": result["text"],
                    "language": result.get("language"),
                    "confidence": calculate_confidence(result),
                    "segments": result.get("segments", [])
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def preprocess_audio(file_path: str):
    """Preprocess audio file for Whisper."""
    try:
        # Load audio file
        audio, sr = librosa.load(file_path, sr=16000)  # Whisper expects 16kHz
        
        # Normalize audio
        audio = librosa.util.normalize(audio)
        
        return audio
        
    except Exception as e:
        logger.error(f"Audio preprocessing failed: {e}")
        raise


def transcribe_with_whisper(audio_data, language: Optional[str] = None):
    """Transcribe audio using Whisper model."""
    try:
        if whisper_model is None:
            raise Exception("Whisper model not loaded")
        
        # Transcribe
        options = {
            "fp16": torch.cuda.is_available(),  # Use FP16 if CUDA available
            "language": language,
            "task": "transcribe"
        }
        
        result = whisper_model.transcribe(audio_data, **options)
        
        return result
        
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise


def calculate_confidence(result):
    """Calculate average confidence from Whisper result."""
    try:
        if "segments" in result and result["segments"]:
            # Calculate average confidence from segments
            total_confidence = 0
            segment_count = 0
            
            for segment in result["segments"]:
                if "avg_logprob" in segment:
                    # Convert log probability to confidence (0-1)
                    confidence = min(1.0, max(0.0, (segment["avg_logprob"] + 1.0)))
                    total_confidence += confidence
                    segment_count += 1
            
            if segment_count > 0:
                return total_confidence / segment_count
        
        # Default confidence if no segments available
        return 0.8
        
    except Exception as e:
        logger.warning(f"Confidence calculation failed: {e}")
        return 0.5


@app.post("/transcribe-stream")
async def transcribe_stream():
    """Placeholder for streaming transcription (future implementation)."""
    raise HTTPException(
        status_code=501,
        detail="Streaming transcription not yet implemented"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
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
        port=8001,
        reload=True,
        log_level="info"
    )