// Package db — Postgres pool + migration entry.
package db

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

// Pool wraps pgxpool.Pool so callers depend on this package's type and
// the underlying driver can be swapped without breaking call sites.
type Pool = pgxpool.Pool

// Open creates a connection pool from the canonical DATABASE_URL.
func Open(ctx context.Context, dsn string, poolSize, maxOverflow int) (*Pool, error) {
	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, fmt.Errorf("parse dsn: %w", err)
	}
	cfg.MaxConns = int32(poolSize + maxOverflow)
	cfg.MinConns = int32(poolSize / 4)
	p, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("connect: %w", err)
	}
	if err := p.Ping(ctx); err != nil {
		p.Close()
		return nil, fmt.Errorf("ping: %w", err)
	}
	return p, nil
}

// Init runs the schema migrations. Idempotent.
func Init(ctx context.Context, p *Pool) error {
	for _, stmt := range schemaStatements {
		if _, err := p.Exec(ctx, stmt); err != nil {
			return fmt.Errorf("migration %q: %w", stmt[:min(len(stmt), 60)], err)
		}
	}
	return nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
