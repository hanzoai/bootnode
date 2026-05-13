// Package client — canonical client interface for Hanzo Bootnode.
//
//	import bn "github.com/hanzoai/bootnode/api-go/client"
//	var b bn.Bootnode = bn.NewClient(cfg)

package client

import (
	"context"
	"encoding/json"
	"time"
)

// Bootnode is the blockchain-developer-platform surface: chain
// registry, JSON-RPC proxy, smart-wallet provisioning, token + NFT
// metadata reads, webhook subscriptions.
type Bootnode interface {
	// Kind reports the backend identifier (hanzo-bootnode).
	Kind() string

	// Chains returns the available chain catalog (id, chainId, name).
	Chains(ctx context.Context) ([]Chain, error)

	// ChainStatus returns the indexer's snapshot of a chain's current
	// height + uptime.
	ChainStatus(ctx context.Context, chainID string) (*ChainStatus, error)

	// RPC proxies a JSON-RPC request to the chain's upstream provider.
	// The response is the raw RPC envelope (jsonrpc + id + result/error)
	// the caller passes back to its client unchanged.
	RPC(ctx context.Context, chainID string, request json.RawMessage) (json.RawMessage, error)

	// CreateProject opens a developer project. Org is taken from the
	// authenticated caller's claims.
	CreateProject(ctx context.Context, req CreateProjectRequest) (*Project, error)

	// ListProjects returns projects in the caller's org.
	ListProjects(ctx context.Context) ([]Project, error)

	// IssueAPIKey mints a new API key for a project. The plaintext key
	// is returned ONCE; the caller persists it. Subsequent reads see
	// only the prefix.
	IssueAPIKey(ctx context.Context, projectID, name string) (*APIKeyIssued, error)

	// RevokeAPIKey disables an API key. Idempotent.
	RevokeAPIKey(ctx context.Context, keyID string) error

	// RegisterWallet binds a smart wallet (EIP-4337) or EOA to a
	// project for tracking. Returns the wallet record.
	RegisterWallet(ctx context.Context, req RegisterWalletRequest) (*Wallet, error)

	// ListWallets returns wallets bound to a project.
	ListWallets(ctx context.Context, projectID string) ([]Wallet, error)

	// TokenMetadata returns the canonical ERC-20 metadata for an
	// address on a chain.
	TokenMetadata(ctx context.Context, chainID, address string) (*TokenInfo, error)

	// TokenBalance returns the holder's balance.
	TokenBalance(ctx context.Context, chainID, token, holder string) (*Balance, error)

	// NFTCollection returns collection-level metadata.
	NFTCollection(ctx context.Context, chainID, collection string) (*NFTCollection, error)

	// NFTToken returns single-token metadata.
	NFTToken(ctx context.Context, chainID, collection, tokenID string) (*NFTToken, error)

	// SubscribeWebhook registers a per-project webhook subscription.
	SubscribeWebhook(ctx context.Context, req WebhookRequest) (*Webhook, error)

	// UnsubscribeWebhook removes a subscription. Idempotent.
	UnsubscribeWebhook(ctx context.Context, webhookID string) error
}

// Chain is one chain registry entry.
type Chain struct {
	ID      string // canonical short name (ethereum | lux-c | liquid | pars | zoo | hanzo)
	ChainID int    // EIP-155 chain id
	Name    string // display name
}

// ChainStatus is the indexer-reported live status.
type ChainStatus struct {
	ChainID string
	Online  bool
	Height  uint64
	At      time.Time
}

// CreateProjectRequest is the project-creation payload.
type CreateProjectRequest struct {
	Name        string
	Description string
	// AllowedChains restricts the project's RPC access. Empty = all
	// chains in the registry.
	AllowedChains []string
}

// Project is the canonical project record.
type Project struct {
	ID            string
	Name          string
	OwnerID       string
	OrgID         string
	Description   string
	AllowedChains []string
	CreatedAt     time.Time
	UpdatedAt     time.Time
}

// APIKeyIssued is the response from IssueAPIKey. PlaintextKey is
// shown once.
type APIKeyIssued struct {
	ID            string
	ProjectID     string
	Name          string
	PlaintextKey  string // shown once; persist client-side
	KeyPrefix     string // displayed in admin lists
	RateLimit     int
	CreatedAt     time.Time
}

// RegisterWalletRequest is the wallet-binding payload.
type RegisterWalletRequest struct {
	ProjectID   string
	Chain       string
	Address     string
	Label       string
	SmartWallet bool
}

// Wallet is the canonical wallet record.
type Wallet struct {
	ID          string
	ProjectID   string
	Chain       string
	Address     string
	Label       string
	SmartWallet bool
	CreatedAt   time.Time
}

// TokenInfo is the ERC-20 metadata sidecar.
type TokenInfo struct {
	Chain       string
	Address     string
	Name        string
	Symbol      string
	Decimals    int
	TotalSupply string // decimal string to preserve precision
}

// Balance is a holder's balance + USD value (when oracle data is
// available).
type Balance struct {
	Token      string
	Holder     string
	Balance    string // decimal string
	BalanceUSD float64
}

// NFTCollection is collection-level metadata.
type NFTCollection struct {
	Chain    string
	Address  string
	Name     string
	Symbol   string
	Standard string // erc721 | erc1155
	TotalSupply uint64
}

// NFTToken is one NFT's metadata.
type NFTToken struct {
	Chain        string
	Collection   string
	TokenID      string
	Owner        string
	TokenURI     string
	Metadata     map[string]any
}

// WebhookRequest is the webhook-subscription payload.
type WebhookRequest struct {
	ProjectID string
	Name      string
	URL       string
	// Events is the subscription filter
	// (block.new | tx.confirmed | log.matched | wallet.balance_changed).
	Events []string
}

// Webhook is the canonical subscription record.
type Webhook struct {
	ID        string
	ProjectID string
	Name      string
	URL       string
	Events    []string
	Secret    string // signing secret, shown once at creation
	CreatedAt time.Time
}
