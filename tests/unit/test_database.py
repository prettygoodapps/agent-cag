"""
Unit tests for the database abstraction layer.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

# Mock dependencies before importing
with patch('api.database.duckdb'), \
     patch('api.database.chromadb', create=True), \
     patch('api.database.neo4j', create=True):
    from api.database import DatabaseManager, DuckDBBackend, FullStackBackend
    from api.models import ConversationEntry, SearchResult


class TestDatabaseManager:
    """Test the database manager."""
    
    def test_manager_lightweight_profile(self):
        """Test manager initialization with lightweight profile."""
        manager = DatabaseManager("lightweight")
        
        assert isinstance(manager.backend, DuckDBBackend)
        assert manager.deployment_profile == "lightweight"

    def test_manager_full_profile(self):
        """Test manager initialization with full profile."""
        manager = DatabaseManager("full")
        
        assert isinstance(manager.backend, FullStackBackend)
        assert manager.deployment_profile == "full"

    def test_manager_invalid_profile(self):
        """Test manager initialization with invalid profile."""
        with pytest.raises(ValueError, match="Unknown deployment profile"):
            DatabaseManager("invalid")

    @pytest.mark.asyncio
    async def test_manager_delegates_to_backend(self):
        """Test that manager delegates calls to backend."""
        mock_backend = MagicMock()
        mock_backend.initialize = AsyncMock()
        mock_backend.close = AsyncMock()
        mock_backend.health_check = AsyncMock()
        mock_backend.store_query = AsyncMock(return_value="query-123")
        mock_backend.store_response = AsyncMock(return_value="response-456")
        mock_backend.get_user_history = AsyncMock(return_value=[])
        mock_backend.search_similar = AsyncMock(return_value=[])
        
        manager = DatabaseManager("lightweight")
        manager.backend = mock_backend
        
        # Test all delegated methods
        await manager.initialize()
        await manager.close()
        await manager.health_check()
        
        query_id = await manager.store_query("test", "user", "text")
        response_id = await manager.store_response("query-123", "response", {})
        history = await manager.get_user_history("user", 10)
        results = await manager.search_similar("query", 5)
        
        # Verify all calls were delegated
        mock_backend.initialize.assert_called_once()
        mock_backend.close.assert_called_once()
        mock_backend.health_check.assert_called_once()
        mock_backend.store_query.assert_called_once_with("test", "user", "text")
        mock_backend.store_response.assert_called_once_with("query-123", "response", {})
        mock_backend.get_user_history.assert_called_once_with("user", 10)
        mock_backend.search_similar.assert_called_once_with("query", 5)
        
        assert query_id == "query-123"
        assert response_id == "response-456"
        assert history == []
        assert results == []


class TestDuckDBBackend:
    """Test the DuckDB backend."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
            yield temp_file.name
            # Cleanup
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    @pytest.mark.asyncio
    async def test_duckdb_initialization(self, temp_db_path):
        """Test DuckDB backend initialization."""
        with patch('api.database.duckdb.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            
            backend = DuckDBBackend(temp_db_path)
            await backend.initialize()
            
            mock_connect.assert_called_once_with(temp_db_path)
            # Verify table creation calls
            assert mock_conn.execute.call_count >= 5  # At least 5 tables

    @pytest.mark.asyncio
    async def test_duckdb_health_check_success(self):
        """Test successful DuckDB health check."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = [1]
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        await backend.health_check()  # Should not raise
        
        mock_conn.execute.assert_called_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_duckdb_health_check_no_connection(self):
        """Test DuckDB health check without connection."""
        backend = DuckDBBackend()
        backend.conn = None
        
        with pytest.raises(Exception, match="Database not initialized"):
            await backend.health_check()

    @pytest.mark.asyncio
    async def test_duckdb_health_check_failure(self):
        """Test DuckDB health check failure."""
        mock_conn = MagicMock()
        mock_conn.execute.return_value.fetchone.return_value = [0]  # Wrong result
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        with pytest.raises(Exception, match="Database health check failed"):
            await backend.health_check()

    @pytest.mark.asyncio
    async def test_duckdb_store_query(self):
        """Test storing a query in DuckDB."""
        mock_conn = MagicMock()
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        query_id = await backend.store_query("What is AI?", "user123", "text")
        
        assert isinstance(query_id, str)
        assert len(query_id) > 0
        
        # Verify user and query insertion
        assert mock_conn.execute.call_count == 2
        calls = mock_conn.execute.call_args_list
        
        # First call should be user insertion
        assert "INSERT OR IGNORE INTO users" in calls[0][0][0]
        # Second call should be query insertion
        assert "INSERT INTO queries" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_duckdb_store_response(self):
        """Test storing a response in DuckDB."""
        mock_conn = MagicMock()
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        response_id = await backend.store_response(
            "query-123", 
            "AI is artificial intelligence", 
            {"tokens": 100}
        )
        
        assert isinstance(response_id, str)
        assert len(response_id) > 0
        
        # Verify response and relationship insertion
        assert mock_conn.execute.call_count == 2
        calls = mock_conn.execute.call_args_list
        
        # First call should be response insertion
        assert "INSERT INTO responses" in calls[0][0][0]
        # Second call should be relationship insertion
        assert "INSERT INTO relationships" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_duckdb_get_user_history(self):
        """Test getting user history from DuckDB."""
        mock_conn = MagicMock()
        mock_result = [
            ("q1", "r1", "What is AI?", "AI is...", datetime.now(), "text"),
            ("q2", "r2", "How does ML work?", "ML works...", datetime.now(), "text")
        ]
        mock_conn.execute.return_value.fetchall.return_value = mock_result
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        history = await backend.get_user_history("user123", 10)
        
        assert len(history) == 2
        assert all(isinstance(entry, ConversationEntry) for entry in history)
        assert history[0].query_id == "q1"
        assert history[0].query_text == "What is AI?"

    @pytest.mark.asyncio
    async def test_duckdb_search_similar(self):
        """Test searching similar content in DuckDB."""
        mock_conn = MagicMock()
        mock_result = [
            ("r1", "AI is artificial intelligence", 1.0),
            ("r2", "Machine learning is a subset of AI", 0.8)
        ]
        mock_conn.execute.return_value.fetchall.return_value = mock_result
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        results = await backend.search_similar("artificial intelligence", 5)
        
        assert len(results) == 2
        assert all(isinstance(result, SearchResult) for result in results)
        assert results[0].id == "r1"
        assert results[0].score == 1.0

    @pytest.mark.asyncio
    async def test_duckdb_close(self):
        """Test closing DuckDB connection."""
        mock_conn = MagicMock()
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        await backend.close()
        
        mock_conn.close.assert_called_once()


class TestFullStackBackend:
    """Test the full stack backend."""
    
    @pytest.mark.asyncio
    async def test_fullstack_initialization_success(self):
        """Test successful full stack backend initialization."""
        mock_chroma_client = MagicMock()
        mock_neo4j_driver = MagicMock()
        mock_session = MagicMock()
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        mock_neo4j_driver.session.return_value.__exit__.return_value = None
        
        with patch('api.database.chromadb.HttpClient', return_value=mock_chroma_client), \
             patch('api.database.GraphDatabase.driver', return_value=mock_neo4j_driver), \
             patch.dict('os.environ', {
                 'CHROMA_HOST': 'localhost',
                 'CHROMA_PORT': '8005',
                 'NEO4J_URI': 'bolt://localhost:7687',
                 'NEO4J_USER': 'neo4j',
                 'NEO4J_PASSWORD': 'password'
             }):
            
            backend = FullStackBackend()
            await backend.initialize()
            
            assert backend.chroma_client == mock_chroma_client
            assert backend.neo4j_driver == mock_neo4j_driver

    @pytest.mark.asyncio
    async def test_fullstack_initialization_import_error(self):
        """Test full stack backend initialization with missing dependencies."""
        with patch('api.database.chromadb', side_effect=ImportError("chromadb not found")):
            backend = FullStackBackend()
            
            with pytest.raises(ImportError):
                await backend.initialize()

    @pytest.mark.asyncio
    async def test_fullstack_health_check_success(self):
        """Test successful full stack health check."""
        mock_chroma_client = MagicMock()
        mock_neo4j_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.return_value.single.return_value = [1]
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        mock_neo4j_driver.session.return_value.__exit__.return_value = None
        
        backend = FullStackBackend()
        backend.chroma_client = mock_chroma_client
        backend.neo4j_driver = mock_neo4j_driver
        
        await backend.health_check()  # Should not raise

    @pytest.mark.asyncio
    async def test_fullstack_health_check_chroma_not_initialized(self):
        """Test full stack health check with ChromaDB not initialized."""
        backend = FullStackBackend()
        backend.chroma_client = None
        backend.neo4j_driver = MagicMock()
        
        with pytest.raises(Exception, match="ChromaDB not initialized"):
            await backend.health_check()

    @pytest.mark.asyncio
    async def test_fullstack_health_check_neo4j_not_initialized(self):
        """Test full stack health check with Neo4j not initialized."""
        backend = FullStackBackend()
        backend.chroma_client = MagicMock()
        backend.neo4j_driver = None
        
        with pytest.raises(Exception, match="Neo4j not initialized"):
            await backend.health_check()

    @pytest.mark.asyncio
    async def test_fullstack_store_query(self):
        """Test storing a query in Neo4j."""
        mock_neo4j_driver = MagicMock()
        mock_session = MagicMock()
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        mock_neo4j_driver.session.return_value.__exit__.return_value = None
        
        backend = FullStackBackend()
        backend.neo4j_driver = mock_neo4j_driver
        
        query_id = await backend.store_query("What is AI?", "user123", "text")
        
        assert isinstance(query_id, str)
        assert len(query_id) > 0
        
        # Verify Neo4j query execution
        mock_session.run.assert_called_once()
        cypher_query = mock_session.run.call_args[0][0]
        assert "MERGE (u:User" in cypher_query
        assert "CREATE (q:Query" in cypher_query

    @pytest.mark.asyncio
    async def test_fullstack_store_response(self):
        """Test storing a response in Neo4j."""
        mock_neo4j_driver = MagicMock()
        mock_session = MagicMock()
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        mock_neo4j_driver.session.return_value.__exit__.return_value = None
        
        backend = FullStackBackend()
        backend.neo4j_driver = mock_neo4j_driver
        
        response_id = await backend.store_response(
            "query-123", 
            "AI is artificial intelligence", 
            {"tokens": 100}
        )
        
        assert isinstance(response_id, str)
        assert len(response_id) > 0
        
        # Verify Neo4j query execution
        mock_session.run.assert_called_once()
        cypher_query = mock_session.run.call_args[0][0]
        assert "MATCH (q:Query" in cypher_query
        assert "CREATE (r:Response" in cypher_query

    @pytest.mark.asyncio
    async def test_fullstack_get_user_history(self):
        """Test getting user history from Neo4j."""
        mock_neo4j_driver = MagicMock()
        mock_session = MagicMock()
        mock_record1 = {
            "q.id": "q1", "r.id": "r1", "q.text": "What is AI?", 
            "r.text": "AI is...", "q.created_at": datetime.now(), "q.input_type": "text"
        }
        mock_record2 = {
            "q.id": "q2", "r.id": "r2", "q.text": "How does ML work?", 
            "r.text": "ML works...", "q.created_at": datetime.now(), "q.input_type": "text"
        }
        mock_session.run.return_value = [mock_record1, mock_record2]
        mock_neo4j_driver.session.return_value.__enter__.return_value = mock_session
        mock_neo4j_driver.session.return_value.__exit__.return_value = None
        
        backend = FullStackBackend()
        backend.neo4j_driver = mock_neo4j_driver
        
        history = await backend.get_user_history("user123", 10)
        
        assert len(history) == 2
        assert all(isinstance(entry, ConversationEntry) for entry in history)
        assert history[0].query_id == "q1"

    @pytest.mark.asyncio
    async def test_fullstack_search_similar(self):
        """Test searching similar content in ChromaDB."""
        mock_chroma_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["AI is artificial intelligence", "Machine learning is a subset of AI"]],
            "ids": [["r1", "r2"]],
            "distances": [[0.1, 0.3]]
        }
        mock_chroma_client.get_collection.return_value = mock_collection
        
        backend = FullStackBackend()
        backend.chroma_client = mock_chroma_client
        
        results = await backend.search_similar("artificial intelligence", 5)
        
        assert len(results) == 2
        assert all(isinstance(result, SearchResult) for result in results)
        assert results[0].id == "r1"
        assert results[0].score == 0.9  # 1.0 - 0.1

    @pytest.mark.asyncio
    async def test_fullstack_close(self):
        """Test closing full stack backend connections."""
        mock_neo4j_driver = MagicMock()
        
        backend = FullStackBackend()
        backend.neo4j_driver = mock_neo4j_driver
        
        await backend.close()
        
        mock_neo4j_driver.close.assert_called_once()


class TestDatabaseErrorHandling:
    """Test database error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_duckdb_connection_error(self):
        """Test DuckDB connection error handling."""
        with patch('api.database.duckdb.connect', side_effect=Exception("Connection failed")):
            backend = DuckDBBackend()
            
            with pytest.raises(Exception):
                await backend.initialize()

    @pytest.mark.asyncio
    async def test_duckdb_query_execution_error(self):
        """Test DuckDB query execution error handling."""
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = Exception("SQL error")
        
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        with pytest.raises(Exception):
            await backend.store_query("test", "user", "text")

    @pytest.mark.asyncio
    async def test_fullstack_neo4j_connection_error(self):
        """Test Neo4j connection error in full stack backend."""
        with patch('api.database.GraphDatabase.driver', side_effect=Exception("Neo4j connection failed")):
            backend = FullStackBackend()
            
            with pytest.raises(Exception):
                await backend.initialize()

    @pytest.mark.asyncio
    async def test_fullstack_chroma_connection_error(self):
        """Test ChromaDB connection error in full stack backend."""
        with patch('api.database.chromadb.HttpClient', side_effect=Exception("ChromaDB connection failed")):
            backend = FullStackBackend()
            
            with pytest.raises(Exception):
                await backend.initialize()


class TestDatabaseConcurrency:
    """Test database concurrency scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_query_storage(self):
        """Test concurrent query storage."""
        import asyncio
        
        mock_conn = MagicMock()
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        # Simulate concurrent query storage
        tasks = [
            backend.store_query(f"Query {i}", f"user{i}", "text")
            for i in range(5)
        ]
        
        query_ids = await asyncio.gather(*tasks)
        
        assert len(query_ids) == 5
        assert all(isinstance(qid, str) for qid in query_ids)
        assert len(set(query_ids)) == 5  # All unique

    @pytest.mark.asyncio
    async def test_concurrent_response_storage(self):
        """Test concurrent response storage."""
        import asyncio
        
        mock_conn = MagicMock()
        backend = DuckDBBackend()
        backend.conn = mock_conn
        
        # Simulate concurrent response storage
        tasks = [
            backend.store_response(f"query-{i}", f"Response {i}", {"index": i})
            for i in range(5)
        ]
        
        response_ids = await asyncio.gather(*tasks)
        
        assert len(response_ids) == 5
        assert all(isinstance(rid, str) for rid in response_ids)
        assert len(set(response_ids)) == 5  # All unique