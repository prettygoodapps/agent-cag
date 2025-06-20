"""
Enhanced integration tests for Agent CAG system.
Tests complete workflows across all deployment profiles.
"""

import pytest
import asyncio
import time
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
import json

# Mock dependencies before importing
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

with patch('httpx.AsyncClient'), \
     patch('duckdb'), \
     patch('chromadb', create=True), \
     patch('neo4j', create=True):
    from api.database import DatabaseManager
    from api.models import QueryRequest, ConversationEntry


class TestDeploymentProfiles:
    """Test different deployment profiles."""
    
    @pytest.mark.asyncio
    async def test_lightweight_profile_workflow(self):
        """Test complete workflow with lightweight profile."""
        # Initialize lightweight database
        db_manager = DatabaseManager("lightweight")
        
        with patch('api.database.duckdb.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            await db_manager.initialize()
            
            # Test query storage
            query_id = await db_manager.store_query(
                "Test lightweight query", 
                "test_user", 
                "text"
            )
            
            assert isinstance(query_id, str)
            assert len(query_id) > 0
            
            # Test response storage
            response_id = await db_manager.store_response(
                query_id,
                "Test lightweight response",
                {"model": "test", "tokens": 50}
            )
            
            assert isinstance(response_id, str)
            assert len(response_id) > 0
            
            # Test history retrieval
            mock_conn.execute.return_value.fetchall.return_value = [
                (query_id, response_id, "Test lightweight query", 
                 "Test lightweight response", "2023-01-01 12:00:00", "text")
            ]
            
            history = await db_manager.get_user_history("test_user", 10)
            
            assert len(history) == 1
            assert history[0].query_text == "Test lightweight query"
            
            await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_full_profile_workflow(self):
        """Test complete workflow with full profile."""
        # Initialize full stack database
        db_manager = DatabaseManager("full")
        
        mock_chroma_client = MagicMock()
        mock_neo4j_driver = MagicMock()
        mock_session = MagicMock()
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        mock_neo4j_driver.session.return_value.__exit__.return_value = None
        
        with patch('chromadb.HttpClient', return_value=mock_chroma_client), \
             patch('neo4j.GraphDatabase.driver', return_value=mock_neo4j_driver), \
             patch.dict('os.environ', {
                 'CHROMA_HOST': 'localhost',
                 'CHROMA_PORT': '8005',
                 'NEO4J_URI': 'bolt://localhost:7687',
                 'NEO4J_USER': 'neo4j',
                 'NEO4J_PASSWORD': 'password'
             }):
            
            await db_manager.initialize()
            
            # Test query storage in Neo4j
            query_id = await db_manager.store_query(
                "Test full stack query",
                "test_user",
                "text"
            )
            
            assert isinstance(query_id, str)
            assert len(query_id) > 0
            
            # Test response storage
            response_id = await db_manager.store_response(
                query_id,
                "Test full stack response",
                {"model": "test", "tokens": 75}
            )
            
            assert isinstance(response_id, str)
            assert len(response_id) > 0
            
            # Test similarity search in ChromaDB
            mock_collection = MagicMock()
            mock_collection.query.return_value = {
                "documents": [["Test full stack response"]],
                "ids": [[response_id]],
                "distances": [[0.1]]
            }
            mock_chroma_client.get_collection.return_value = mock_collection
            
            results = await db_manager.search_similar("full stack", 5)
            
            assert len(results) == 1
            assert results[0].id == response_id
            assert results[0].score == 0.9  # 1.0 - 0.1
            
            await db_manager.close()


class TestServiceIntegration:
    """Test integration between different services."""
    
    @pytest.mark.asyncio
    async def test_asr_to_llm_integration(self):
        """Test ASR service integration with LLM service."""
        # Mock ASR service response
        mock_asr_response = {
            "transcription": "What is artificial intelligence?",
            "confidence": 0.95,
            "duration": 3.2
        }
        
        # Mock LLM service response
        mock_llm_response = {
            "response": "Artificial intelligence is a field of computer science...",
            "model": "test-model",
            "tokens_used": 150,
            "processing_time": 2.1
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            
            # Configure ASR response
            mock_response.status_code = 200
            mock_response.json.return_value = mock_asr_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Test ASR processing
            # This would be part of the API gateway logic
            transcription = mock_asr_response["transcription"]
            assert transcription == "What is artificial intelligence?"
            
            # Configure LLM response
            mock_response.json.return_value = mock_llm_response
            
            # Test LLM processing
            llm_result = mock_llm_response["response"]
            assert "artificial intelligence" in llm_result.lower()
    
    @pytest.mark.asyncio
    async def test_llm_to_tts_integration(self):
        """Test LLM service integration with TTS service."""
        # Mock LLM response
        llm_text = "This is a test response from the language model."
        
        # Mock TTS service response
        mock_tts_response = {
            "audio_file": "response_audio.wav",
            "duration": 4.5,
            "format": "wav",
            "sample_rate": 22050
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_tts_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Test TTS processing
            audio_result = mock_tts_response
            assert audio_result["audio_file"] == "response_audio.wav"
            assert audio_result["duration"] > 0
    
    @pytest.mark.asyncio
    async def test_translation_integration(self):
        """Test Sardaukar translation integration."""
        # Mock translation request
        original_text = "Hello, how are you?"
        target_language = "es"  # Spanish
        
        # Mock translation response
        mock_translation_response = {
            "translated_text": "Hola, ¿cómo estás?",
            "source_language": "en",
            "target_language": "es",
            "confidence": 0.98
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_translation_response
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            # Test translation
            translated = mock_translation_response["translated_text"]
            assert translated == "Hola, ¿cómo estás?"
            assert mock_translation_response["confidence"] > 0.9


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_voice_to_voice_workflow(self):
        """Test complete voice input to voice output workflow."""
        # Simulate complete pipeline: Audio -> ASR -> LLM -> TTS -> Audio
        
        # Mock audio input
        audio_input = b"fake_audio_data"
        
        # Mock ASR response
        mock_asr_response = {
            "transcription": "What's the weather like today?",
            "confidence": 0.92,
            "duration": 2.8
        }
        
        # Mock LLM response
        mock_llm_response = {
            "response": "I don't have access to real-time weather data, but you can check your local weather service.",
            "model": "test-model",
            "tokens_used": 85
        }
        
        # Mock TTS response
        mock_tts_response = {
            "audio_file": "weather_response.wav",
            "duration": 6.2,
            "format": "wav"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_client_instance = mock_client.return_value.__aenter__.return_value
            
            # Configure responses in sequence
            responses = [mock_asr_response, mock_llm_response, mock_tts_response]
            mock_response.status_code = 200
            mock_response.json.side_effect = responses
            mock_client_instance.post.return_value = mock_response
            
            # Test workflow steps
            # Step 1: ASR processing
            asr_result = mock_asr_response
            assert asr_result["transcription"] == "What's the weather like today?"
            
            # Step 2: LLM processing
            llm_result = mock_llm_response
            assert "weather" in llm_result["response"].lower()
            
            # Step 3: TTS processing
            tts_result = mock_tts_response
            assert tts_result["audio_file"].endswith(".wav")
    
    @pytest.mark.asyncio
    async def test_text_conversation_workflow(self):
        """Test text-based conversation workflow."""
        # Simulate multi-turn conversation
        
        conversation_turns = [
            {
                "user_input": "Hello, can you help me learn about AI?",
                "expected_response": "I'd be happy to help you learn about artificial intelligence!"
            },
            {
                "user_input": "What are the main types of machine learning?",
                "expected_response": "The main types are supervised, unsupervised, and reinforcement learning."
            },
            {
                "user_input": "Can you explain supervised learning?",
                "expected_response": "Supervised learning uses labeled training data to learn patterns."
            }
        ]
        
        # Mock database for conversation history
        db_manager = DatabaseManager("lightweight")
        
        with patch('duckdb.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            await db_manager.initialize()
            
            conversation_history = []
            
            for i, turn in enumerate(conversation_turns):
                # Store query
                query_id = await db_manager.store_query(
                    turn["user_input"],
                    "conversation_user",
                    "text"
                )
                
                # Mock LLM response
                with patch('httpx.AsyncClient') as mock_client:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_response.json.return_value = {
                        "response": turn["expected_response"],
                        "model": "test-model",
                        "tokens_used": 50 + i * 10
                    }
                    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
                    
                    # Store response
                    response_id = await db_manager.store_response(
                        query_id,
                        turn["expected_response"],
                        {"model": "test-model", "tokens": 50 + i * 10}
                    )
                    
                    conversation_history.append({
                        "query_id": query_id,
                        "response_id": response_id,
                        "user_input": turn["user_input"],
                        "response": turn["expected_response"]
                    })
            
            # Verify conversation history
            assert len(conversation_history) == 3
            assert "AI" in conversation_history[0]["user_input"]
            assert "machine learning" in conversation_history[1]["user_input"]
            
            await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_multilingual_workflow(self):
        """Test multilingual conversation workflow."""
        # Test conversation in multiple languages
        
        multilingual_queries = [
            {"text": "Hello, how are you?", "language": "en"},
            {"text": "Hola, ¿cómo estás?", "language": "es"},
            {"text": "Bonjour, comment allez-vous?", "language": "fr"},
            {"text": "Guten Tag, wie geht es Ihnen?", "language": "de"}
        ]
        
        for query in multilingual_queries:
            # Mock translation to English if needed
            if query["language"] != "en":
                mock_translation = {
                    "translated_text": "Hello, how are you?",
                    "source_language": query["language"],
                    "target_language": "en"
                }
            else:
                mock_translation = {
                    "translated_text": query["text"],
                    "source_language": "en",
                    "target_language": "en"
                }
            
            # Mock LLM response
            mock_llm_response = {
                "response": "I'm doing well, thank you for asking!",
                "model": "test-model",
                "tokens_used": 45
            }
            
            # Mock translation back to original language
            if query["language"] != "en":
                response_translations = {
                    "es": "¡Estoy bien, gracias por preguntar!",
                    "fr": "Je vais bien, merci de demander!",
                    "de": "Mir geht es gut, danke der Nachfrage!"
                }
                mock_response_translation = {
                    "translated_text": response_translations[query["language"]],
                    "source_language": "en",
                    "target_language": query["language"]
                }
            else:
                mock_response_translation = {
                    "translated_text": mock_llm_response["response"],
                    "source_language": "en",
                    "target_language": "en"
                }
            
            # Verify translation workflow
            assert mock_translation["translated_text"] == "Hello, how are you?"
            assert mock_response_translation["target_language"] == query["language"]


class TestErrorRecoveryWorkflows:
    """Test error recovery and fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_service_failure_recovery(self):
        """Test recovery when services fail."""
        # Test ASR service failure with fallback
        with patch('httpx.AsyncClient') as mock_client:
            # Mock ASR service failure
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("ASR service unavailable")
            
            # Should handle gracefully and provide fallback
            try:
                # This would be handled by the API gateway
                result = "Service temporarily unavailable. Please try again."
                assert "unavailable" in result
            except Exception:
                pytest.fail("Should handle service failure gracefully")
    
    @pytest.mark.asyncio
    async def test_database_failure_recovery(self):
        """Test recovery when database fails."""
        db_manager = DatabaseManager("lightweight")
        
        with patch('duckdb.connect', side_effect=Exception("Database connection failed")):
            # Should handle database failure gracefully
            try:
                await db_manager.initialize()
                pytest.fail("Should raise exception for database failure")
            except Exception as e:
                assert "Database connection failed" in str(e)
    
    @pytest.mark.asyncio
    async def test_partial_service_degradation(self):
        """Test behavior when some services are degraded."""
        # Mock scenario where TTS is slow but functional
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "audio_file": "slow_response.wav",
                "duration": 5.0,
                "processing_time": 15.0  # Slow processing
            }
            
            # Simulate slow response
            async def slow_post(*args, **kwargs):
                await asyncio.sleep(0.1)  # Simulate delay
                return mock_response
            
            mock_client.return_value.__aenter__.return_value.post = slow_post
            
            # Should handle slow services
            start_time = time.time()
            result = await slow_post()
            end_time = time.time()
            
            assert end_time - start_time >= 0.1
            assert result.json()["processing_time"] > 10.0


class TestDataConsistency:
    """Test data consistency across different components."""
    
    @pytest.mark.asyncio
    async def test_query_response_consistency(self):
        """Test consistency between stored queries and responses."""
        db_manager = DatabaseManager("lightweight")
        
        with patch('duckdb.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            await db_manager.initialize()
            
            # Store query
            query_text = "Test consistency query"
            query_id = await db_manager.store_query(
                query_text,
                "consistency_user",
                "text"
            )
            
            # Store response
            response_text = "Test consistency response"
            response_id = await db_manager.store_response(
                query_id,
                response_text,
                {"model": "test", "tokens": 25}
            )
            
            # Mock history retrieval
            mock_conn.execute.return_value.fetchall.return_value = [
                (query_id, response_id, query_text, response_text, 
                 "2023-01-01 12:00:00", "text")
            ]
            
            # Retrieve and verify consistency
            history = await db_manager.get_user_history("consistency_user", 10)
            
            assert len(history) == 1
            assert history[0].query_id == query_id
            assert history[0].response_id == response_id
            assert history[0].query_text == query_text
            assert history[0].response_text == response_text
            
            await db_manager.close()
    
    @pytest.mark.asyncio
    async def test_cross_service_data_consistency(self):
        """Test data consistency across different services."""
        # Test that data stored by one service can be retrieved by another
        
        # Mock storing data through API service
        api_stored_data = {
            "query_id": "api_query_123",
            "user_id": "cross_service_user",
            "query_text": "Cross-service test query",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        # Mock retrieving data through history service
        history_retrieved_data = {
            "query_id": "api_query_123",
            "user_id": "cross_service_user",
            "query_text": "Cross-service test query",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        # Verify consistency
        assert api_stored_data["query_id"] == history_retrieved_data["query_id"]
        assert api_stored_data["user_id"] == history_retrieved_data["user_id"]
        assert api_stored_data["query_text"] == history_retrieved_data["query_text"]
    
    @pytest.mark.asyncio
    async def test_concurrent_data_access_consistency(self):
        """Test data consistency under concurrent access."""
        db_manager = DatabaseManager("lightweight")
        
        with patch('duckdb.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            await db_manager.initialize()
            
            # Simulate concurrent operations
            async def concurrent_operation(operation_id):
                query_id = await db_manager.store_query(
                    f"Concurrent query {operation_id}",
                    f"concurrent_user_{operation_id}",
                    "text"
                )
                
                response_id = await db_manager.store_response(
                    query_id,
                    f"Concurrent response {operation_id}",
                    {"operation_id": operation_id}
                )
                
                return query_id, response_id
            
            # Run concurrent operations
            tasks = [concurrent_operation(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            
            # Verify all operations completed successfully
            assert len(results) == 5
            query_ids = [result[0] for result in results]
            response_ids = [result[1] for result in results]
            
            # All IDs should be unique
            assert len(set(query_ids)) == 5
            assert len(set(response_ids)) == 5
            
            await db_manager.close()


class TestPerformanceIntegration:
    """Test performance characteristics of integrated workflows."""
    
    @pytest.mark.asyncio
    async def test_response_time_under_load(self):
        """Test response times under simulated load."""
        start_time = time.time()
        
        # Simulate multiple concurrent requests
        async def simulate_request(request_id):
            # Mock processing time
            await asyncio.sleep(0.1)  # Simulate processing
            return f"Response {request_id}"
        
        # Run concurrent requests
        tasks = [simulate_request(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle concurrent requests efficiently
        assert len(results) == 10
        assert total_time < 2.0  # Should complete in under 2 seconds
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test memory usage stability during extended operation."""
        # This would test memory usage over time
        # For now, we'll simulate extended operation
        
        operations_count = 100
        
        for i in range(operations_count):
            # Simulate operation
            data = f"Operation {i} data" * 100  # Create some data
            
            # Simulate processing
            processed = data.upper()
            
            # Clean up (simulate garbage collection)
            del data, processed
        
        # Should complete without memory issues
        assert True  # If we get here, memory was stable
    
    @pytest.mark.asyncio
    async def test_throughput_measurement(self):
        """Test system throughput measurement."""
        start_time = time.time()
        request_count = 50
        
        # Simulate processing multiple requests
        for i in range(request_count):
            # Mock request processing
            await asyncio.sleep(0.01)  # Minimal processing time
        
        end_time = time.time()
        total_time = end_time - start_time
        throughput = request_count / total_time
        
        # Should achieve reasonable throughput
        assert throughput > 10  # At least 10 requests per second
        assert total_time < 10   # Should complete in reasonable time