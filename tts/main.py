"""
TTS (Text-to-Speech) Service

Converts text to speech using Piper TTS with optional Sardaukar translation.
"""

import os
import logging
import tempfile
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import httpx
from prometheus_client import Counter, Histogram, generate_latest
from prometheus_client import start_http_server
import subprocess
import soundfile as sf

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('tts_requests_total', 'Total TTS requests')
REQUEST_DURATION = Histogram('tts_request_duration_seconds', 'TTS request duration')
SYNTHESIS_COUNT = Counter('synthesis_total', 'Total syntheses')
SARDAUKAR_COUNT = Counter('sardaukar_translations_total', 'Total Sardaukar translations')
ERROR_COUNT = Counter('tts_errors_total', 'Total TTS errors', ['error_type'])

# Global configuration
PIPER_MODEL = None
OUTPUT_DIR = "/app/output"


class SynthesisRequest(BaseModel):
    """Request model for speech synthesis."""
    text: str
    voice: Optional[str] = None
    use_sardaukar: bool = False


class SynthesisResponse(BaseModel):
    """Response model for speech synthesis."""
    audio_url: str
    duration: Optional[float] = None
    format: str = "wav"
    original_text: str
    final_text: str
    used_sardaukar: bool


def initialize_piper():
    """Initialize Piper TTS model."""
    global PIPER_MODEL
    
    model_name = os.getenv("PIPER_MODEL", "en_US-lessac-medium")
    logger.info(f"Initializing Piper TTS with model: {model_name}")
    
    try:
        # In a real implementation, you would download and load the Piper model
        # For now, we'll use a placeholder
        PIPER_MODEL = model_name
        logger.info("Piper TTS initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Piper TTS: {e}")
        raise


# Initialize FastAPI app
app = FastAPI(
    title="Agent CAG TTS Service",
    description="Text-to-Speech with optional Sardaukar translation",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Initialize the service."""
    logger.info("Starting TTS Service...")
    
    # Initialize Piper TTS
    initialize_piper()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Start Prometheus metrics server if enabled
    if os.getenv("METRICS_ENABLED", "false").lower() == "true":
        start_http_server(8083)
        logger.info("Prometheus metrics server started on port 8083")
    
    logger.info("TTS Service started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        if PIPER_MODEL is None:
            raise Exception("Piper TTS not initialized")
        
        return {
            "status": "healthy",
            "service": "agent-tts",
            "model": PIPER_MODEL,
            "sardaukar_enabled": os.getenv("SARDAUKAR_TRANSLATOR_URL") is not None
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()


@app.post("/synthesize", response_model=SynthesisResponse)
async def synthesize_speech(request: SynthesisRequest):
    """Synthesize speech from text."""
    try:
        REQUEST_COUNT.inc()
        
        with REQUEST_DURATION.time():
            original_text = request.text
            final_text = original_text
            used_sardaukar = False
            
            # Translate to Sardaukar if requested
            if request.use_sardaukar:
                try:
                    final_text = await translate_to_sardaukar(original_text)
                    used_sardaukar = True
                    SARDAUKAR_COUNT.inc()
                    logger.info(f"Translated to Sardaukar: '{original_text}' -> '{final_text}'")
                except Exception as e:
                    logger.warning(f"Sardaukar translation failed, using original text: {e}")
                    final_text = original_text
                    used_sardaukar = False
            
            # Generate speech
            audio_file_path = await generate_speech(final_text, request.voice)
            
            # Calculate duration
            duration = get_audio_duration(audio_file_path)
            
            # Generate URL for the audio file
            audio_filename = os.path.basename(audio_file_path)
            audio_url = f"/audio/{audio_filename}"
            
            SYNTHESIS_COUNT.inc()
            
            return SynthesisResponse(
                audio_url=audio_url,
                duration=duration,
                format="wav",
                original_text=original_text,
                final_text=final_text,
                used_sardaukar=used_sardaukar
            )
            
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Speech synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/audio/{filename}")
async def get_audio_file(filename: str):
    """Serve generated audio files."""
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        file_path,
        media_type="audio/wav",
        filename=filename
    )


async def translate_to_sardaukar(text: str) -> str:
    """Translate text to Sardaukar using the translator service."""
    sardaukar_url = os.getenv("SARDAUKAR_TRANSLATOR_URL")
    
    if not sardaukar_url:
        raise Exception("Sardaukar translator URL not configured")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            f"{sardaukar_url}/api/translate",
            json={
                "text": text,
                "include_phonetics": False
            }
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("sardaukar", text)


async def generate_speech(text: str, voice: Optional[str] = None) -> str:
    """Generate speech using Piper TTS."""
    try:
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        output_path = os.path.join(OUTPUT_DIR, f"{audio_id}.wav")
        
        # Use espeak-ng as a fallback TTS engine
        # In a real implementation, you would use Piper TTS
        await generate_speech_with_espeak(text, output_path)
        
        return output_path
        
    except Exception as e:
        logger.error(f"Speech generation failed: {e}")
        raise


async def generate_speech_with_espeak(text: str, output_path: str):
    """Generate speech using espeak-ng (fallback implementation)."""
    try:
        # Use espeak-ng to generate speech
        cmd = [
            "espeak-ng",
            "-s", "150",  # Speed
            "-v", "en+f3",  # Voice
            "-w", output_path,  # Output file
            text
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.returncode != 0:
            raise Exception(f"espeak-ng failed: {result.stderr}")
        
        logger.info(f"Generated speech file: {output_path}")
        
    except subprocess.CalledProcessError as e:
        logger.error(f"espeak-ng command failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Speech generation error: {e}")
        raise


def get_audio_duration(file_path: str) -> Optional[float]:
    """Get duration of audio file in seconds."""
    try:
        data, sample_rate = sf.read(file_path)
        duration = len(data) / sample_rate
        return duration
    except Exception as e:
        logger.warning(f"Could not determine audio duration: {e}")
        return None


@app.post("/voices")
async def list_voices():
    """List available voices."""
    # In a real implementation, you would return available Piper voices
    return {
        "voices": [
            {
                "id": "en_US-lessac-medium",
                "name": "Lessac (English US)",
                "language": "en-US",
                "gender": "female"
            },
            {
                "id": "en_US-ryan-medium",
                "name": "Ryan (English US)",
                "language": "en-US",
                "gender": "male"
            }
        ]
    }


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
        port=8003,
        reload=True,
        log_level="info"
    )