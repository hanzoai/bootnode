// Package db — typed row structs corresponding to schema.go tables.
package db

import (
	"time"

	"github.com/google/uuid"
)

// User mirrors the users table.
type User struct {
	ID           uuid.UUID
	Email        string
	Name         string
	PasswordHash *string
	Avatar       *string
	Roles        []string
	Permissions  []string
	IsActive     bool
	LastLoginAt  *time.Time
	CreatedAt    time.Time
	UpdatedAt    time.Time
}

// Project mirrors the projects table.
type Project struct {
	ID            uuid.UUID
	Name          string
	OwnerID       uuid.UUID
	OrgID         string
	Description   *string
	Settings      map[string]any
	AllowedChains []string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

// APIKey mirrors the api_keys table. KeyHash is opaque to the caller;
// the plaintext is shown once at creation and never re-emitted.
type APIKey struct {
	ID                uuid.UUID
	ProjectID         uuid.UUID
	Name              string
	KeyHash           string
	KeyPrefix         string
	RateLimit         int
	ComputeUnitsLimit int
	AllowedOrigins    []string
	AllowedChains     []string
	IsActive          bool
	LastUsedAt        *time.Time
	CreatedAt         time.Time
}

// Webhook mirrors the webhooks table.
type Webhook struct {
	ID        uuid.UUID
	ProjectID uuid.UUID
	Name      string
	URL       string
	Secret    string
	Events    []string
	IsActive  bool
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Wallet mirrors the wallets table.
type Wallet struct {
	ID          uuid.UUID
	ProjectID   uuid.UUID
	Chain       string
	Address     string
	Label       *string
	SmartWallet bool
	CreatedAt   time.Time
	UpdatedAt   time.Time
}
