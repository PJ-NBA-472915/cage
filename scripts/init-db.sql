-- Initialize Cage database with pgvector extension
-- This script runs when the PostgreSQL container starts

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create git_blobs table
CREATE TABLE IF NOT EXISTS git_blobs (
    blob_sha TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    mime TEXT,
    first_seen_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create embeddings table with pgvector
CREATE TABLE IF NOT EXISTS embeddings (
    blob_sha TEXT REFERENCES git_blobs(blob_sha) ON DELETE CASCADE,
    chunk_id INTEGER NOT NULL,
    vector VECTOR(1536) NOT NULL,
    meta JSONB NOT NULL,
    PRIMARY KEY (blob_sha, chunk_id)
);

-- Create blob_paths table
CREATE TABLE IF NOT EXISTS blob_paths (
    blob_sha TEXT NOT NULL,
    commit_sha TEXT NOT NULL,
    path TEXT NOT NULL,
    PRIMARY KEY (commit_sha, path)
);

-- Create events table
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    type TEXT NOT NULL,
    payload JSONB NOT NULL,
    correlation_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index on events type
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);

-- Create crew_runs table
CREATE TABLE IF NOT EXISTS crew_runs (
    id UUID PRIMARY KEY,
    task_id TEXT,
    status TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create run_artefacts table
CREATE TABLE IF NOT EXISTS run_artefacts (
    id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES crew_runs(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    content_type TEXT,
    size BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_blob_paths_commit ON blob_paths(commit_sha);
CREATE INDEX IF NOT EXISTS idx_blob_paths_path ON blob_paths(path);
CREATE INDEX IF NOT EXISTS idx_crew_runs_task_id ON crew_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_crew_runs_status ON crew_runs(status);

-- Insert initial event
INSERT INTO events (type, payload, correlation_id) VALUES 
('cage.database.initialized', '{"message": "Database initialized successfully"}', 'init');
