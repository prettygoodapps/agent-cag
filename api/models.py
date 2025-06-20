"""
Pydantic models for the Agent CAG API service.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from enum import Enum


class InputType(str, Enum):
    """Input type enumeration."""
    TEXT = "text"
    SPEECH = "speech"


class QueryRequest(BaseModel):
    """Request model for query processing."""
    text: str = Field(..., description="The query text to process")
    user_id: Optional[str] = Field(None, description="User identifier")
    input_type: InputType = Field(InputType.TEXT, description="Type of input")
    generate_speech: bool = Field(False, description="Whether to generate speech output")
    use_sardaukar: bool = Field(False, description="Whether to use Sardaukar translation for speech")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class QueryResponse(BaseModel):
    """Response model for query processing."""
    query_id: str = Field(..., description="Unique identifier for the query")
    response_id: str = Field(..., description="Unique identifier for the response")
    text: str = Field(..., description="The generated response text")
    audio_url: Optional[str] = Field(None, description="URL to generated audio file")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    service: str = Field(..., description="Service name")
    profile: str = Field(..., description="Deployment profile")
    version: str = Field(..., description="Service version")
    timestamp: Optional[str] = Field(None, description="Health check timestamp")


class TranscriptionRequest(BaseModel):
    """Request model for speech transcription."""
    audio_data: bytes = Field(..., description="Audio data to transcribe")
    format: str = Field("wav", description="Audio format")
    language: Optional[str] = Field("en", description="Language code")


class TranscriptionResponse(BaseModel):
    """Response model for speech transcription."""
    text: str = Field(..., description="Transcribed text")
    confidence: Optional[float] = Field(None, description="Transcription confidence")
    language: Optional[str] = Field(None, description="Detected language")


class SynthesisRequest(BaseModel):
    """Request model for speech synthesis."""
    text: str = Field(..., description="Text to synthesize")
    voice: Optional[str] = Field(None, description="Voice to use")
    use_sardaukar: bool = Field(False, description="Whether to translate to Sardaukar first")


class SynthesisResponse(BaseModel):
    """Response model for speech synthesis."""
    audio_url: str = Field(..., description="URL to generated audio file")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")
    format: str = Field("wav", description="Audio format")


class ConversationEntry(BaseModel):
    """Model for conversation history entries."""
    query_id: str = Field(..., description="Query identifier")
    response_id: str = Field(..., description="Response identifier")
    query_text: str = Field(..., description="Original query")
    response_text: str = Field(..., description="Generated response")
    timestamp: str = Field(..., description="Entry timestamp")
    input_type: InputType = Field(..., description="Type of input")


class SearchResult(BaseModel):
    """Model for search results."""
    id: str = Field(..., description="Result identifier")
    text: str = Field(..., description="Result text")
    score: float = Field(..., description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")