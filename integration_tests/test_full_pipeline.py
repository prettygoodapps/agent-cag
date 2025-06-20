"""
Integration tests for the full Agent CAG pipeline.
"""

import pytest
import httpx
import asyncio
import time
from typing import Dict, Any


class TestAgentPipeline:
    """Test the complete agent pipeline."""

    BASE_URL = "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_health_checks(self):
        """Test that all services are healthy."""
        services = [
            ("API", "http://localhost:8000/health"),
            ("ASR", "http://localhost:8001/health"),
            ("LLM", "http://localhost:8002/health"),
            ("TTS", "http://localhost:8003/health"),
            ("Sardaukar", "http://localhost:8004/api/health"),
        ]

        async with httpx.AsyncClient() as client:
            for service_name, url in services:
                try:
                    response = await client.get(url, timeout=10.0)
                    assert (
                        response.status_code == 200
                    ), f"{service_name} service unhealthy"
                    data = response.json()
                    assert (
                        data.get("status") == "healthy"
                    ), f"{service_name} reports unhealthy status"
                except httpx.RequestError as e:
                    pytest.fail(f"{service_name} service not reachable: {e}")

    @pytest.mark.asyncio
    async def test_text_query_pipeline(self):
        """Test the complete text query pipeline."""
        async with httpx.AsyncClient() as client:
            # Send a text query
            query_data = {
                "text": "What is artificial intelligence?",
                "user_id": "test-user-integration",
                "input_type": "text",
                "generate_speech": False,
                "use_sardaukar": False,
            }

            response = await client.post(
                f"{self.BASE_URL}/query", json=query_data, timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "query_id" in data
            assert "response_id" in data
            assert "text" in data
            assert len(data["text"]) > 0

            # Verify the query was stored
            history_response = await client.get(
                f"{self.BASE_URL}/history/test-user-integration?limit=1"
            )

            assert history_response.status_code == 200
            history_data = history_response.json()
            assert len(history_data["history"]) >= 1

    @pytest.mark.asyncio
    async def test_speech_synthesis_pipeline(self):
        """Test the speech synthesis pipeline."""
        async with httpx.AsyncClient() as client:
            # Send a query with speech generation
            query_data = {
                "text": "Hello, this is a test.",
                "user_id": "test-user-speech",
                "input_type": "text",
                "generate_speech": True,
                "use_sardaukar": False,
            }

            response = await client.post(
                f"{self.BASE_URL}/query", json=query_data, timeout=30.0
            )

            assert response.status_code == 200
            data = response.json()

            # Verify audio URL is provided
            assert "audio_url" in data
            assert data["audio_url"] is not None

    @pytest.mark.asyncio
    async def test_sardaukar_translation_pipeline(self):
        """Test the Sardaukar translation pipeline."""
        async with httpx.AsyncClient() as client:
            # First test direct translation
            translation_data = {
                "text": "Hello, how are you?",
                "include_phonetics": False,
            }

            response = await client.post(
                "http://localhost:8004/api/translate",
                json=translation_data,
                timeout=10.0,
            )

            assert response.status_code == 200
            data = response.json()
            assert "sardaukar" in data
            assert len(data["sardaukar"]) > 0

            # Now test through the TTS service
            tts_data = {"text": "Hello, how are you?", "use_sardaukar": True}

            response = await client.post(
                "http://localhost:8003/synthesize", json=tts_data, timeout=20.0
            )

            assert response.status_code == 200
            data = response.json()
            assert data["used_sardaukar"] == True
            assert data["final_text"] != data["original_text"]

    @pytest.mark.asyncio
    async def test_search_functionality(self):
        """Test the search functionality."""
        async with httpx.AsyncClient() as client:
            # First, add some content by making queries
            queries = [
                "What is machine learning?",
                "Explain neural networks",
                "How does deep learning work?",
            ]

            for query in queries:
                await client.post(
                    f"{self.BASE_URL}/query",
                    json={
                        "text": query,
                        "user_id": "test-search-user",
                        "generate_speech": False,
                    },
                    timeout=30.0,
                )
                # Small delay to ensure queries are processed
                await asyncio.sleep(1)

            # Now search for related content
            response = await client.get(
                f"{self.BASE_URL}/search?query=machine learning&limit=5"
            )

            assert response.status_code == 200
            data = response.json()
            assert "results" in data

    @pytest.mark.asyncio
    async def test_metrics_endpoints(self):
        """Test that metrics endpoints are accessible."""
        metrics_urls = [
            "http://localhost:8080/metrics",  # API metrics (if monitoring enabled)
            "http://localhost:8081/metrics",  # ASR metrics
            "http://localhost:8082/metrics",  # LLM metrics
            "http://localhost:8083/metrics",  # TTS metrics
        ]

        async with httpx.AsyncClient() as client:
            for url in metrics_urls:
                try:
                    response = await client.get(url, timeout=5.0)
                    # Metrics endpoints might return 404 if monitoring is disabled
                    # or 200 with prometheus format
                    assert response.status_code in [200, 404]
                except httpx.RequestError:
                    # Metrics endpoints might not be available in lightweight mode
                    pass

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in the pipeline."""
        async with httpx.AsyncClient() as client:
            # Test invalid query
            response = await client.post(
                f"{self.BASE_URL}/query", json={"invalid": "data"}, timeout=10.0
            )

            assert response.status_code == 422  # Validation error

            # Test non-existent endpoint
            response = await client.get(f"{self.BASE_URL}/nonexistent", timeout=10.0)

            assert response.status_code == 404


class TestPerformance:
    """Performance tests for the system."""

    BASE_URL = "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_concurrent_queries(self):
        """Test handling of concurrent queries."""
        async with httpx.AsyncClient() as client:
            # Create multiple concurrent queries
            tasks = []
            for i in range(5):
                task = client.post(
                    f"{self.BASE_URL}/query",
                    json={
                        "text": f"Test query number {i}",
                        "user_id": f"concurrent-user-{i}",
                        "generate_speech": False,
                    },
                    timeout=30.0,
                )
                tasks.append(task)

            # Execute all queries concurrently
            start_time = time.time()
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            # Verify all requests succeeded
            for response in responses:
                if isinstance(response, Exception):
                    pytest.fail(f"Concurrent request failed: {response}")
                assert response.status_code == 200

            # Verify reasonable response time
            total_time = end_time - start_time
            assert total_time < 60.0, f"Concurrent queries took too long: {total_time}s"

    @pytest.mark.asyncio
    async def test_response_time_benchmarks(self):
        """Test response time benchmarks."""
        async with httpx.AsyncClient() as client:
            # Test simple query response time
            start_time = time.time()

            response = await client.post(
                f"{self.BASE_URL}/query",
                json={
                    "text": "What is the capital of France?",
                    "user_id": "benchmark-user",
                    "generate_speech": False,
                },
                timeout=30.0,
            )

            end_time = time.time()
            response_time = end_time - start_time

            assert response.status_code == 200
            # Response should be under 10 seconds for simple queries
            assert response_time < 10.0, f"Query took too long: {response_time}s"
