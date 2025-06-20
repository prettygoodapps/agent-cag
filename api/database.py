"""
Database abstraction layer for Agent CAG.

Supports both lightweight (DuckDB) and full (ChromaDB + Neo4j) deployment profiles.
"""

import os
import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

import duckdb
from models import ConversationEntry, SearchResult

logger = logging.getLogger(__name__)


class DatabaseBackend(ABC):
    """Abstract base class for database backends."""

    @abstractmethod
    async def initialize(self):
        """Initialize the database backend."""
        pass

    @abstractmethod
    async def close(self):
        """Close database connections."""
        pass

    @abstractmethod
    async def health_check(self):
        """Check database health."""
        pass

    @abstractmethod
    async def store_query(self, text: str, user_id: str, input_type: str) -> str:
        """Store a user query and return query ID."""
        pass

    @abstractmethod
    async def store_response(
        self, query_id: str, text: str, metadata: Dict[str, Any]
    ) -> str:
        """Store a response and return response ID."""
        pass

    @abstractmethod
    async def get_user_history(
        self, user_id: str, limit: int
    ) -> List[ConversationEntry]:
        """Get conversation history for a user."""
        pass

    @abstractmethod
    async def search_similar(self, query: str, limit: int) -> List[SearchResult]:
        """Search for similar content."""
        pass


class DuckDBBackend(DatabaseBackend):
    """DuckDB-based lightweight backend."""

    def __init__(self, db_path: str = "/app/data/agent.db"):
        self.db_path = db_path
        self.conn = None

    async def initialize(self):
        """Initialize DuckDB database."""
        logger.info(f"Initializing DuckDB backend at {self.db_path}")

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        # Connect to DuckDB
        self.conn = duckdb.connect(self.db_path)

        # Create tables
        await self._create_tables()

        logger.info("DuckDB backend initialized successfully")

    async def _create_tables(self):
        """Create necessary tables."""
        # Users table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Queries table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS queries (
                id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                text TEXT,
                input_type VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Responses table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS responses (
                id VARCHAR PRIMARY KEY,
                query_id VARCHAR,
                text TEXT,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (query_id) REFERENCES queries(id)
            )
        """
        )

        # Embeddings table for vector search
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS embeddings (
                id VARCHAR PRIMARY KEY,
                content_id VARCHAR,
                content_type VARCHAR,
                text TEXT,
                embedding FLOAT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Graph relationships table
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relationships (
                id VARCHAR PRIMARY KEY,
                source_id VARCHAR,
                target_id VARCHAR,
                relationship_type VARCHAR,
                properties JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

    async def close(self):
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")

    async def health_check(self):
        """Check DuckDB health."""
        if not self.conn:
            raise Exception("Database not initialized")

        # Simple query to check connection
        result = self.conn.execute("SELECT 1").fetchone()
        if result[0] != 1:
            raise Exception("Database health check failed")

    async def store_query(self, text: str, user_id: str, input_type: str) -> str:
        """Store a user query."""
        query_id = str(uuid.uuid4())

        # Ensure user exists
        self.conn.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", [user_id])

        # Store query
        self.conn.execute(
            "INSERT INTO queries (id, user_id, text, input_type) VALUES (?, ?, ?, ?)",
            [query_id, user_id, text, input_type],
        )

        logger.info(f"Stored query {query_id} for user {user_id}")
        return query_id

    async def store_response(
        self, query_id: str, text: str, metadata: Dict[str, Any]
    ) -> str:
        """Store a response."""
        response_id = str(uuid.uuid4())

        self.conn.execute(
            "INSERT INTO responses (id, query_id, text, metadata) VALUES (?, ?, ?, ?)",
            [response_id, query_id, text, json.dumps(metadata)],
        )

        # Create relationships
        await self._create_relationships(query_id, response_id, text)

        logger.info(f"Stored response {response_id} for query {query_id}")
        return response_id

    async def _create_relationships(
        self, query_id: str, response_id: str, response_text: str
    ):
        """Create graph relationships."""
        # Query -> Response relationship
        rel_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO relationships (id, source_id, target_id, relationship_type) VALUES (?, ?, ?, ?)",
            [rel_id, query_id, response_id, "ANSWERS"],
        )

    async def get_user_history(
        self, user_id: str, limit: int
    ) -> List[ConversationEntry]:
        """Get conversation history for a user."""
        result = self.conn.execute(
            """
            SELECT q.id, r.id, q.text, r.text, q.created_at, q.input_type
            FROM queries q
            JOIN responses r ON q.id = r.query_id
            WHERE q.user_id = ?
            ORDER BY q.created_at DESC
            LIMIT ?
        """,
            [user_id, limit],
        ).fetchall()

        history = []
        for row in result:
            history.append(
                ConversationEntry(
                    query_id=row[0],
                    response_id=row[1],
                    query_text=row[2],
                    response_text=row[3],
                    timestamp=row[4].isoformat(),
                    input_type=row[5],
                )
            )

        return history

    async def search_similar(self, query: str, limit: int) -> List[SearchResult]:
        """Search for similar content using simple text matching."""
        # Simple text search implementation
        # In a real implementation, you would use vector embeddings
        result = self.conn.execute(
            """
            SELECT r.id, r.text, 1.0 as score
            FROM responses r
            WHERE r.text LIKE ?
            ORDER BY score DESC
            LIMIT ?
        """,
            [f"%{query}%", limit],
        ).fetchall()

        results = []
        for row in result:
            results.append(SearchResult(id=row[0], text=row[1], score=row[2]))

        return results


class FullStackBackend(DatabaseBackend):
    """Full stack backend using ChromaDB and Neo4j."""

    def __init__(self):
        self.chroma_client = None
        self.neo4j_driver = None

    async def initialize(self):
        """Initialize ChromaDB and Neo4j connections."""
        logger.info("Initializing full stack backend...")

        try:
            # Initialize ChromaDB
            import chromadb

            chroma_host = os.getenv("CHROMA_HOST", "chroma")
            chroma_port = int(os.getenv("CHROMA_PORT", "8005"))
            self.chroma_client = chromadb.HttpClient(host=chroma_host, port=chroma_port)

            # Initialize Neo4j
            from neo4j import GraphDatabase

            neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
            neo4j_user = os.getenv("NEO4J_USER", "neo4j")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

            self.neo4j_driver = GraphDatabase.driver(
                neo4j_uri, auth=(neo4j_user, neo4j_password)
            )

            # Create collections and constraints
            await self._setup_databases()

            logger.info("Full stack backend initialized successfully")

        except ImportError as e:
            logger.error(f"Missing dependencies for full stack backend: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize full stack backend: {e}")
            raise

    async def _setup_databases(self):
        """Setup ChromaDB collections and Neo4j constraints."""
        # Create ChromaDB collection
        try:
            self.chroma_client.create_collection("agent_embeddings")
        except Exception:
            # Collection might already exist
            pass

        # Create Neo4j constraints
        with self.neo4j_driver.session() as session:
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (q:Query) REQUIRE q.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (r:Response) REQUIRE r.id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE"
            )

    async def close(self):
        """Close database connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
            logger.info("Neo4j connection closed")

    async def health_check(self):
        """Check database health."""
        # Check ChromaDB
        if not self.chroma_client:
            raise Exception("ChromaDB not initialized")

        # Check Neo4j
        if not self.neo4j_driver:
            raise Exception("Neo4j not initialized")

        with self.neo4j_driver.session() as session:
            result = session.run("RETURN 1")
            if not result.single()[0] == 1:
                raise Exception("Neo4j health check failed")

    async def store_query(self, text: str, user_id: str, input_type: str) -> str:
        """Store a user query in Neo4j."""
        query_id = str(uuid.uuid4())

        with self.neo4j_driver.session() as session:
            session.run(
                """
                MERGE (u:User {id: $user_id})
                CREATE (q:Query {
                    id: $query_id,
                    text: $text,
                    input_type: $input_type,
                    created_at: datetime()
                })
                CREATE (u)-[:ASKED]->(q)
            """,
                user_id=user_id,
                query_id=query_id,
                text=text,
                input_type=input_type,
            )

        return query_id

    async def store_response(
        self, query_id: str, text: str, metadata: Dict[str, Any]
    ) -> str:
        """Store a response in Neo4j."""
        response_id = str(uuid.uuid4())

        with self.neo4j_driver.session() as session:
            session.run(
                """
                MATCH (q:Query {id: $query_id})
                CREATE (r:Response {
                    id: $response_id,
                    text: $text,
                    metadata: $metadata,
                    created_at: datetime()
                })
                CREATE (r)-[:ANSWERS]->(q)
            """,
                query_id=query_id,
                response_id=response_id,
                text=text,
                metadata=json.dumps(metadata),
            )

        return response_id

    async def get_user_history(
        self, user_id: str, limit: int
    ) -> List[ConversationEntry]:
        """Get conversation history from Neo4j."""
        with self.neo4j_driver.session() as session:
            result = session.run(
                """
                MATCH (u:User {id: $user_id})-[:ASKED]->(q:Query)<-[:ANSWERS]-(r:Response)
                RETURN q.id, r.id, q.text, r.text, q.created_at, q.input_type
                ORDER BY q.created_at DESC
                LIMIT $limit
            """,
                user_id=user_id,
                limit=limit,
            )

            history = []
            for record in result:
                history.append(
                    ConversationEntry(
                        query_id=record["q.id"],
                        response_id=record["r.id"],
                        query_text=record["q.text"],
                        response_text=record["r.text"],
                        timestamp=record["q.created_at"].isoformat(),
                        input_type=record["q.input_type"],
                    )
                )

            return history

    async def search_similar(self, query: str, limit: int) -> List[SearchResult]:
        """Search for similar content using ChromaDB."""
        collection = self.chroma_client.get_collection("agent_embeddings")

        results = collection.query(query_texts=[query], n_results=limit)

        search_results = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                search_results.append(
                    SearchResult(
                        id=results["ids"][0][i],
                        text=doc,
                        score=1.0
                        - results["distances"][0][i],  # Convert distance to similarity
                    )
                )

        return search_results


class DatabaseManager:
    """Database manager that selects the appropriate backend."""

    def __init__(self, deployment_profile: str):
        self.deployment_profile = deployment_profile

        if deployment_profile == "lightweight":
            self.backend = DuckDBBackend()
        elif deployment_profile == "full":
            self.backend = FullStackBackend()
        else:
            raise ValueError(f"Unknown deployment profile: {deployment_profile}")

    async def initialize(self):
        """Initialize the selected backend."""
        await self.backend.initialize()

    async def close(self):
        """Close the backend."""
        await self.backend.close()

    async def health_check(self):
        """Check backend health."""
        await self.backend.health_check()

    async def store_query(self, text: str, user_id: str, input_type: str) -> str:
        """Store a query."""
        return await self.backend.store_query(text, user_id, input_type)

    async def store_response(
        self, query_id: str, text: str, metadata: Dict[str, Any]
    ) -> str:
        """Store a response."""
        return await self.backend.store_response(query_id, text, metadata)

    async def get_user_history(
        self, user_id: str, limit: int
    ) -> List[ConversationEntry]:
        """Get user history."""
        return await self.backend.get_user_history(user_id, limit)

    async def search_similar(self, query: str, limit: int) -> List[SearchResult]:
        """Search for similar content."""
        return await self.backend.search_similar(query, limit)
