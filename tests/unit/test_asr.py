"""
Unit tests for the ASR (Automatic Speech Recognition) service.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import UploadFile
import numpy as np

# Mock dependencies before importing
with patch('asr.main.whisper'), \
     patch('asr.main.torch'), \
     patch('asr.main.sf'), \
     patch('asr.main.librosa'):
    from asr.main import app, preprocess_audio, transcribe_with_whisper, calculate_confidence

client = TestClient(app)


class TestASRHealthEndpoint:
    """Test the ASR health check endpoint."""
    
    def test_health_check_success(self):
        """Test successful health check."""
        with patch('asr.main.whisper_model', 'mocked_model'):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "agent-asr"
            assert "model" in data
            assert "device" in data

    def test_health_check_model_not_loaded(self):
        """Test health check when model is not loaded."""
        with patch('asr.main.whisper_model', None):
            response = client.get("/health")
            
            assert response.status_code == 503


class TestASRTranscription:
    """Test the transcription functionality."""
    
    @pytest.fixture
    def mock_audio_file(self):
        """Create a mock audio file for testing."""
        # Create a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            # Write minimal WAV header and some dummy data
            wav_header = b'RIFF\x24\x08\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x08\x00\x00'
            dummy_audio = b'\x00\x00' * 1000  # 1000 samples of silence
            temp_file.write(wav_header + dummy_audio)
            temp_file.flush()
            
            yield temp_file.name
            
            # Cleanup
            os.unlink(temp_file.name)

    @patch('asr.main.preprocess_audio')
    @patch('asr.main.transcribe_with_whisper')
    @patch('asr.main.calculate_confidence')
    def test_transcribe_audio_success(self, mock_confidence, mock_transcribe, mock_preprocess, mock_audio_file):
        """Test successful audio transcription."""
        # Setup mocks
        mock_preprocess.return_value = np.array([0.1, 0.2, 0.3])
        mock_transcribe.return_value = {
            "text": "Hello world",
            "language": "en",
            "segments": [{"text": "Hello world", "avg_logprob": -0.5}]
        }
        mock_confidence.return_value = 0.85
        
        # Create file upload
        with open(mock_audio_file, 'rb') as f:
            files = {"audio_file": ("test.wav", f, "audio/wav")}
            response = client.post("/transcribe", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello world"
        assert data["language"] == "en"
        assert data["confidence"] == 0.85
        assert "segments" in data

    def test_transcribe_invalid_file_type(self):
        """Test transcription with invalid file type."""
        # Create a text file instead of audio
        with tempfile.NamedTemporaryFile(suffix=".txt", mode='w', delete=False) as temp_file:
            temp_file.write("This is not audio")
            temp_file.flush()
            
            try:
                with open(temp_file.name, 'rb') as f:
                    files = {"audio_file": ("test.txt", f, "text/plain")}
                    response = client.post("/transcribe", files=files)
                
                assert response.status_code == 400
                assert "audio file" in response.json()["detail"].lower()
            finally:
                os.unlink(temp_file.name)

    @patch('asr.main.preprocess_audio')
    def test_transcribe_preprocessing_error(self, mock_preprocess, mock_audio_file):
        """Test transcription when preprocessing fails."""
        mock_preprocess.side_effect = Exception("Preprocessing failed")
        
        with open(mock_audio_file, 'rb') as f:
            files = {"audio_file": ("test.wav", f, "audio/wav")}
            response = client.post("/transcribe", files=files)
        
        assert response.status_code == 500


class TestASRUtilityFunctions:
    """Test utility functions."""
    
    @patch('asr.main.librosa.load')
    @patch('asr.main.librosa.util.normalize')
    def test_preprocess_audio_success(self, mock_normalize, mock_load):
        """Test successful audio preprocessing."""
        mock_load.return_value = (np.array([0.1, 0.2, 0.3]), 16000)
        mock_normalize.return_value = np.array([0.1, 0.2, 0.3])
        
        result = preprocess_audio("test.wav")
        
        mock_load.assert_called_once_with("test.wav", sr=16000)
        mock_normalize.assert_called_once()
        assert isinstance(result, np.ndarray)

    @patch('asr.main.librosa.load')
    def test_preprocess_audio_error(self, mock_load):
        """Test audio preprocessing error handling."""
        mock_load.side_effect = Exception("File not found")
        
        with pytest.raises(Exception):
            preprocess_audio("nonexistent.wav")

    @patch('asr.main.whisper_model')
    def test_transcribe_with_whisper_success(self, mock_model):
        """Test successful Whisper transcription."""
        mock_model.transcribe.return_value = {
            "text": "Test transcription",
            "language": "en"
        }
        
        audio_data = np.array([0.1, 0.2, 0.3])
        result = transcribe_with_whisper(audio_data, language="en")
        
        assert result["text"] == "Test transcription"
        assert result["language"] == "en"
        mock_model.transcribe.assert_called_once()

    def test_transcribe_with_whisper_no_model(self):
        """Test transcription when model is not loaded."""
        with patch('asr.main.whisper_model', None):
            with pytest.raises(Exception, match="Whisper model not loaded"):
                transcribe_with_whisper(np.array([0.1, 0.2, 0.3]))

    def test_calculate_confidence_with_segments(self):
        """Test confidence calculation with segments."""
        result = {
            "segments": [
                {"avg_logprob": -0.5},
                {"avg_logprob": -0.3},
                {"avg_logprob": -0.7}
            ]
        }
        
        confidence = calculate_confidence(result)
        
        assert 0.0 <= confidence <= 1.0
        assert isinstance(confidence, float)

    def test_calculate_confidence_no_segments(self):
        """Test confidence calculation without segments."""
        result = {"text": "Hello world"}
        
        confidence = calculate_confidence(result)
        
        assert confidence == 0.8  # Default confidence

    def test_calculate_confidence_error(self):
        """Test confidence calculation error handling."""
        result = {"segments": [{"invalid": "data"}]}
        
        confidence = calculate_confidence(result)
        
        assert confidence == 0.5  # Error fallback


class TestASRMetrics:
    """Test metrics endpoints."""
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint accessibility."""
        response = client.get("/metrics")
        
        # Should return prometheus metrics format
        assert response.status_code == 200
        # Basic check for prometheus format
        assert isinstance(response.content, bytes)


class TestASRStreamingPlaceholder:
    """Test streaming transcription placeholder."""
    
    def test_streaming_not_implemented(self):
        """Test that streaming endpoint returns not implemented."""
        response = client.post("/transcribe-stream")
        
        assert response.status_code == 501
        assert "not yet implemented" in response.json()["detail"]