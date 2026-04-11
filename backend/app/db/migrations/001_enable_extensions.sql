-- Migration 001: Enable required Postgres extensions
-- Run this first in Supabase SQL editor

-- pgvector for 1536-dim embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
