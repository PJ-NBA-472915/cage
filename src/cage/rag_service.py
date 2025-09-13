"""
RAG (Retrieval-Augmented Generation) Service for Cage

This module implements the RAG system with vector embeddings, PostgreSQL with pgvector,
and Redis caching as specified in the Cage specification.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

import asyncpg
import redis.asyncio as redis
import openai
from openai import AsyncOpenAI, AuthenticationError
import numpy as np
from pgvector.asyncpg import register_vector, to_db

logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    path: str
    language: Optional[str] = None
    commit_sha: Optional[str] = None
    branch: Optional[str] = None
    task_id: Optional[str] = None
    chunk_id: int = 0

@dataclass
class SearchResult:
    """Search result from RAG query."""
    content: str
    metadata: ChunkMetadata
    score: float
    blob_sha: str

class RAGService:
    """RAG service implementation with PostgreSQL and Redis."""
    
    def __init__(self, 
                 db_url: str,
                 redis_url: str = "redis://localhost:6379",
                 openai_api_key: Optional[str] = None,
                 embedding_model: str = "text-embedding-3-small"):
        """Initialize RAG service."""
        self.db_url = db_url
        self.redis_url = redis_url
        self.openai_client = AsyncOpenAI(api_key=openai_api_key or os.getenv("OPENAI_API_KEY"))
        self.embedding_model = embedding_model
        self.embedding_dimension = 1536  # text-embedding-3-small dimension
        
        # Connection pools
        self.db_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Initialize database and Redis connections."""
        try:
            # Initialize PostgreSQL connection pool
            self.db_pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            
            # Register pgvector extension
            async with self.db_pool.acquire() as conn:
                await register_vector(conn)
                await self._create_tables()
            
            # Initialize Redis connection
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            
            logger.info("RAG service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise
    
    async def _create_tables(self):
        """Create database tables according to specification."""
        async with self.db_pool.acquire() as conn:
            # Create git_blobs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS git_blobs (
                    blob_sha TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    mime TEXT,
                    first_seen_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Create embeddings table with pgvector
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    blob_sha TEXT REFERENCES git_blobs(blob_sha) ON DELETE CASCADE,
                    chunk_id INTEGER NOT NULL,
                    vector VECTOR(1536) NOT NULL,
                    meta JSONB NOT NULL,
                    PRIMARY KEY (blob_sha, chunk_id)
                )
            """)
            
            # Create blob_paths table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS blob_paths (
                    blob_sha TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (commit_sha, path)
                )
            """)
            
            # Create events table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id BIGSERIAL PRIMARY KEY,
                    type TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    correlation_id TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            # Create index on events type
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)
            """)
            
            # Create crew_runs table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crew_runs (
                    id UUID PRIMARY KEY,
                    task_id TEXT,
                    status TEXT,
                    started_at TIMESTAMPTZ DEFAULT NOW(),
                    completed_at TIMESTAMPTZ
                )
            """)
            
            # Create run_artefacts table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS run_artefacts (
                    id BIGSERIAL PRIMARY KEY,
                    run_id UUID NOT NULL REFERENCES crew_runs(id) ON DELETE CASCADE,
                    key TEXT NOT NULL,
                    content_type TEXT,
                    size BIGINT NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)
            
            logger.info("Database tables created successfully")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed. Please check your API key: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 40) -> List[str]:
        """Chunk text into overlapping segments."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings within the last 100 characters
                search_start = max(start, end - 100)
                sentence_end = text.rfind('.', search_start, end)
                if sentence_end > start:
                    end = sentence_end + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file path."""
        ext = Path(file_path).suffix.lower()
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.go': 'go',
            '.rs': 'rust',
            '.php': 'php',
            '.rb': 'ruby',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.sql': 'sql'
        }
        return language_map.get(ext)
    
    async def index_file(self, file_path: str, content: str, commit_sha: str, branch: str = "main") -> List[str]:
        """Index a file and return blob SHAs."""
        try:
            # Calculate blob SHA
            blob_sha = hashlib.sha256(content.encode('utf-8')).hexdigest()
            
            # Store blob metadata
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO git_blobs (blob_sha, size, mime, first_seen_at)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (blob_sha) DO NOTHING
                """, blob_sha, len(content), self._get_mime_type(file_path), datetime.now())
                
                # Store blob path
                await conn.execute("""
                    INSERT INTO blob_paths (blob_sha, commit_sha, path)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (commit_sha, path) DO UPDATE SET blob_sha = $1
                """, blob_sha, commit_sha, file_path)
            
            # Chunk the content
            language = self._detect_language(file_path)
            if language in ['python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'go', 'rust']:
                chunk_size = 400
            elif language == 'markdown':
                chunk_size = 800
            else:
                chunk_size = 500
            
            chunks = self._chunk_text(content, chunk_size, 40)
            
            # Process each chunk
            chunk_shas = []
            for i, chunk in enumerate(chunks):
                chunk_sha = f"{blob_sha}_{i}"
                chunk_shas.append(chunk_sha)
                
                # Generate embedding
                embedding = await self.generate_embedding(chunk)
                
                # Create metadata
                metadata = ChunkMetadata(
                    path=file_path,
                    language=language,
                    commit_sha=commit_sha,
                    branch=branch,
                    chunk_id=i
                )
                
                # Store embedding
                async with self.db_pool.acquire() as conn:
                    # Convert embedding to numpy array
                    import numpy as np
                    embedding_array = np.array(embedding, dtype=np.float32)
                    
                    await conn.execute("""
                        INSERT INTO embeddings (blob_sha, chunk_id, vector, meta)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (blob_sha, chunk_id) DO UPDATE SET
                            vector = $3,
                            meta = $4
                    """, blob_sha, i, embedding_array, json.dumps(metadata.__dict__))
                
                # Store chunk content in Redis
                if self.redis_client:
                    try:
                        cache_key = f"chunk:{blob_sha}:{i}"
                        await self.redis_client.setex(cache_key, 86400, chunk)  # Cache for 24 hours
                    except Exception as e:
                        logger.warning(f"Failed to cache chunk content for {cache_key}: {e}")
            
            logger.info(f"Indexed file {file_path} with {len(chunks)} chunks")
            return chunk_shas
            
        except Exception as e:
            logger.error(f"Failed to index file {file_path}: {e}")
            raise
    
    def _get_mime_type(self, file_path: str) -> str:
        """Get MIME type for file."""
        ext = Path(file_path).suffix.lower()
        mime_map = {
            '.py': 'text/x-python',
            '.js': 'text/javascript',
            '.ts': 'text/typescript',
            '.md': 'text/markdown',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.yaml': 'text/yaml',
            '.yml': 'text/yaml',
            '.xml': 'text/xml',
            '.html': 'text/html',
            '.css': 'text/css',
            '.sql': 'text/sql'
        }
        return mime_map.get(ext, 'text/plain')
    
    async def query(self, query_text: str, top_k: int = 8, filters: Optional[Dict] = None) -> List[SearchResult]:
        """Query the RAG system."""
        try:
            # Generate query embedding
            query_embedding = await self.generate_embedding(query_text)
            logger.info(f"Generated query embedding with {len(query_embedding)} dimensions")
            
            # Convert to database format - convert to list for pgvector
            import numpy as np
            query_vector = np.array(query_embedding, dtype=np.float32)
            query_list = query_vector.tolist()
            logger.info(f"Converted query vector type: {type(query_list)}")
            logger.info(f"Query vector length: {len(query_list)}")
            
            # Build SQL query with optional filters
            sql = """
                SELECT e.blob_sha, e.chunk_id, e.meta, e.vector,
                       1 - (e.vector <=> $1::vector) as score
                FROM embeddings e
                JOIN git_blobs gb ON e.blob_sha = gb.blob_sha
            """
            params = [query_list]
            param_count = 1
            
            if filters:
                where_conditions = []
                if 'path' in filters:
                    param_count += 1
                    where_conditions.append(f"e.meta->>'path' LIKE ${param_count}")
                    params.append(f"%{filters['path']}%")
                
                if 'language' in filters:
                    param_count += 1
                    where_conditions.append(f"e.meta->>'language' = ${param_count}")
                    params.append(filters['language'])
                
                if 'branch' in filters:
                    param_count += 1
                    where_conditions.append(f"e.meta->>'branch' = ${param_count}")
                    params.append(filters['branch'])
                
                if where_conditions:
                    sql += " WHERE " + " AND ".join(where_conditions)
            
            sql += f" ORDER BY e.vector <=> $1::vector LIMIT {top_k}"
            
            # Execute query
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(sql, *params)
            
            # Convert to SearchResult objects
            results = []
            for row in rows:
                metadata_dict = json.loads(row['meta'])
                metadata = ChunkMetadata(**metadata_dict)
                
                # Get chunk content from Redis cache or regenerate
                cache_key = f"chunk:{row['blob_sha']}:{row['chunk_id']}"
                content = await self._get_chunk_content(row['blob_sha'], row['chunk_id'])
                
                result = SearchResult(
                    content=content,
                    metadata=metadata,
                    score=float(row['score']),
                    blob_sha=row['blob_sha']
                )
                results.append(result)
            
            logger.info(f"RAG query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Failed to query RAG system: {e}")
            raise
    
    async def _get_chunk_content(self, blob_sha: str, chunk_id: int) -> str:
        """Get chunk content from cache or regenerate."""
        cache_key = f"chunk:{blob_sha}:{chunk_id}"
        
        # Try Redis cache first
        if self.redis_client:
            try:
                cached_content = await self.redis_client.get(cache_key)
                if cached_content:
                    return cached_content
            except Exception as e:
                logger.warning(f"Redis cache miss for {cache_key}: {e}")
        
        # Get the original content from the repository
        try:
            # Get file path from database
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT bp.path, e.meta
                    FROM blob_paths bp
                    JOIN embeddings e ON bp.blob_sha = e.blob_sha
                    WHERE bp.blob_sha = $1 AND e.chunk_id = $2
                """, blob_sha, chunk_id)
                
                if row:
                    file_path = row['path']
                    metadata = json.loads(row['meta'])
                    
                    # Read the file content
                    repo_path = Path(os.environ.get('REPO_PATH', '/work/repo'))
                    full_path = repo_path / file_path
                    
                    if full_path.exists():
                        content = full_path.read_text(encoding='utf-8')
                        
                        # Chunk the content the same way as during indexing
                        language = metadata.get('language', 'text')
                        if language in ['python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'go', 'rust']:
                            chunk_size = 400
                        elif language == 'markdown':
                            chunk_size = 800
                        else:
                            chunk_size = 500
                        
                        chunks = self._chunk_text(content, chunk_size, 40)
                        
                        # Return the specific chunk
                        if chunk_id < len(chunks):
                            chunk_content = chunks[chunk_id]
                            
                            # Cache the content for future use
                            if self.redis_client:
                                try:
                                    await self.redis_client.setex(cache_key, 3600, chunk_content)  # Cache for 1 hour
                                except Exception as e:
                                    logger.warning(f"Failed to cache content for {cache_key}: {e}")
                            
                            return chunk_content
                        else:
                            logger.warning(f"Chunk {chunk_id} not found in file {file_path}")
                            return f"Chunk {chunk_id} not found"
                    else:
                        logger.warning(f"File not found: {full_path}")
                        return f"File not found: {file_path}"
                else:
                    logger.warning(f"No metadata found for blob {blob_sha} chunk {chunk_id}")
                    return f"No metadata found for blob {blob_sha[:8]}..."
                    
        except Exception as e:
            logger.error(f"Error retrieving content for {blob_sha}:{chunk_id}: {e}")
            return f"Error retrieving content: {str(e)}"
    
    async def reindex_repository(self, repo_path: Path, scope: str = "all") -> Dict[str, Any]:
        """Reindex repository content."""
        try:
            logger.info(f"DEBUG: Starting reindex of repository at {repo_path} with scope {scope}")
            logger.info(f"DEBUG: Repository path type: {type(repo_path)}")
            logger.info(f"DEBUG: Repository path exists: {repo_path.exists()}")
            
            indexed_files = 0
            total_chunks = 0
            blob_shas = []
            
            logger.info(f"Starting reindex of repository at {repo_path} with scope {scope}")
            
            if scope in ["all", "repo"]:
                # Index code files
                logger.info(f"Scanning for files in {repo_path}")
                files_found = 0
                files_skipped = 0
                for file_path in repo_path.rglob("*"):
                    if file_path.is_file():
                        files_found += 1
                        logger.info(f"Found file: {file_path}")
                        if not self._should_skip_file(file_path):
                            logger.info(f"Indexing file: {file_path}")
                            try:
                                content = file_path.read_text(encoding='utf-8')
                                logger.info(f"File content length: {len(content)} characters")
                                chunks = await self.index_file(
                                    str(file_path.relative_to(repo_path)),
                                    content,
                                    "HEAD",  # TODO: Get actual commit SHA
                                    "main"
                                )
                                blob_shas.extend(chunks)
                                indexed_files += 1
                                total_chunks += len(chunks)
                                logger.info(f"Successfully indexed {file_path} with {len(chunks)} chunks")
                            except Exception as e:
                                logger.warning(f"Failed to index {file_path}: {e}")
                        else:
                            files_skipped += 1
                            logger.info(f"Skipped file: {file_path}")
                
                logger.info(f"File scan complete: {files_found} files found, {files_skipped} skipped, {indexed_files} indexed")
            
            if scope in ["all", "tasks"]:
                # Index task files
                tasks_path = repo_path / "tasks"
                if tasks_path.exists():
                    for task_file in tasks_path.glob("*.json"):
                        try:
                            content = task_file.read_text(encoding='utf-8')
                            chunks = await self.index_file(
                                str(task_file.relative_to(repo_path)),
                                content,
                                "HEAD",
                                "main"
                            )
                            blob_shas.extend(chunks)
                            indexed_files += 1
                            total_chunks += len(chunks)
                        except Exception as e:
                            logger.warning(f"Failed to index task file {task_file}: {e}")
            
            # Store indexed blobs in Redis for auditability
            if self.redis_client and blob_shas:
                # Add each blob SHA individually to avoid Redis argument issues
                for blob_sha in blob_shas:
                    await self.redis_client.sadd("rag:pending_blobs", blob_sha)
            
            logger.info(f"Reindexed {indexed_files} files with {total_chunks} chunks")
            return {
                "status": "success",
                "indexed_files": indexed_files,
                "total_chunks": total_chunks,
                "blob_shas": blob_shas
            }
            
        except Exception as e:
            logger.error(f"Failed to reindex repository: {e}")
            raise
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """Determine if file should be skipped during indexing."""
        skip_patterns = [
            r'\.git/',
            r'__pycache__/',
            r'\.pyc$',
            r'node_modules/',
            r'\.env',
            r'\.DS_Store',
            r'\.log$',
            r'\.tmp$',
            r'\.cache/',
            r'venv/',
            r'\.venv/',
            r'htmlcov/',
            r'\.coverage'
        ]
        
        file_str = str(file_path)
        return any(re.search(pattern, file_str) for pattern in skip_patterns)
    
    async def check_blob_metadata(self, blob_sha: str) -> Dict[str, Any]:
        """Check if blob metadata is present."""
        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT blob_sha, size, mime, first_seen_at
                    FROM git_blobs
                    WHERE blob_sha = $1
                """, blob_sha)
                
                if row:
                    return {
                        "present": True,
                        "blob_sha": row['blob_sha'],
                        "size": row['size'],
                        "mime": row['mime'],
                        "first_seen_at": row['first_seen_at'].isoformat()
                    }
                else:
                    return {"present": False, "blob_sha": blob_sha}
                    
        except Exception as e:
            logger.error(f"Failed to check blob metadata for {blob_sha}: {e}")
            raise
    
    async def close(self):
        """Close connections."""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("RAG service connections closed")
