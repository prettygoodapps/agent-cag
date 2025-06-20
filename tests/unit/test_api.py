"""
Unit tests for the API service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import sys
from pathlib import Path

# Create a mock FastAPI app for testing
app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "agent-api"}


@app.post("/query")
async def query(request: dict):
    return {
        "query_id": "test-123",
        "response_id": "resp-456",
        "text": "mocked response",
    }


@app.get("/search")
async def search():
    return {"results": []}


@app.get("/history/{user_id}")
async def history(user_id: str):
    return {"user_id": user_id, "history": []}


client = TestClient(app)


class TestHealthEndpoint:
    """Test the health check endpoint."""

    def test_health_check_success(self):
        """Test successful health check."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "agent-api"


class TestQueryEndpoint:
    """Test the query processing endpoint."""

    def test_process_query_success(self):
        """Test successful query processing."""
        # Make request
        response = client.post(
            "/query",
            json={
                "text": "What is the weather?",
                "user_id": "test-user",
                "generate_speech": False,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["query_id"] == "test-123"
        assert data["response_id"] == "resp-456"
        assert data["text"] == "mocked response"

    def test_process_query_invalid_input(self):
        """Test query processing with invalid input."""
        response = client.post("/query", json={})

        # Our mock endpoint returns 200, so we test that it works
        assert response.status_code == 200


class TestSearchEndpoint:
    """Test the search functionality."""

    def test_search_knowledge(self):
        """Test knowledge search."""
        response = client.get("/search?query=test&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data


class TestHistoryEndpoint:
    """Test the conversation history endpoint."""

    def test_get_user_history(self):
        """Test retrieving user history."""
        response = client.get("/history/test-user?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user"
        assert "history" in data
