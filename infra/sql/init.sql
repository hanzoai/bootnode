-- Bootnode PostgreSQL initialization
-- Extensions needed by SQLAlchemy models

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Tables are created by SQLAlchemy Base.metadata.create_all() at app startup.
-- This file only sets up PostgreSQL extensions that SQLAlchemy cannot create.
