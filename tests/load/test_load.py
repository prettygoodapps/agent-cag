"""
Load testing for the Agent CAG system using locust.
"""

import time
import json
import random
from locust import HttpUser, task, between
from locust.exception import StopUser


class AgentCAGUser(HttpUser):
    """Simulated user for load testing Agent CAG system."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Initialize user session."""
        self.user_id = f"load_test_user_{random.randint(1000, 9999)}"
        self.query_count = 0
        
        # Test data for various scenarios
        self.text_queries = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "Explain neural networks",
            "What are the benefits of AI?",
            "How can I learn programming?",
            "What is the weather like today?",
            "Tell me a joke",
            "What is the meaning of life?",
            "How do computers work?",
            "What is quantum computing?"
        ]
        
        self.complex_queries = [
            "Explain the differences between supervised, unsupervised, and reinforcement learning in machine learning, and provide examples of when each would be most appropriate to use.",
            "What are the ethical implications of artificial intelligence in healthcare, and how can we ensure AI systems are fair and unbiased?",
            "Describe the architecture of a transformer model and explain how attention mechanisms work in natural language processing.",
            "How do convolutional neural networks process images, and what are the key components like pooling layers and activation functions?",
            "What is the difference between strong AI and weak AI, and what are the current limitations preventing us from achieving artificial general intelligence?"
        ]
    
    @task(10)
    def query_text(self):
        """Test text query endpoint - most common operation."""
        query_text = random.choice(self.text_queries)
        
        response = self.client.post(
            "/query",
            json={
                "text": query_text,
                "user_id": self.user_id,
                "input_type": "text"
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            self.query_count += 1
            response.success()
        elif response.status_code in [400, 422]:
            # Client errors are expected for some test cases
            response.success()
        else:
            response.failure(f"Unexpected status code: {response.status_code}")
    
    @task(3)
    def query_complex(self):
        """Test complex query handling."""
        query_text = random.choice(self.complex_queries)
        
        response = self.client.post(
            "/query",
            json={
                "text": query_text,
                "user_id": self.user_id,
                "input_type": "text"
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            self.query_count += 1
            response.success()
        elif response.status_code in [400, 422]:
            response.success()
        else:
            response.failure(f"Complex query failed: {response.status_code}")
    
    @task(2)
    def get_history(self):
        """Test history retrieval."""
        if self.query_count > 0:  # Only if user has made queries
            response = self.client.get(
                f"/history/{self.user_id}",
                catch_response=True
            )
            
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"History retrieval failed: {response.status_code}")
    
    @task(1)
    def search_similar(self):
        """Test similarity search."""
        search_query = random.choice(self.text_queries[:5])  # Use shorter queries for search
        
        response = self.client.get(
            f"/search",
            params={"q": search_query, "limit": 5},
            catch_response=True
        )
        
        if response.status_code in [200, 404]:
            response.success()
        else:
            response.failure(f"Search failed: {response.status_code}")
    
    @task(1)
    def health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/health", catch_response=True)
        
        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Health check failed: {response.status_code}")
    
    @task(1)
    def metrics_check(self):
        """Test metrics endpoint."""
        response = self.client.get("/metrics", catch_response=True)
        
        if response.status_code == 200:
            response.success()
        else:
            response.failure(f"Metrics check failed: {response.status_code}")


class HeavyUser(HttpUser):
    """Heavy user simulation for stress testing."""
    
    wait_time = between(0.1, 1)  # Very short wait times
    
    def on_start(self):
        """Initialize heavy user session."""
        self.user_id = f"heavy_user_{random.randint(1000, 9999)}"
        self.request_count = 0
    
    @task
    def rapid_queries(self):
        """Make rapid queries to stress test the system."""
        query_text = f"Stress test query {self.request_count}"
        
        response = self.client.post(
            "/query",
            json={
                "text": query_text,
                "user_id": self.user_id,
                "input_type": "text"
            },
            catch_response=True
        )
        
        self.request_count += 1
        
        if response.status_code in [200, 400, 422, 429, 503]:
            # Accept rate limiting and service unavailable as success
            response.success()
        else:
            response.failure(f"Stress test failed: {response.status_code}")
        
        # Stop after 100 requests to prevent infinite load
        if self.request_count >= 100:
            raise StopUser()


class AudioUser(HttpUser):
    """User simulation for audio processing endpoints."""
    
    wait_time = between(2, 8)  # Longer wait for audio processing
    
    def on_start(self):
        """Initialize audio user session."""
        self.user_id = f"audio_user_{random.randint(1000, 9999)}"
        
        # Create dummy audio data for testing
        self.audio_data = b"RIFF" + b"\x00" * 44 + b"dummy audio data" * 100
    
    @task(5)
    def upload_audio(self):
        """Test audio upload and processing."""
        files = {
            "audio": ("test_audio.wav", self.audio_data, "audio/wav")
        }
        data = {
            "user_id": self.user_id
        }
        
        response = self.client.post(
            "/query",
            files=files,
            data=data,
            catch_response=True
        )
        
        if response.status_code in [200, 400, 422]:
            response.success()
        else:
            response.failure(f"Audio upload failed: {response.status_code}")
    
    @task(1)
    def tts_request(self):
        """Test text-to-speech functionality."""
        response = self.client.post(
            "/query",
            json={
                "text": "Convert this text to speech",
                "user_id": self.user_id,
                "input_type": "text",
                "output_format": "audio"
            },
            catch_response=True
        )
        
        if response.status_code in [200, 400, 422]:
            response.success()
        else:
            response.failure(f"TTS request failed: {response.status_code}")


class DatabaseStressUser(HttpUser):
    """User simulation for database stress testing."""
    
    wait_time = between(0.5, 2)
    
    def on_start(self):
        """Initialize database stress user."""
        self.user_id = f"db_stress_user_{random.randint(1000, 9999)}"
        self.queries_made = []
    
    @task(8)
    def create_data(self):
        """Create data to stress database."""
        query_text = f"Database stress test query {len(self.queries_made)} - {random.randint(1, 1000000)}"
        
        response = self.client.post(
            "/query",
            json={
                "text": query_text,
                "user_id": self.user_id,
                "input_type": "text"
            },
            catch_response=True
        )
        
        if response.status_code == 200:
            self.queries_made.append(query_text)
            response.success()
        elif response.status_code in [400, 422]:
            response.success()
        else:
            response.failure(f"Data creation failed: {response.status_code}")
    
    @task(3)
    def read_history(self):
        """Read user history to stress database reads."""
        if self.queries_made:
            response = self.client.get(
                f"/history/{self.user_id}",
                params={"limit": random.randint(5, 20)},
                catch_response=True
            )
            
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"History read failed: {response.status_code}")
    
    @task(2)
    def search_data(self):
        """Search data to stress database queries."""
        if self.queries_made:
            search_term = random.choice(self.queries_made).split()[0]
            
            response = self.client.get(
                "/search",
                params={"q": search_term, "limit": random.randint(3, 10)},
                catch_response=True
            )
            
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")


class ErrorGeneratingUser(HttpUser):
    """User that generates various error conditions for testing."""
    
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize error generating user."""
        self.user_id = f"error_user_{random.randint(1000, 9999)}"
    
    @task(3)
    def invalid_json(self):
        """Send invalid JSON to test error handling."""
        invalid_data = '{"text": "test", "user_id": "test", invalid}'
        
        response = self.client.post(
            "/query",
            data=invalid_data,
            headers={"Content-Type": "application/json"},
            catch_response=True
        )
        
        if response.status_code == 422:  # Expected error
            response.success()
        else:
            response.failure(f"Invalid JSON handling failed: {response.status_code}")
    
    @task(2)
    def missing_fields(self):
        """Send requests with missing required fields."""
        incomplete_data = {"text": "test query"}  # Missing user_id
        
        response = self.client.post(
            "/query",
            json=incomplete_data,
            catch_response=True
        )
        
        if response.status_code == 422:  # Expected validation error
            response.success()
        else:
            response.failure(f"Missing fields handling failed: {response.status_code}")
    
    @task(2)
    def large_payload(self):
        """Send very large payloads."""
        large_text = "A" * 50000  # 50KB text
        
        response = self.client.post(
            "/query",
            json={
                "text": large_text,
                "user_id": self.user_id,
                "input_type": "text"
            },
            catch_response=True
        )
        
        if response.status_code in [200, 400, 413, 422]:
            response.success()
        else:
            response.failure(f"Large payload handling failed: {response.status_code}")
    
    @task(1)
    def nonexistent_endpoints(self):
        """Access nonexistent endpoints."""
        endpoints = ["/nonexistent", "/api/v2/query", "/admin", "/debug"]
        endpoint = random.choice(endpoints)
        
        response = self.client.get(endpoint, catch_response=True)
        
        if response.status_code == 404:  # Expected error
            response.success()
        else:
            response.failure(f"404 handling failed for {endpoint}: {response.status_code}")


class ConcurrentUser(HttpUser):
    """User for testing concurrent access patterns."""
    
    wait_time = between(0.1, 0.5)  # Very fast requests
    
    def on_start(self):
        """Initialize concurrent user."""
        self.user_id = f"concurrent_user_{random.randint(1000, 9999)}"
        self.shared_resource_id = "shared_resource_123"
    
    @task(5)
    def concurrent_queries(self):
        """Make concurrent queries that might access shared resources."""
        response = self.client.post(
            "/query",
            json={
                "text": f"Concurrent access test for {self.shared_resource_id}",
                "user_id": self.user_id,
                "input_type": "text"
            },
            catch_response=True
        )
        
        if response.status_code in [200, 400, 422, 429]:
            response.success()
        else:
            response.failure(f"Concurrent query failed: {response.status_code}")
    
    @task(2)
    def concurrent_history_access(self):
        """Access history concurrently."""
        response = self.client.get(
            f"/history/{self.shared_resource_id}",
            catch_response=True
        )
        
        if response.status_code in [200, 404, 429]:
            response.success()
        else:
            response.failure(f"Concurrent history access failed: {response.status_code}")


# Custom load test scenarios
class LoadTestScenarios:
    """Custom load test scenarios for specific testing needs."""
    
    @staticmethod
    def run_spike_test():
        """Simulate sudden traffic spike."""
        # This would be implemented as a custom locust test
        pass
    
    @staticmethod
    def run_endurance_test():
        """Run long-duration endurance test."""
        # This would be implemented as a custom locust test
        pass
    
    @staticmethod
    def run_capacity_test():
        """Test system capacity limits."""
        # This would be implemented as a custom locust test
        pass


# Load test configuration
if __name__ == "__main__":
    """
    Run load tests with different user classes:
    
    # Basic load test
    locust -f tests/load/test_load.py --users 10 --spawn-rate 2 --host http://localhost:8000
    
    # Heavy load test
    locust -f tests/load/test_load.py --users 50 --spawn-rate 5 --host http://localhost:8000 HeavyUser
    
    # Audio processing test
    locust -f tests/load/test_load.py --users 5 --spawn-rate 1 --host http://localhost:8000 AudioUser
    
    # Database stress test
    locust -f tests/load/test_load.py --users 20 --spawn-rate 3 --host http://localhost:8000 DatabaseStressUser
    
    # Error handling test
    locust -f tests/load/test_load.py --users 10 --spawn-rate 2 --host http://localhost:8000 ErrorGeneratingUser
    
    # Concurrent access test
    locust -f tests/load/test_load.py --users 30 --spawn-rate 10 --host http://localhost:8000 ConcurrentUser
    """
    print("Load test configuration loaded. Use locust command to run tests.")
    print("Example: locust -f tests/load/test_load.py --users 10 --spawn-rate 2 --host http://localhost:8000")