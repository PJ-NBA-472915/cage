-- Initialize Cage database with pgvector extension

-- Create pgvector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create basic tables for RAG
CREATE TABLE IF NOT EXISTS embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx ON embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
