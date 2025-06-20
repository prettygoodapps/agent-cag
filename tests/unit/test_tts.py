"""
Unit tests for the TTS (Text-to-Speech) service.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Mock dependencies before importing
with patch('tts.main.httpx'), \
     patch('tts.main.subprocess'), \
     patch('tts.main.sf'):
    from tts.main import app, translate_to_sardaukar, generate_speech, get_audio_duration

client = TestClient(app)


class TestTTSHealthEndpoint:
    """Test the TTS health check endpoint."""
    
    def test_health_check_success(self):
        """Test successful health check."""
        with patch('tts.main.PIPER_MODEL', 'en_US-lessac-medium'):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "agent-tts"
            assert data["model"] == "en_US-lessac-medium"
            assert "sardaukar_enabled" in data

    def test_health_check_model_not_loaded(self):
        """Test health check when Piper model is not loaded."""
        with patch('tts.main.PIPER_MODEL', None):
            response = client.get("/health")
            
            assert response.status_code == 503

    def test_health_check_sardaukar_enabled(self):
        """Test health check with Sardaukar enabled."""
        with patch('tts.main.PIPER_MODEL', 'test-model'), \
             patch.dict('os.environ', {'SARDAUKAR_TRANSLATOR_URL': 'http://sardaukar:8004'}):
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["sardaukar_enabled"] == True


class TestTTSSynthesis:
    """Test speech synthesis functionality."""
    
    @patch('tts.main.generate_speech')
    @patch('tts.main.get_audio_duration')
    def test_synthesize_speech_success(self, mock_duration, mock_generate):
        """Test successful speech synthesis."""
        mock_generate.return_value = "/app/output/test-audio.wav"
        mock_duration.return_value = 2.5
        
        response = client.post("/synthesize", json={
            "text": "Hello, this is a test.",
            "use_sardaukar": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_text"] == "Hello, this is a test."
        assert data["final_text"] == "Hello, this is a test."
        assert data["used_sardaukar"] == False
        assert data["duration"] == 2.5
        assert data["format"] == "wav"
        assert "/audio/" in data["audio_url"]

    @patch('tts.main.translate_to_sardaukar')
    @patch('tts.main.generate_speech')
    @patch('tts.main.get_audio_duration')
    async def test_synthesize_speech_with_sardaukar(self, mock_duration, mock_generate, mock_translate):
        """Test speech synthesis with Sardaukar translation."""
        mock_translate.return_value = "Sardaukar translated text"
        mock_generate.return_value = "/app/output/test-audio.wav"
        mock_duration.return_value = 3.0
        
        response = client.post("/synthesize", json={
            "text": "Hello world",
            "use_sardaukar": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_text"] == "Hello world"
        assert data["final_text"] == "Sardaukar translated text"
        assert data["used_sardaukar"] == True

    @patch('tts.main.translate_to_sardaukar')
    @patch('tts.main.generate_speech')
    @patch('tts.main.get_audio_duration')
    async def test_synthesize_speech_sardaukar_fallback(self, mock_duration, mock_generate, mock_translate):
        """Test speech synthesis with Sardaukar translation failure fallback."""
        mock_translate.side_effect = Exception("Translation failed")
        mock_generate.return_value = "/app/output/test-audio.wav"
        mock_duration.return_value = 2.0
        
        response = client.post("/synthesize", json={
            "text": "Hello world",
            "use_sardaukar": True
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["original_text"] == "Hello world"
        assert data["final_text"] == "Hello world"  # Fallback to original
        assert data["used_sardaukar"] == False

    def test_synthesize_speech_invalid_request(self):
        """Test speech synthesis with invalid request."""
        response = client.post("/synthesize", json={})
        
        assert response.status_code == 422  # Validation error

    @patch('tts.main.generate_speech')
    def test_synthesize_speech_generation_error(self, mock_generate):
        """Test speech synthesis when generation fails."""
        mock_generate.side_effect = Exception("Generation failed")
        
        response = client.post("/synthesize", json={
            "text": "Test text"
        })
        
        assert response.status_code == 500


class TestTTSAudioServing:
    """Test audio file serving."""
    
    def test_get_audio_file_not_found(self):
        """Test getting non-existent audio file."""
        response = client.get("/audio/nonexistent.wav")
        
        assert response.status_code == 404

    @patch('os.path.exists')
    @patch('tts.main.FileResponse')
    def test_get_audio_file_success(self, mock_file_response, mock_exists):
        """Test successful audio file retrieval."""
        mock_exists.return_value = True
        mock_file_response.return_value = MagicMock()
        
        response = client.get("/audio/test.wav")
        
        # The actual response depends on FileResponse mock
        mock_exists.assert_called_once()
        mock_file_response.assert_called_once()


class TestTTSUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_translate_to_sardaukar_success(self):
        """Test successful Sardaukar translation."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"sardaukar": "Translated text"}
        mock_response.raise_for_status = MagicMock()
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        
        with patch('tts.main.httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'SARDAUKAR_TRANSLATOR_URL': 'http://sardaukar:8004'}):
            
            result = await translate_to_sardaukar("Hello world")
            
            assert result == "Translated text"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_translate_to_sardaukar_no_url(self):
        """Test Sardaukar translation without URL configured."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(Exception, match="Sardaukar translator URL not configured"):
                await translate_to_sardaukar("Hello world")

    @pytest.mark.asyncio
    async def test_translate_to_sardaukar_http_error(self):
        """Test Sardaukar translation HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP error")
        
        mock_client = MagicMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        
        with patch('tts.main.httpx.AsyncClient', return_value=mock_client), \
             patch.dict('os.environ', {'SARDAUKAR_TRANSLATOR_URL': 'http://sardaukar:8004'}):
            
            with pytest.raises(Exception):
                await translate_to_sardaukar("Hello world")

    @pytest.mark.asyncio
    async def test_generate_speech_success(self):
        """Test successful speech generation."""
        with patch('tts.main.generate_speech_with_espeak') as mock_espeak, \
             patch('tts.main.OUTPUT_DIR', '/tmp'):
            
            mock_espeak.return_value = None
            
            result = await generate_speech("Hello world")
            
            assert result.startswith('/tmp/')
            assert result.endswith('.wav')
            mock_espeak.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_speech_with_voice(self):
        """Test speech generation with specific voice."""
        with patch('tts.main.generate_speech_with_espeak') as mock_espeak, \
             patch('tts.main.OUTPUT_DIR', '/tmp'):
            
            result = await generate_speech("Hello world", voice="female")
            
            assert result.endswith('.wav')
            mock_espeak.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_speech_error(self):
        """Test speech generation error handling."""
        with patch('tts.main.generate_speech_with_espeak') as mock_espeak:
            mock_espeak.side_effect = Exception("Generation failed")
            
            with pytest.raises(Exception):
                await generate_speech("Hello world")

    @pytest.mark.asyncio
    @patch('tts.main.subprocess.run')
    async def test_generate_speech_with_espeak_success(self, mock_run):
        """Test successful espeak generation."""
        from tts.main import generate_speech_with_espeak
        
        mock_run.return_value = MagicMock(returncode=0)
        
        await generate_speech_with_espeak("Hello world", "/tmp/test.wav")
        
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "espeak-ng" in args
        assert "Hello world" in args

    @pytest.mark.asyncio
    @patch('tts.main.subprocess.run')
    async def test_generate_speech_with_espeak_error(self, mock_run):
        """Test espeak generation error."""
        from tts.main import generate_speech_with_espeak
        
        mock_run.side_effect = Exception("Command failed")
        
        with pytest.raises(Exception):
            await generate_speech_with_espeak("Hello world", "/tmp/test.wav")

    @patch('tts.main.sf.read')
    def test_get_audio_duration_success(self, mock_read):
        """Test successful audio duration calculation."""
        mock_read.return_value = ([0.1, 0.2, 0.3] * 1000, 16000)  # 3000 samples at 16kHz
        
        duration = get_audio_duration("/tmp/test.wav")
        
        assert duration == 0.1875  # 3000 / 16000
        mock_read.assert_called_once_with("/tmp/test.wav")

    @patch('tts.main.sf.read')
    def test_get_audio_duration_error(self, mock_read):
        """Test audio duration calculation error handling."""
        mock_read.side_effect = Exception("File read error")
        
        duration = get_audio_duration("/tmp/test.wav")
        
        assert duration is None


class TestTTSVoicesEndpoint:
    """Test voices listing endpoint."""
    
    def test_list_voices(self):
        """Test voices listing."""
        response = client.post("/voices")
        
        assert response.status_code == 200
        data = response.json()
        assert "voices" in data
        assert len(data["voices"]) > 0
        
        # Check voice structure
        voice = data["voices"][0]
        assert "id" in voice
        assert "name" in voice
        assert "language" in voice
        assert "gender" in voice


class TestTTSMetrics:
    """Test metrics endpoints."""
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint accessibility."""
        response = client.get("/metrics")
        
        # Should return prometheus metrics format
        assert response.status_code == 200
        assert isinstance(response.content, bytes)


class TestTTSInitialization:
    """Test TTS initialization functions."""
    
    @patch('tts.main.os.makedirs')
    def test_initialize_piper_success(self, mock_makedirs):
        """Test successful Piper initialization."""
        from tts.main import initialize_piper
        
        with patch.dict('os.environ', {'PIPER_MODEL': 'test-model'}):
            initialize_piper()
            
            # Should not raise any exceptions

    def test_initialize_piper_default_model(self):
        """Test Piper initialization with default model."""
        from tts.main import initialize_piper
        
        with patch.dict('os.environ', {}, clear=True):
            initialize_piper()
            
            # Should use default model without errors


class TestTTSErrorHandling:
    """Test error handling scenarios."""
    
    @patch('tts.main.generate_speech')
    def test_synthesis_unexpected_error(self, mock_generate):
        """Test handling of unexpected errors during synthesis."""
        mock_generate.side_effect = RuntimeError("Unexpected error")
        
        response = client.post("/synthesize", json={
            "text": "Test text"
        })
        
        assert response.status_code == 500

    def test_synthesis_empty_text(self):
        """Test synthesis with empty text."""
        response = client.post("/synthesize", json={
            "text": "",
            "use_sardaukar": False
        })
        
        # Should handle empty text gracefully
        assert response.status_code in [200, 422]  # Either success or validation error

    @patch('tts.main.generate_speech')
    @patch('tts.main.get_audio_duration')
    def test_synthesis_duration_calculation_error(self, mock_duration, mock_generate):
        """Test synthesis when duration calculation fails."""
        mock_generate.return_value = "/app/output/test.wav"
        mock_duration.return_value = None  # Duration calculation failed
        
        response = client.post("/synthesize", json={
            "text": "Test text"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["duration"] is None