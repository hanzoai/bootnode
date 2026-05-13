// Package db — schema statements applied in order at startup.
package db

// schemaStatements is the authoritative schema. Each statement is
// idempotent (CREATE IF NOT EXISTS). New columns land via additive
// ALTER TABLE statements appended at the end.
var schemaStatements = []string{
	`CREATE EXTENSION IF NOT EXISTS pgcrypto`,
	`CREATE EXTENSION IF NOT EXISTS "uuid-ossp"`,

	`CREATE TABLE IF NOT EXISTS users (
		id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		email         VARCHAR(255) NOT NULL UNIQUE,
		name          VARCHAR(255) NOT NULL,
		password_hash VARCHAR(255),
		avatar        VARCHAR(500),
		roles         JSONB DEFAULT '["user"]',
		permissions   JSONB DEFAULT '["read","write"]',
		is_active     BOOLEAN DEFAULT TRUE,
		last_login_at TIMESTAMPTZ,
		created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
		updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
	)`,

	`CREATE TABLE IF NOT EXISTS projects (
		id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		name            VARCHAR(255) NOT NULL,
		owner_id        UUID NOT NULL,
		org_id          VARCHAR(100) NOT NULL DEFAULT 'hanzo',
		description     TEXT,
		settings        JSONB NOT NULL DEFAULT '{}',
		allowed_chains  JSONB,
		created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
		updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
	)`,
	`CREATE INDEX IF NOT EXISTS idx_projects_org ON projects(org_id)`,
	`CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects(owner_id)`,

	`CREATE TABLE IF NOT EXISTS api_keys (
		id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		project_id         UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
		name               VARCHAR(255) NOT NULL,
		key_hash           VARCHAR(255) NOT NULL UNIQUE,
		key_prefix         VARCHAR(12) NOT NULL,
		rate_limit         INTEGER NOT NULL DEFAULT 100,
		compute_units_limit INTEGER NOT NULL DEFAULT 1000,
		allowed_origins    JSONB,
		allowed_chains     JSONB,
		is_active          BOOLEAN NOT NULL DEFAULT TRUE,
		last_used_at       TIMESTAMPTZ,
		created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
	)`,
	`CREATE INDEX IF NOT EXISTS idx_api_keys_project ON api_keys(project_id)`,
	`CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash)`,

	`CREATE TABLE IF NOT EXISTS webhooks (
		id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
		name          VARCHAR(255) NOT NULL,
		url           VARCHAR(1000) NOT NULL,
		secret        VARCHAR(255) NOT NULL,
		events        JSONB NOT NULL DEFAULT '[]',
		is_active     BOOLEAN NOT NULL DEFAULT TRUE,
		created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
		updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
	)`,
	`CREATE INDEX IF NOT EXISTS idx_webhooks_project ON webhooks(project_id)`,

	`CREATE TABLE IF NOT EXISTS wallets (
		id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
		project_id    UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
		chain         VARCHAR(64) NOT NULL,
		address       VARCHAR(128) NOT NULL,
		label         VARCHAR(255),
		smart_wallet  BOOLEAN NOT NULL DEFAULT FALSE,
		created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
		updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
	)`,
	`CREATE UNIQUE INDEX IF NOT EXISTS uq_wallets_proj_chain_addr ON wallets(project_id, chain, address)`,
}
