"""
Unit tests for the LLM (Large Language Model) service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

# Mock dependencies before importing
with patch('llm.main.ollama'), \
     patch('llm.main.subprocess'), \
     patch('llm.main.socket'):
    from llm.main import app, initialize_llm, generate_with_ollama, get_host_gateway_ip

client = TestClient(app)


class TestLLMHealthEndpoint:
    """Test the LLM health check endpoint."""
    
    def test_health_check_success(self):
        """Test successful health check."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            'models': [
                {'name': 'llama3'},
                {'name': 'mistral'}
            ]
        }
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client):
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "agent-llm"
            assert "model" in data
            assert "available_models" in data
            assert len(data["available_models"]) == 2

    def test_health_check_client_not_initialized(self):
        """Test health check when Ollama client is not initialized."""
        with patch('llm.main.OLLAMA_CLIENT', None):
            response = client.get("/health")
            
            assert response.status_code == 503

    def test_health_check_ollama_connection_error(self):
        """Test health check when Ollama connection fails."""
        mock_client = MagicMock()
        mock_client.list.side_effect = Exception("Connection failed")
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client):
            response = client.get("/health")
            
            assert response.status_code == 503


class TestLLMGeneration:
    """Test text generation functionality."""
    
    @pytest.mark.asyncio
    async def test_generate_text_success(self):
        """Test successful text generation."""
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            'response': 'This is a generated response.',
            'done': True,
            'total_duration': 1000000,
            'load_duration': 100000,
            'prompt_eval_count': 10,
            'eval_count': 20
        }
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client), \
             patch('llm.main.MODEL_NAME', 'llama3'):
            
            response = client.post("/generate", json={
                "text": "What is artificial intelligence?",
                "max_tokens": 500,
                "temperature": 0.7
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "This is a generated response."
            assert data["model"] == "llama3"
            assert data["tokens_used"] > 0
            assert "metadata" in data

    @pytest.mark.asyncio
    async def test_generate_text_with_system_prompt(self):
        """Test text generation with system prompt."""
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            'response': 'System-guided response.',
            'done': True
        }
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client), \
             patch('llm.main.MODEL_NAME', 'llama3'):
            
            response = client.post("/generate", json={
                "text": "Explain quantum computing",
                "system_prompt": "You are a physics expert."
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "System-guided response."

    def test_generate_text_invalid_request(self):
        """Test text generation with invalid request."""
        response = client.post("/generate", json={})
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_generate_text_ollama_error(self):
        """Test text generation when Ollama fails."""
        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("Ollama error")
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client), \
             patch('llm.main.MODEL_NAME', 'llama3'):
            
            response = client.post("/generate", json={
                "text": "Test query"
            })
            
            assert response.status_code == 200  # Should return fallback response
            data = response.json()
            assert "unable to process" in data["text"].lower()
            assert data["metadata"]["fallback"] == True


class TestLLMUtilityFunctions:
    """Test utility functions."""
    
    @pytest.mark.asyncio
    async def test_generate_with_ollama_success(self):
        """Test successful Ollama generation."""
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            'response': 'Generated text response',
            'done': True,
            'total_duration': 2000000,
            'eval_count': 25
        }
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client), \
             patch('llm.main.MODEL_NAME', 'llama3'):
            
            result = await generate_with_ollama(
                prompt="Test prompt",
                max_tokens=100,
                temperature=0.5
            )
            
            assert result["text"] == "Generated text response"
            assert result["tokens_used"] > 0
            assert "metadata" in result
            mock_client.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_ollama_client_not_initialized(self):
        """Test generation when client is not initialized."""
        with patch('llm.main.OLLAMA_CLIENT', None):
            result = await generate_with_ollama("Test prompt")
            
            assert "unable to process" in result["text"].lower()
            assert result["metadata"]["fallback"] == True

    @pytest.mark.asyncio
    async def test_generate_with_ollama_error(self):
        """Test generation error handling."""
        mock_client = MagicMock()
        mock_client.generate.side_effect = Exception("Generation failed")
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client):
            result = await generate_with_ollama("Test prompt")
            
            assert "unable to process" in result["text"].lower()
            assert result["metadata"]["error"] == "Generation failed"

    @patch('llm.main.subprocess.run')
    def test_get_host_gateway_ip_success(self, mock_run):
        """Test successful gateway IP discovery."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="default via 172.18.0.1 dev eth0"
        )
        
        ip = get_host_gateway_ip()
        
        assert ip == "172.18.0.1"

    @patch('llm.main.subprocess.run')
    @patch('llm.main.socket.gethostbyname')
    def test_get_host_gateway_ip_fallback_docker_internal(self, mock_gethostbyname, mock_run):
        """Test gateway IP discovery with docker internal fallback."""
        mock_run.return_value = MagicMock(returncode=1)
        mock_gethostbyname.return_value = "192.168.65.2"
        
        ip = get_host_gateway_ip()
        
        assert ip == "192.168.65.2"

    @patch('llm.main.subprocess.run')
    @patch('llm.main.socket.gethostbyname')
    def test_get_host_gateway_ip_final_fallback(self, mock_gethostbyname, mock_run):
        """Test gateway IP discovery with final fallback."""
        mock_run.return_value = MagicMock(returncode=1)
        mock_gethostbyname.side_effect = Exception("DNS error")
        
        ip = get_host_gateway_ip()
        
        assert ip == "172.18.0.1"  # Final fallback


class TestLLMModelsEndpoint:
    """Test models listing endpoint."""
    
    def test_list_models_success(self):
        """Test successful model listing."""
        mock_client = MagicMock()
        mock_client.list.return_value = {
            'models': [
                {'name': 'llama3', 'size': 4000000000},
                {'name': 'mistral', 'size': 7000000000}
            ]
        }
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client), \
             patch('llm.main.MODEL_NAME', 'llama3'):
            
            response = client.get("/models")
            
            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert data["current_model"] == "llama3"
            assert len(data["models"]) == 2

    def test_list_models_client_not_initialized(self):
        """Test model listing when client is not initialized."""
        with patch('llm.main.OLLAMA_CLIENT', None):
            response = client.get("/models")
            
            assert response.status_code == 500


class TestLLMChatCompletion:
    """Test chat completion endpoint."""
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self):
        """Test successful chat completion."""
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            'response': 'Chat response from assistant.',
            'done': True
        }
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client), \
             patch('llm.main.MODEL_NAME', 'llama3'):
            
            response = client.post("/chat", json={
                "text": "Hello, how are you?",
                "system_prompt": "You are a helpful assistant."
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Chat response from assistant."

    @pytest.mark.asyncio
    async def test_chat_completion_default_system_prompt(self):
        """Test chat completion with default system prompt."""
        mock_client = MagicMock()
        mock_client.generate.return_value = {
            'response': 'Default assistant response.',
            'done': True
        }
        
        with patch('llm.main.OLLAMA_CLIENT', mock_client), \
             patch('llm.main.MODEL_NAME', 'llama3'):
            
            response = client.post("/chat", json={
                "text": "What's the weather like?"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["text"] == "Default assistant response."


class TestLLMMetrics:
    """Test metrics endpoints."""
    
    def test_metrics_endpoint(self):
        """Test metrics endpoint accessibility."""
        response = client.get("/metrics")
        
        # Should return prometheus metrics format
        assert response.status_code == 200
        assert isinstance(response.content, bytes)


class TestLLMInitialization:
    """Test LLM initialization functions."""
    
    @patch('llm.main.ollama.Client')
    def test_initialize_llm_success(self, mock_ollama_client):
        """Test successful LLM initialization."""
        mock_client = MagicMock()
        mock_client.list.return_value = {'models': [{'name': 'llama3'}]}
        mock_ollama_client.return_value = mock_client
        
        with patch.dict('os.environ', {
            'MODEL_NAME': 'llama3',
            'OLLAMA_HOST': 'http://localhost:11434'
        }):
            initialize_llm()
            
            mock_ollama_client.assert_called_once_with(host='http://localhost:11434')

    @patch('llm.main.ollama.Client')
    def test_initialize_llm_model_not_found(self, mock_ollama_client):
        """Test LLM initialization when model is not found."""
        mock_client = MagicMock()
        mock_client.list.return_value = {'models': []}
        mock_client.pull = MagicMock()
        mock_ollama_client.return_value = mock_client
        
        with patch.dict('os.environ', {'MODEL_NAME': 'missing-model'}):
            initialize_llm()
            
            mock_client.pull.assert_called_once_with('missing-model')

    @patch('llm.main.ollama.Client')
    def test_initialize_llm_connection_error(self, mock_ollama_client):
        """Test LLM initialization connection error."""
        mock_ollama_client.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception):
            initialize_llm()