# Hanzo Web3 - Blockchain Development Platform

## Project Overview

**Hanzo Web3** is a blockchain development platform providing enterprise infrastructure APIs for building Web3 applications. The platform enables developers to interact with multiple blockchains through unified APIs - similar to Alchemy, Infura, or QuickNode but powered by Hanzo AI.

### White-Label Deployments
This codebase supports white-labeling for different brands:
- **Hanzo Web3** (default): web3.hanzo.ai - Enterprise blockchain infrastructure
- **Lux Cloud**: lux.cloud - Lux Network ecosystem infrastructure
- **Zoo Labs**: web3.zoo.ngo - Decentralized AI infrastructure
- **Bootnode**: bootno.de - Standalone deployment

Brand is auto-detected from domain or via `NEXT_PUBLIC_BRAND` environment variable (set at build time for Next.js).

## Current State Analysis

### Legacy Architecture (2018-2019 era)
```
bootnode/
├── bootnode/          # Python backend (Quart framework)
│   ├── bootnode.py    # Core orchestration logic
│   ├── kubernetes.py  # K8s deployment management
│   ├── gcloud.py      # GCP integration
│   └── template.py    # Blockchain deployment templates
├── bootnode-admin/    # Next.js 7 admin dashboard
│   ├── pages/         # React pages
│   ├── components/    # UI components (Material UI 3)
│   └── src/           # Client utilities
├── geth/              # Ethereum node Dockerfile
├── casper/            # Casper node Dockerfile
└── config/            # Kubernetes configs
```

### Legacy Tech Stack (Outdated)
- **Backend**: Python 3.7, Quart (async Flask), requests_async
- **Database**: MongoDB (pymongo)
- **Frontend**: Next.js 7, React 16.7, Material UI 3, Stylus
- **Templating**: react-pug (deprecated)
- **Infrastructure**: Google Cloud, Kubernetes
- **Blockchains**: Ethereum (geth), Casper only

### Critical Issues
1. **Security**: Hardcoded credentials in app.py
2. **Dependencies**: All packages severely outdated
3. **Chain Support**: Only 2 blockchains (Ethereum, Casper)
4. **Features**: No modern blockchain APIs (NFT, tokens, AA, etc.)
5. **Frontend**: Ancient Next.js/React versions

## Target Architecture: Cortex Platform

### Feature Matrix
| Feature | Description | Priority |
|---------|-------------|----------|
| RPC API | Multi-chain JSON-RPC proxy with load balancing | P0 |
| WebSockets | Real-time blockchain subscriptions | P0 |
| Token API | ERC-20/ERC-721/ERC-1155 balances & metadata | P0 |
| NFT API | NFT collections, ownership, metadata | P1 |
| Transfers API | Transaction history & transfers | P1 |
| Webhooks | Event-driven notifications | P1 |
| Smart Wallets | ERC-4337 account abstraction | P1 |
| Bundler API | UserOp bundling for AA | P2 |
| Gas Manager API | Paymaster & gas sponsorship | P2 |
| Rollups | L2 support (OP Stack, Arbitrum, zkSync) | P2 |

### Supported Chains (Phase 1)
- **EVM**: Ethereum, Polygon, Arbitrum, Optimism, Base, Avalanche, BNB Chain, Lux
- **Non-EVM**: Solana, Bitcoin (read-only)
- **L2/Rollups**: OP Stack chains, Arbitrum Orbit, zkSync Era

### Modern Tech Stack
```
bootnode/
├── api/                    # FastAPI backend (Python 3.12+)
│   ├── bootnode/
│   │   ├── api/           # API routes
│   │   │   ├── rpc/       # JSON-RPC proxy
│   │   │   ├── tokens/    # Token API
│   │   │   ├── nfts/      # NFT API
│   │   │   ├── transfers/ # Transfers API
│   │   │   ├── webhooks/  # Webhook management
│   │   │   ├── wallets/   # Smart wallet API
│   │   │   ├── bundler/   # ERC-4337 bundler
│   │   │   └── gas/       # Gas manager
│   │   ├── core/          # Core business logic
│   │   │   ├── chains/    # Chain configurations
│   │   │   ├── indexer/   # Event indexing
│   │   │   └── cache/     # Caching layer
│   │   ├── db/            # Database models
│   │   └── ws/            # WebSocket handlers
│   ├── pyproject.toml
│   └── Dockerfile
├── web/                    # Next.js 15 dashboard
│   ├── app/               # App router
│   ├── components/        # @hanzo/ui components
│   └── package.json
├── indexer/               # Event indexer service
│   ├── src/
│   └── Cargo.toml         # Rust for performance
├── infra/                 # Infrastructure
│   ├── k8s/               # Kubernetes manifests
│   ├── terraform/         # IaC
│   └── compose.yml        # Local development
└── docs/                  # Documentation
```

### API Design

#### RPC API
```
POST /v1/rpc/{chain}
POST /v1/rpc/{chain}/{network}
Headers: X-API-Key: <api_key>

# Example
POST /v1/rpc/ethereum/mainnet
{
  "jsonrpc": "2.0",
  "method": "eth_blockNumber",
  "params": [],
  "id": 1
}
```

#### Token API
```
GET  /v1/tokens/{chain}/balances/{address}
GET  /v1/tokens/{chain}/metadata/{contract}
GET  /v1/tokens/{chain}/holders/{contract}
GET  /v1/tokens/{chain}/transfers/{address}
```

#### NFT API
```
GET  /v1/nfts/{chain}/collections/{address}
GET  /v1/nfts/{chain}/owned/{address}
GET  /v1/nfts/{chain}/metadata/{contract}/{tokenId}
GET  /v1/nfts/{chain}/transfers/{address}
POST /v1/nfts/{chain}/refresh-metadata/{contract}/{tokenId}
```

#### Webhooks
```
POST   /v1/webhooks
GET    /v1/webhooks
DELETE /v1/webhooks/{id}
GET    /v1/webhooks/{id}/deliveries

# Webhook Types
- ADDRESS_ACTIVITY      # Any tx involving address
- MINED_TRANSACTION     # Tx confirmation
- NFT_ACTIVITY          # NFT transfers
- TOKEN_TRANSFER        # ERC-20 transfers
- INTERNAL_TRANSFER     # Internal ETH transfers
- GRAPHQL               # Custom GraphQL filters
```

#### WebSocket Subscriptions
```
WS /v1/ws/{chain}

# Subscribe to new blocks
{"jsonrpc":"2.0","method":"eth_subscribe","params":["newHeads"],"id":1}

# Subscribe to pending txs
{"jsonrpc":"2.0","method":"eth_subscribe","params":["pendingTransactions"],"id":2}

# Subscribe to logs (events)
{"jsonrpc":"2.0","method":"eth_subscribe","params":["logs",{"address":"0x..."}],"id":3}
```

#### Native ZAP Protocol

ZAP (Zero-Copy App Proto) is a high-performance Cap'n Proto-based binary RPC protocol.
Bootnode implements **native ZAP** - no gateway, direct Cap'n Proto RPC over TCP.

**Connection**
```
AI Agent → zap://api.bootno.de:9999 (direct Cap'n Proto RPC)
```

**Schema Files**
- `bootnode/zap/bootnode.zap` - Clean whitespace-significant syntax (new format)
- `bootnode/zap/bootnode.capnp` - Compiled Cap'n Proto schema (for pycapnp)

**Python Client Example**
```python
from hanzo_zap import Client

async with Client.connect("zap://api.bootno.de:9999") as client:
    # Initialize connection
    server_info = await client.init({"name": "my-agent", "version": "1.0"})

    # List tools
    tools = await client.list_tools()

    # Call a tool
    result = await client.call_tool("rpc_call", {
        "chain": "ethereum",
        "method": "eth_blockNumber"
    })
```

**REST Endpoints (Discovery)**
```
GET /v1/zap/connect       # Connection info & examples
GET /v1/zap/info          # Server capabilities
GET /v1/zap/tools         # Available tools
GET /v1/zap/resources     # Available resources
GET /v1/zap/schema        # .zap schema (whitespace-significant)
GET /v1/zap/schema.capnp  # Compiled .capnp schema
GET /v1/zap/health        # Health check
```

**Code Generation**
```bash
# Get schema and compile
curl -H "X-API-Key: $KEY" https://api.bootno.de/v1/zap/schema > bootnode.zap
zapc compile bootnode.zap --out=bootnode.capnp

# Generate client code
zapc generate bootnode.capnp --lang python --out ./gen/
```

**ZAP Tools (MCP-compatible)**
| Tool | Description |
|------|-------------|
| rpc_call | Execute JSON-RPC on blockchain |
| get_token_balances | Get ERC-20 token balances for address |
| get_token_metadata | Get token metadata (name, symbol, decimals) |
| get_nfts_owned | Get NFTs owned by address |
| get_nft_metadata | Get NFT metadata and attributes |
| create_smart_wallet | Create ERC-4337 smart wallet |
| get_smart_wallet | Get smart wallet details |
| create_webhook | Create webhook for blockchain events |
| list_webhooks | List configured webhooks |
| delete_webhook | Delete webhook by ID |
| estimate_gas | Get current gas prices |

**ZAP Resources**
| URI | Description |
|-----|-------------|
| bootnode://chains | List of all supported blockchain networks |
| bootnode://usage | API usage for current billing period |
| bootnode://config | Current API configuration and limits |

**Server Implementation**
- Location: `api/bootnode/zap/server.py`
- Class: `BootnodeZapImpl(bootnode_capnp.Bootnode.Server)`
- Startup: Automatic in `main.py` lifespan handler
- Default port: 9999 (configurable via `ZAP_PORT` env var)

**Environment Variables**
```env
ZAP_ENABLED=true     # Enable native ZAP server
ZAP_HOST=0.0.0.0     # Bind address
ZAP_PORT=9999        # Listen port
```

See: https://github.com/hanzo-ai/zap

#### Smart Wallets (ERC-4337)
```
POST /v1/wallets/create
GET  /v1/wallets/{address}
POST /v1/wallets/{address}/sign
POST /v1/wallets/{address}/execute
```

#### Bundler API
```
POST /v1/bundler/{chain}
{
  "jsonrpc": "2.0",
  "method": "eth_sendUserOperation",
  "params": [userOp, entryPoint],
  "id": 1
}

# Supported methods:
# - eth_sendUserOperation
# - eth_estimateUserOperationGas
# - eth_getUserOperationByHash
# - eth_getUserOperationReceipt
# - eth_supportedEntryPoints
```

#### Gas Manager API
```
POST /v1/gas/sponsor
POST /v1/gas/estimate
GET  /v1/gas/prices/{chain}
GET  /v1/gas/policies
POST /v1/gas/policies
```

#### Infrastructure Management API
```
# Kubernetes Clusters
GET    /v1/infra/clusters                    # List clusters
POST   /v1/infra/clusters                    # Create cluster
GET    /v1/infra/clusters/{id}               # Get cluster details
DELETE /v1/infra/clusters/{id}               # Delete cluster
POST   /v1/infra/clusters/{id}/scale         # Scale node count
GET    /v1/infra/clusters/{id}/kubeconfig    # Download kubeconfig

# Persistent Volumes
GET    /v1/infra/volumes                     # List volumes
POST   /v1/infra/volumes                     # Create volume
GET    /v1/infra/volumes/{id}                # Get volume details
DELETE /v1/infra/volumes/{id}                # Delete volume
POST   /v1/infra/volumes/{id}/attach         # Attach to cluster
POST   /v1/infra/volumes/{id}/detach         # Detach from cluster
POST   /v1/infra/volumes/{id}/resize         # Resize volume

# Snapshots
GET    /v1/infra/snapshots                   # List snapshots
POST   /v1/infra/snapshots                   # Create snapshot
DELETE /v1/infra/snapshots/{id}              # Delete snapshot

# Storage Cloning (copy-on-write for fast provisioning)
GET    /v1/infra/clone                       # List clone jobs
POST   /v1/infra/clone                       # Clone volume or snapshot
GET    /v1/infra/clone/{id}                  # Get clone status
DELETE /v1/infra/clone/{id}                  # Cancel clone

# Infrastructure Stats
GET    /v1/infra/stats                       # Overall stats
```

### Database Schema (PostgreSQL)
```sql
-- API Keys & Projects
CREATE TABLE projects (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  owner_id UUID NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE api_keys (
  id UUID PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  key_hash TEXT NOT NULL,
  name TEXT,
  rate_limit INT DEFAULT 100,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Webhooks
CREATE TABLE webhooks (
  id UUID PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  url TEXT NOT NULL,
  chain TEXT NOT NULL,
  event_type TEXT NOT NULL,
  filters JSONB,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking
CREATE TABLE usage (
  id BIGSERIAL PRIMARY KEY,
  project_id UUID REFERENCES projects(id),
  chain TEXT NOT NULL,
  method TEXT NOT NULL,
  compute_units INT DEFAULT 1,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```

### Caching Strategy
- **Redis**: RPC response caching, rate limiting, session management
- **CDN**: Static NFT metadata, token logos
- **Memory**: Hot chain data, recent blocks

### Compute Unit Pricing
| Method Category | CU Cost |
|-----------------|---------|
| eth_blockNumber, eth_chainId | 1 |
| eth_getBalance, eth_getCode | 5 |
| eth_call, eth_estimateGas | 10 |
| eth_getLogs (100 blocks) | 25 |
| eth_sendRawTransaction | 50 |
| debug_*, trace_* | 100+ |
| NFT/Token API calls | 5-25 |

## E2E Test Status (2026-02-02)

All systems tested and operational:

| Component | Status | Details |
|-----------|--------|---------|
| API Health | ✅ | healthy, v2.0.0 |
| RPC Ethereum | ✅ | Block 0x173e276 |
| RPC Polygon | ✅ | Block 0x4ea72d1 |
| RPC Arbitrum | ✅ | Block 0x1982512d |
| RPC Base | ✅ | Block 0x27b5c63 |
| RPC Optimism | ✅ | Block 0x8c69df8 |
| Chains API | ✅ | 10 chains supported |
| Token API | ✅ | USDC metadata verified |
| Gas API | ✅ | Real-time gas prices |
| Wallets API | ✅ | Smart wallet creation working |
| Webhooks API | ✅ | Webhook creation working |
| Auth/Keys API | ✅ | API key management working |
| ZAP Protocol | ✅ | Native ZAP server (zap://:9999) |
| Infra: Clusters | ✅ | K8s cluster management working |
| Infra: Volumes | ✅ | Persistent volume management working |
| Infra: Snapshots | ✅ | Snapshot creation working |
| Infra: Cloning | ✅ | Rapid storage cloning working |
| Dashboard | ✅ | All pages return 200 |

## Hanzo Infrastructure Status (2026-02-03)

### Active Services (Production)
| Service | URL | Status | Description |
|---------|-----|--------|-------------|
| IAM | https://hanzo.id | ✅ 200 | Hanzo Identity (Casdoor SSO) |
| App Builder | https://hanzo.app | ✅ 200 | AI-powered app builder |
| KMS | kms.hanzo.ai (internal) | ✅ OK | Key Management Service (Infisical) |
| MinIO | internal | ✅ | Object storage |
| MongoDB | internal | ✅ | Document database |
| PostgreSQL | internal | ✅ | Relational database |
| Redis | internal | ✅ | Cache & message queue |
| Monitor | internal | ✅ | GitOps monitoring |
| Sync | internal | ✅ | GitOps sync |

### Pending Deployment
- **Cloud/LLM**: cloud.hanzo.ai replaced with static landing page (nginx)
- **Commerce**: Deployed to hanzo-k8s, PVC `commerce-data` (5Gi), CI building latest image with SQLite bridge
- **KMS External Access**: Needs Cloudflare SSL configuration (Flexible mode)

### Scaled Down (Image Issues)
- platform, studio, webhook: ghcr.io/hanzoai images unavailable

### Infrastructure Configuration
- **Kubernetes**: DigitalOcean DOKS
- **LoadBalancer**: 24.199.76.156 (nginx-ingress)
- **SSL**: Let's Encrypt via cert-manager (pending for some domains due to Cloudflare)
- **Databases**:
  - IAM: Managed DigitalOcean PostgreSQL
  - KMS/Bootnode: In-cluster PostgreSQL
- **Secrets**: ROOT_ENCRYPTION_KEY (base64-encoded 32-byte key for AES-256-GCM)

## Implementation Progress

### Phase 1: Core Infrastructure ✅ COMPLETE
- [x] FastAPI backend with proper project structure (Python 3.12+)
- [x] Multi-chain RPC proxy (100+ chains supported)
- [x] WebSocket subscriptions
- [x] PostgreSQL schema with SQLAlchemy 2.0 async
- [x] API key authentication & rate limiting
- [x] Next.js 15 dashboard with @hanzo/ui

### Phase 2: Enhanced APIs ✅ COMPLETE
- [x] Token API (balances, metadata, transfers)
- [x] NFT API (collections, ownership, metadata)
- [x] Transfers API (transaction history)
- [x] Webhook system with RabbitMQ
- [x] Usage tracking via DataStore (Hanzo Datastore)

### Phase 3: Account Abstraction ✅ COMPLETE
- [x] ERC-4337 bundler with spec-compliant keccak256 userOpHash (eth-abi encoding)
- [x] Smart wallet CREATE2 address computation (keccak256, not sha256)
- [x] Gas manager with paymasterAndData structure (validity window + signature)
- [x] UserOp simulation & estimation
- [x] Webhook delivery with exponential backoff retry (arq)
- [x] Webhook delivery cleanup cron (30-day retention)
- [x] NFT metadata refresh queued via arq/Redis

### Phase 4: Infrastructure ✅ COMPLETE
- [x] Docker Compose full stack
- [x] Kubernetes manifests with HPA/PDB
- [x] Multi-cloud deployment (AWS, GCP, Azure, DigitalOcean)
- [x] DataStore (Hanzo Datastore) for high-performance analytics
- [x] Multi-chain indexer (forked from lux/indexer)
- [x] K8s cluster management API (/v1/infra/clusters)
- [x] Persistent volume management API (/v1/infra/volumes)
- [x] Snapshot management API (/v1/infra/snapshots)
- [x] Rapid storage cloning API (/v1/infra/clone) - copy-on-write

## Development Commands

```bash
# Backend
cd api
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn bootnode.main:app --reload

# Frontend
cd web
pnpm install
pnpm dev

# Infrastructure
docker compose up -d  # Local dev with Postgres, Redis

# Tests
pytest api/tests/
pnpm test --prefix web
```

## Key Dependencies

### Backend (Python)
- fastapi >= 2.0
- uvicorn[standard]
- sqlalchemy >= 2.0
- asyncpg
- redis
- web3.py
- pydantic >= 2.0
- httpx
- websockets
- pycapnp >= 2.0 (native ZAP server)

### Frontend (TypeScript)
- next >= 15.0
- react >= 19.0
- @hanzo/ui
- wagmi
- viem
- @tanstack/react-query
- tailwindcss

## Environment Variables
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/bootnode

# Redis
REDIS_URL=redis://localhost:6379

# Chain RPCs (upstream nodes)
ETH_MAINNET_RPC=https://eth-mainnet.g.alchemy.com/v2/...
ETH_SEPOLIA_RPC=https://eth-sepolia.g.alchemy.com/v2/...
POLYGON_MAINNET_RPC=https://polygon-mainnet.g.alchemy.com/v2/...
# ... more chains

# Auth
JWT_SECRET=...
API_KEY_SALT=...

# Hanzo KMS (Secret Management)
HANZO_KMS_URL=https://kms.hanzo.ai
HANZO_KMS_ORG=hanzo
HANZO_KMS_PROJECT=bootnode
HANZO_KMS_ENV=production
HANZO_KMS_CLIENT_ID=...
HANZO_KMS_CLIENT_SECRET=...

# Hanzo IAM (Authentication)
HANZO_IAM_URL=https://hanzo.id
HANZO_IAM_ORG=HANZO
HANZO_IAM_CLIENT_ID=...
HANZO_IAM_CLIENT_SECRET=...

# External Services
IPFS_GATEWAY=https://ipfs.io/ipfs/
```

## Hanzo KMS Integration (2026-02-02)

Bootnode uses Hanzo KMS for centralized secret management with multi-tenant support.

### SDK Location
- **hanzo-kms**: `~/work/hanzo/python-sdk/pkg/hanzo-kms/`
- **hanzo-iam**: `~/work/hanzo/python-sdk/pkg/hanzo-iam/`

### Multi-Tenancy Support
KMS supports organization-scoped secrets via the `X-Org-Name` header:
- `hanzo` - Hanzo AI organization
- `zoo` - Zoo Labs Foundation
- `lux` - Lux Network
- `pars` - Pars organization

### Usage in Bootnode
```python
from bootnode.core.kms import get_secret, inject_secrets

# At startup (in main.py)
inject_secrets()  # Loads secrets from KMS into environment

# Get individual secret
db_url = get_secret("DATABASE_URL", default="postgresql://...")
```

### Kubernetes Integration
The KMS operator syncs secrets from Hanzo KMS to K8s secrets:
- CRD: `KMSSecret` - Defines which secrets to sync
- Secrets are auto-injected as environment variables
- No need for KMS credentials in K8s (operator handles auth)

## Authentication System

Bootnode supports dual-mode authentication:

### Development Mode (Local)
- **Endpoint**: `POST /v1/auth/register` - Create new user account
- **Endpoint**: `POST /v1/auth/login` - Login with email/password
- **Endpoint**: `GET /v1/auth/me` - Get current authenticated user
- **Storage**: bcrypt-hashed passwords in PostgreSQL users table
- **Token**: JWT with 24-hour expiration

```bash
# Register
curl -X POST http://localhost:8100/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","name":"User Name"}'

# Login
curl -X POST http://localhost:8100/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123"}'

# Get current user
curl http://localhost:8100/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

### Production Mode (Hanzo IAM)
- **IdP**: hanzo.id, zoo.id, lux.id, pars.id
- **Protocol**: OAuth2/OIDC
- **Endpoint**: `POST /v1/auth/oauth/callback` - Exchange auth code for token
- **Multi-tenant**: Supports Hanzo, Zoo Labs, Lux Network, Pars orgs

### Frontend Auth Flow
- `web/lib/auth.tsx` - AuthProvider context with login/register/logout
- `web/app/login/page.tsx` - Dual-mode login page (local dev vs IAM production)
- `web/app/auth/callback/page.tsx` - OAuth callback handler
- `ProtectedRoute` component redirects unauthenticated users to /login

### Auth Detection
- Development: `window.location.hostname === "localhost"`
- Production: Any non-localhost hostname OR `NEXT_PUBLIC_AUTH_MODE=iam`

## Notes
- Use uv for Python package management (per user preference)
- Use compose.yml not docker-compose.yml
- Never commit .env files or API keys
- Follow Hanzo AI conventions for @hanzo/ui components

## Current Architecture

### Project Structure
```
bootnode/
├── api/                        # FastAPI backend (Python 3.12+)
│   └── bootnode/
│       ├── api/                # API routes (rpc, tokens, nfts, etc.)
│       ├── core/               # Business logic
│       │   ├── cache/          # Redis caching
│       │   └── datastore/      # Hanzo Datastore client
│       ├── db/                 # SQLAlchemy models
│       ├── workers/            # Background workers (webhooks)
│       └── ws/                 # WebSocket handlers
├── web/                        # Next.js 15 dashboard
│   └── app/
│       ├── dashboard/          # Admin dashboard pages
│       └── docs/               # Documentation
├── indexer/                    # Go multi-chain indexer
│   └── cmd/multichain/         # Main indexer binary
└── infra/                      # Infrastructure
    ├── compose.yml             # Docker Compose (full stack)
    ├── k8s/                    # Kubernetes manifests
    ├── cloud/                  # Cloud deployment configs
    │   ├── aws/                # EKS cluster
    │   ├── gcp/                # GKE cluster
    │   ├── azure/              # AKS cluster
    │   └── digitalocean/       # DOKS cluster
    ├── config/                 # Chain configurations
    └── monitoring/             # VictoriaMetrics/Grafana
        ├── scrape.yml          # VMAgent scrape config
        └── grafana-datasources.yml
```

### Data Layer
- **PostgreSQL**: Operational data (projects, API keys, webhooks, wallets)
- **DataStore (Hanzo Datastore)**: Analytics & indexed blockchain data (Hanzo's fork)
- **Redis**: Caching, rate limiting, message queue (BullMQ/@hanzo/mq compatible via arq)
- **VictoriaMetrics**: Time-series metrics (Hanzo's fork, replaces Prometheus)

### Hanzo Integration
Bootnode powers the Blockchain & Web3 products on [hanzo.ai](https://hanzo.ai/blockchain):
- Products navigation includes "Blockchain & Web3" category
- Pricing page has dedicated "Blockchain" tab
- Featured in main products grid and footer
- Branded as "Hanzo Blockchain" / "Hanzo Chain"

### Supported Chains (100+)
**Layer 1**: Ethereum, BNB Chain, Avalanche, Gnosis, Celo, Rootstock, Solana, Aptos, Flow, Berachain, Sei, Sonic, Tron, TON

**Optimistic L2**: Arbitrum (One, Nova), Optimism, Base, Blast, Mantle, Metis, Mode, Zora, opBNB

**ZK L2**: Polygon zkEVM, zkSync Era, Scroll, Linea, Starknet

**Other**: Polygon PoS, Astar, ZetaChain, World Chain, Abstract, Soneium, Lux Network

### Deployment
```bash
# Local development
cd infra && docker compose up -d

# With monitoring
docker compose --profile monitoring up -d

# With bundler (ERC-4337)
docker compose --profile bundler up -d

# Cloud deployment
./cloud/deploy.sh aws|gcp|azure|digitalocean
```

### Key Files
- `api/bootnode/config.py` - Application settings (datastore, redis MQ, ZAP)
- `api/bootnode/main.py` - FastAPI application entry (ZAP server startup)
- `api/bootnode/zap/bootnode.zap` - ZAP schema (whitespace-significant syntax)
- `api/bootnode/zap/bootnode.capnp` - Compiled Cap'n Proto schema
- `api/bootnode/zap/server.py` - Native ZAP server implementation
- `api/bootnode/api/zap.py` - ZAP REST endpoints (discovery)
- `api/bootnode/core/datastore/client.py` - Hanzo Datastore client
- `api/bootnode/workers/webhook.py` - Webhook delivery worker (arq/Redis-based)
- `api/pyproject.toml` - Python dependencies (arq, aiochclient, pycapnp)
- `infra/compose.yml` - Full Docker Compose stack (VictoriaMetrics, VMAgent)
- `infra/config/chains.yaml` - Multi-chain configuration
- `infra/monitoring/scrape.yml` - VMAgent scrape config
- `infra/.env.example` - Environment variables template
- `indexer/README.md` - Indexer documentation

## Hanzo Platform Infrastructure

### DigitalOcean Docker Swarm Deployment

**Server**: `hanzo-platform` (165.227.92.111)
- Docker Swarm Manager node
- Ubuntu with Docker
- SSH key: hanzo-platform@hanzo.ai

**Stack Configuration**: `/opt/hanzo/stack.yml`

### Services Running

| Service | Domain | Status | Image |
|---------|--------|--------|-------|
| Platform | platform.hanzo.ai | ✅ Active | hanzoai/platform:latest |
| Staging | staging.platform.hanzo.ai | ✅ Active | hanzoai/platform:latest |
| LLM API | llm.hanzo.ai | ✅ Active | hanzoai/llm:latest |
| Traefik | - | ✅ Active | traefik:v2.11 |
| PostgreSQL | - | ✅ Active | postgres:16-alpine |
| Redis | - | ✅ Active | redis:7-alpine |

### Platform PaaS Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Swarm Cluster                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐       │
│  │   Traefik   │   │  Platform   │   │  Platform   │       │
│  │  (global)   │   │  (2 repl)   │   │  Staging    │       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                  │                  │              │
│         │  hanzo-network   │                  │              │
│  ┌──────┴──────────────────┴──────────────────┴──────┐     │
│  │                   Overlay Network                   │     │
│  └──────┬──────────────────┬──────────────────┬──────┘     │
│         │                  │                  │              │
│  ┌──────┴──────┐   ┌──────┴──────┐   ┌──────┴──────┐       │
│  │  PostgreSQL │   │    Redis    │   │ platform-   │       │
│  │             │   │             │   │ network     │       │
│  └─────────────┘   └─────────────┘   └──────┬──────┘       │
│                                              │              │
│                                      ┌───────┴───────┐     │
│                                      │ Platform Apps │     │
│                                      │  (LLM, etc)   │     │
│                                      └───────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Traefik Configuration

- **Docker provider**: Swarm mode for Platform services
- **File provider**: `/etc/platform/traefik/dynamic/` for Platform-deployed apps
- **Networks**: Connected to both `hanzo-network` and `platform-network`
- **SSL**: Let's Encrypt ACME with HTTP challenge

### Platform API

- **URL**: https://platform.hanzo.ai
- **Admin**: admin@hanzo.ai
- **Organization**: Hanzo Services (aIwfYjsvHRtJEM2lZgc00)

### Applications Configured

| Application | App ID | Domain | Docker Image |
|-------------|--------|--------|--------------|
| Hanzo IAM | 2q38x48jAZ8P3RTeoPLIn | iam.hanzo.ai | hanzoai/iam:latest |
| Hanzo Console | 6dY7lG_2Fi0Ki2EHDUTC2 | console.hanzo.ai | hanzoai/console:latest |
| Hanzo Chat | -EwrYn-tplr1aE_f_OPqY | chat.hanzo.ai | hanzoai/chat:latest |
| Hanzo Commerce | f9aw6D5KCq4Q8VQqxPGnL | commerce.hanzo.ai | hanzoai/commerce:latest |
| Hanzo Analytics | sID_Yo2Lgc_zaG5y_YREf | analytics.hanzo.ai | hanzoai/analytics:latest |
| Hanzo Gateway | YxpbUnqLPm8YZNq0T4ZeU | api.hanzo.ai | hanzoai/gateway:latest |
| Hanzo LLM | bS2chI8EdueK-OWuqa3N- | llm.hanzo.ai | hanzoai/llm:latest |
| Hanzo Mail | R1dgri7AR1fSAtK59HzsA | mail.hanzo.ai | hanzoai/mail:latest |

### Docker Images Needed (amd64)

Several applications need Docker images built for amd64:
- `hanzoai/iam` - Not found on Docker Hub
- `hanzoai/console` - Not found on Docker Hub
- `hanzoai/commerce` - Not found on Docker Hub
- `hanzoai/analytics` - Not found on Docker Hub
- `hanzoai/chat` - Exists but arm64 only
- `hanzoai/mail` - Exists, architecture unclear

### Deployment Commands

```bash
# Deploy/Update stack
ssh root@165.227.92.111 "cd /opt/hanzo && \
  POSTGRES_PASSWORD='...' \
  NEXTAUTH_SECRET='...' \
  docker stack deploy -c stack.yml hanzo"

# Add worker node
doctl compute droplet create hanzo-worker-N \
  --region nyc1 --size s-2vcpu-4gb \
  --image docker-20-04 \
  --user-data "docker swarm join --token SWMTKN-... 165.227.92.111:2377"

# Check services
ssh root@165.227.92.111 "docker service ls"

# View logs
ssh root@165.227.92.111 "docker service logs hanzo_platform"
```

### DNS Configuration (Cloudflare)

Zone: hanzo.ai (bac51c3900e73fd28aa75a59898bcee0)
- All subdomains → 165.227.92.111 (A record, proxied=false)
- Subdomains: platform, staging.platform, iam, console, chat, commerce, analytics, api, llm, mail

## CI/CD Pipeline

### GitHub Actions Workflow

The CI/CD pipeline is configured in `.github/workflows/ci.yml`:

| Stage | Trigger | Description |
|-------|---------|-------------|
| test-api | push/PR | Run Python API tests with PostgreSQL + Redis |
| test-web | push/PR | Build Next.js frontend |
| e2e-test | after test-api, test-web | End-to-end API tests |
| build-and-push | main branch only | Build & push Docker images to GHCR |
| deploy | after build-and-push | Deploy to DOKS via kubectl |

### Docker Images

Images are pushed to Docker Hub (linux/amd64):
- `hanzoai/bootnode:api-latest` - Python FastAPI backend
- `hanzoai/bootnode:web-latest` - Next.js frontend
- Build with: `docker buildx build --platform linux/amd64 -t hanzoai/bootnode:<tag> --push .`

### Required GitHub Secrets

Configure these in GitHub repo Settings → Secrets → Actions:

| Secret | Description |
|--------|-------------|
| `DIGITALOCEAN_ACCESS_TOKEN` | DigitalOcean API token for DOKS access |
| `K8S_CLUSTER_NAME` | DOKS cluster name (e.g., `hanzo-k8s`) |

### Production URLs

| Domain | Service | Description |
|--------|---------|-------------|
| web3.hanzo.ai | bootnode-web | Dashboard frontend |
| api.web3.hanzo.ai | bootnode-api | REST API |
| ws.web3.hanzo.ai | bootnode-api | WebSocket endpoint |

### Production Deployment (2026-02-02)

**Cluster**: do-sfo3-lux-k8s (DigitalOcean Kubernetes)
**Namespace**: bootnode

| Resource | Replicas | Image | Status |
|----------|----------|-------|--------|
| bootnode-api | 3 | hanzoai/bootnode:api-latest | ✅ Running |
| bootnode-web | 2 | hanzoai/bootnode:web-latest | ✅ Running |

**Docker Hub Registry**: Images pushed to `docker.io/hanzoai/bootnode` (linux/amd64)
- `hanzoai/bootnode:api-latest` - FastAPI backend
- `hanzoai/bootnode:web-latest` - Next.js frontend

**Shared Infrastructure** (hanzo namespace):
- PostgreSQL: postgres.hanzo.svc.cluster.local:5432
- Redis: redis-master.hanzo.svc.cluster.local:6379
- Hanzo IAM: iam.hanzo.ai (OAuth2/OIDC)

### Kubernetes Resources

Located in `infra/k8s/`:
- `namespace.yaml` - bootnode namespace
- `secrets.yaml` - Template for secrets (use kubectl to create real secrets)
- `api-deployment.yaml` - API deployment, service, HPA, PDB
- `web-deployment.yaml` - Web deployment, service, HPA
- `ingress.yaml` - Ingress with TLS (cert-manager)

### Manual Deployment

```bash
# Deploy with script
cd infra/k8s && ./deploy.sh deploy

# Check status
./deploy.sh status

# Rollback
./deploy.sh rollback
```

### Creating Production Secrets

```bash
# Create secrets in cluster (never commit real values!)
kubectl create secret generic bootnode-secrets \
  --namespace bootnode \
  --from-literal=database-url='postgresql+asyncpg://...' \
  --from-literal=redis-url='redis://...' \
  --from-literal=datastore-url='clickhouse://...' \
  --from-literal=jwt-secret='$(openssl rand -hex 32)' \
  --from-literal=api-key-salt='$(openssl rand -hex 16)'
```

### Hanzo Universe Integration

Bootnode is also configured for deployment via Hanzo Universe infrastructure:
- Located at: `~/work/hanzo/universe/infra/k8s/bootnode/`
- Uses Kustomize for configuration management
- Shares common labels with other Hanzo services

## Blockchain Node Deployment

Bootnode can deploy and manage real blockchain nodes via Docker.

### Nodes API

```bash
# Check Docker availability
GET /v1/nodes/docker/status

# List all deployed nodes
GET /v1/nodes/

# Get node statistics
GET /v1/nodes/stats

# Deploy a new node
POST /v1/nodes/
{
  "name": "ETH Sepolia",
  "chain": "ethereum",
  "network": "sepolia",
  "provider": "docker"
}

# Get node details & metrics
GET /v1/nodes/{node_id}

# Start/Stop/Delete node
POST /v1/nodes/{node_id}/start
POST /v1/nodes/{node_id}/stop
DELETE /v1/nodes/{node_id}

# Proxy RPC calls through node
POST /v1/nodes/{node_id}/rpc
{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}
```

### Supported Chains for Node Deployment

| Chain | Networks | Docker Image |
|-------|----------|--------------|
| Ethereum | mainnet, sepolia, holesky | ethereum/client-go:stable |
| Bitcoin | mainnet, testnet | kylemanna/bitcoind:latest |
| Solana | mainnet, devnet | solanalabs/solana:stable |
| Polygon | mainnet | maticnetwork/bor:latest |
| Arbitrum | mainnet | offchainlabs/nitro-node:latest |
| Base | mainnet | us-docker.pkg.dev/oplabs-tools-artifacts/images/op-node:latest |

### Node Deployment Features

- **Dynamic Port Allocation**: Each node gets unique RPC/WS ports (8545, 8555, 8565...)
- **Auto-Discovery**: API discovers existing bootnode containers on restart via Docker labels
- **Real Metrics**: CPU/memory usage from Docker stats API
- **Container Lifecycle**: Start, stop, delete via API
- **RPC Proxy**: Forward JSON-RPC calls to deployed nodes

### Docker Integration

The API container requires Docker socket access to manage nodes:

```yaml
# compose.yml
api:
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

Nodes are labeled for discovery:
- `bootnode.managed=true`
- `bootnode.chain=ethereum`
- `bootnode.network=sepolia`
- `bootnode.node_id={uuid}`

## White-Label Branding System

### Overview
The frontend supports automatic white-labeling based on domain or environment variable. All user-facing text, logos, and URLs are brand-aware.

### Brand Configuration Files
- `web/lib/brand.ts` - Runtime brand detection and configuration
- `web/lib/docs-config.ts` - Brand-aware documentation URLs
- `web/components/brand-logo.tsx` - Theme-aware logo component
- `brand/config.ts` - Standalone brand package exports

### Supported Brands

| Brand | Domain | IAM | Environment Variable |
|-------|--------|-----|---------------------|
| Hanzo Web3 | web3.hanzo.ai | hanzo.id | `NEXT_PUBLIC_BRAND=hanzo` (default) |
| Lux Cloud | lux.cloud | lux.id | `NEXT_PUBLIC_BRAND=lux` |
| Zoo Labs | web3.zoo.ngo | zoo.id | `NEXT_PUBLIC_BRAND=zoo` |
| Bootnode | bootno.de | hanzo.id | `NEXT_PUBLIC_BRAND=bootnode` |

### Auto-Detection
Brand is automatically detected from the deployment domain:
- `*.hanzo.ai` → Hanzo Web3
- `*.lux.cloud` or `*.lux.network` → Lux Cloud
- `*.zoo.ngo` or `*.zoo.id` → Zoo Labs
- `*.bootno.de` → Bootnode
- `localhost` → Hanzo Web3 (default)

### Usage in Components
```tsx
import { getBrand } from "@/lib/brand"
const brand = getBrand()

// In JSX
<h1>Welcome to {brand.name}</h1>
<a href={brand.social.twitter}>Twitter</a>
<p>Support: support@{brand.domain}</p>
```

### Logo Component
```tsx
import { BrandLogo } from "@/components/brand-logo"

<BrandLogo size="large" showText={true} />
```

### Adding New White-Label Brands
1. Add brand config to `web/lib/brand.ts` brands object
2. Add domain detection rule in `getBrandKey()` function
3. Add logo files to `web/public/logo/{brand}-*.svg`
4. Deploy with appropriate domain or `NEXT_PUBLIC_BRAND` env var

## Hanzo Commerce Billing Integration (2026-02-10)

### Architecture
Billing goes through Hanzo Commerce (Go service, `commerce.hanzo.ai`) which handles payment processing via Square. Bootnode is a client of Commerce — it never talks to payment processors directly.

```
User → Dashboard → POST /v1/billing/checkout → Bootnode API → Commerce /api/v1/checkout/authorize → Square
                 → GET  /v1/billing/account  → Bootnode API → Commerce /api/v1/user → user+subscription

Commerce Webhooks → POST /v1/billing/webhooks/commerce
  → verify HMAC signature → update local DB → invalidate Redis cache

Usage: API request → Redis CU counter → hourly sync → Commerce /api/v1/subscriptions/:id/usage
```

### Commerce Service
- **URL**: `https://commerce.hanzo.ai` (K8s: `commerce.hanzo.svc:8001`)
- **Image**: `hanzoai/commerce:latest` (Docker Hub, multi-arch)
- **K8s**: hanzo-k8s cluster, namespace `hanzo`, `emptyDir` (stateless, no PVC)
- **DB**: SQLite on emptyDir (bridged from legacy GAE Cloud Datastore model layer)
- **Auth**: JWT access tokens per org (test-secret, test-published, live-secret, live-published)
- **Source**: `~/work/hanzo/commerce/`

### Generic Env Vars (Commerce infra)
| Var | Paradigm | Backing | Priority |
|---|---|---|---|
| `KV_URL` | Key-value | Redis/Valkey | `KV_URL` > `REDIS_URL` > `VALKEY_URL` > `VALKEY_ADDR` |
| `S3_URL` | Object storage | MinIO/S3 | `S3_URL` > `S3_ENDPOINT`+keys > `MINIO_*` |
| `DATASTORE_URL` | Analytics/OLAP | ClickHouse | `DATASTORE_URL` > `COMMERCE_DATASTORE` |
| `DOC_URL` | Document DB | FerretDB (PG-backed) | Future |
| `SQL_URL` | Relational | PostgreSQL | Future |

### Commerce API Endpoints (used by Bootnode)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/checkout/authorize` | POST | Authorize payment via Square (nonce) |
| `/api/v1/checkout/capture/:orderid` | POST | Capture authorized payment |
| `/api/v1/checkout/charge` | POST | Single-step charge |
| `/api/v1/subscribe` | POST | Create subscription |
| `/api/v1/subscribe/:id` | GET | Get subscription |
| `/api/v1/subscribe/:id` | PATCH | Update subscription |
| `/api/v1/subscribe/:id` | DELETE | Cancel subscription |
| `/api/v1/user` | GET | Get user + subscription data |
| `/api/v1/order` | GET | List orders |
| `/health` | GET | Health check |

### Bootnode Billing Key Files
- `api/bootnode/core/billing/commerce.py` — httpx client for Commerce API
- `api/bootnode/core/billing/webhooks.py` — Commerce webhook handler (HMAC verified)
- `api/bootnode/core/billing/unified.py` — IAM + Commerce integration (links users)
- `api/bootnode/core/billing/sync.py` — Usage sync worker (reports CU to Commerce)
- `api/bootnode/core/billing/compute_units.py` — CU calculation (payment-agnostic)
- `api/bootnode/core/billing/tiers.py` — Tier definitions (Free/PAYG/Growth/Enterprise)
- `api/bootnode/core/billing/tracker.py` — Redis-based usage tracking
- `api/bootnode/core/billing/service.py` — Billing service orchestration

### Bootnode Billing API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/billing/checkout` | POST | Create checkout via Commerce → Square |
| `/v1/billing/checkout/capture/:order_id` | POST | Capture via Commerce |
| `/v1/billing/account` | GET | Unified IAM + Commerce account |
| `/v1/billing/account/subscriptions` | GET | Subscriptions from Commerce |
| `/v1/billing/account/invoices` | GET | Invoices from Commerce |
| `/v1/billing/account/payment-methods` | GET | Payment methods (Square) |
| `/v1/billing/webhooks/commerce` | POST | Commerce webhook receiver |
| `/v1/billing/sync` | POST | Manual usage sync to Commerce |
| `/v1/billing/sync/status` | GET | Sync worker status |
| `/v1/billing/usage` | GET | Local usage (Redis/ClickHouse) |
| `/v1/billing/tiers` | GET | Tier definitions (no Commerce dependency) |

### Config (env vars)
```
HANZO_COMMERCE_URL=https://commerce.hanzo.ai
HANZO_COMMERCE_API_KEY=eyJ0eXAi...  (from Commerce seed)
HANZO_COMMERCE_WEBHOOK_SECRET=...
```

### Commerce Seed Data (org: bootnode)
- **Org ID**: `AWhEeDNQO8jjrboh3`
- **Plans**: bootnode-free ($0), bootnode-payg ($0 + metered), bootnode-growth ($49), bootnode-enterprise ($0)
- **API Keys**: test-secret, test-published, live-secret, live-published
- **Square Config**: from env vars (SQUARE_APPLICATION_ID, SQUARE_ACCESS_TOKEN, SQUARE_LOCATION_ID)

### What Was Removed
- All Stripe SDK code (`stripe_client.py`, `stripe_webhooks.py`, `stripe_products.py`)
- `setup_stripe.py` script
- Stripe config vars (stripe_secret_key, stripe_publishable_key, etc.)
- `stripe>=11.0.0` dependency from pyproject.toml
- `/v1/billing/portal`, `/v1/billing/webhooks/stripe`, `/v1/billing/stripe/*` endpoints

## Hanzo IAM / OAuth Configuration (2026-02-12)

### IAM Backend
- **Provider**: Casdoor (not Zitadel)
- **Backend URL**: `https://iam.hanzo.ai` (K8s service)
- **Frontend URL**: `https://hanzo.id` (Cloudflare Pages + middleware proxy)
- **Middleware**: `/Users/z/work/hanzo/hanzo.id/functions/_middleware.ts` proxies auth paths to IAM

### OAuth Flow for Console
- **Provider**: Custom `HanzoIamProvider` in `console/packages/shared/src/server/auth/hanzoIamProvider.ts`
- **Type**: `oauth` (NOT `oidc` — Casdoor JWT tokens have iss claims that openid-client rejects)
- **Key settings**: `idToken: false`, `checks: ["state"]`, custom `token.request` function
- **Token endpoint**: `${serverUrl}/oauth/token`
- **Userinfo endpoint**: `${serverUrl}/api/userinfo`
- **Console env**: `IAM_SERVER_URL=https://hanzo.id`, `IAM_CLIENT_ID=hanzo-console-client-id`

### Casdoor Applications (in iam-init-data configmap)
| App | Display | Homepage |
|-----|---------|----------|
| app-console | Hanzo Console | console.hanzo.ai |
| app-hanzobot | HanzoBot | bot.hanzo.ai |
| app-cloud | Hanzo Cloud | cloud.hanzo.ai |
| app-hanzo | Hanzo | hanzo.ai |

### Critical Lesson
Never set `issuer` on a `type: "oauth"` NextAuth provider pointing at Casdoor. This triggers OIDC discovery which overrides explicit endpoint URLs and causes JWT `iss` validation failures. Use a custom `token.request` function to bypass openid-client's JWT validation.

## Hanzo Bot Deployment (2026-02-12)

### npm Package
- **Name**: `@hanzo/bot` (scoped, public)
- **Registry**: https://www.npmjs.com/package/@hanzo/bot
- **Version**: Calendar-based (YYYY.M.D format, e.g., 2026.2.10)

### GitHub Release
- **Repo**: hanzoai/bot
- **Workflow**: `.github/workflows/release.yml` (triggers on `v*` tags or workflow_dispatch)
- **Steps**: pnpm build → release:check (validates plugin versions match) → npm publish → GitHub Release
- **Important**: Run `pnpm plugins:sync` before tagging — extensions must match root version

### Branding
- **Install.sh**: `curl -fsSL https://hanzo.bot/install.sh | bash`
- **Env prefix**: `HANZO_BOT_` (not `BOTBOT_`)
- **Emoji**: Ninja (🥷) theme (not lobster/crab)
- **Tagline**: "Your AI team, deployed everywhere."

### Sites
- **hanzo.bot** → Landing page (hanzobot/site, Astro, K8s deploy)
- **app.hanzo.bot** → Bot dashboard
- **hanzo.id** → IAM/login (Casdoor via CF Pages middleware)

## Hanzo Gateway Routes (2026-02-12)

### Gateway Technology
- **Engine**: KrakenD v3 (Go-based API gateway)
- **Config**: `~/work/hanzo/gateway/configs/hanzo/gateway.json`
- **Domain**: `api.hanzo.ai`
- **K8s**: 2 replicas, ghcr.io/hanzoai/gateway:hanzo-latest

### Configured Routes
| Prefix | Backend | Service |
|--------|---------|---------|
| `/v1/chat/completions` | cloud-api.hanzo.svc:8000 | LLM Inference |
| `/v1/models` | inference.do-ai.run | Model listing |
| `/v1/embeddings` | inference.do-ai.run | Embeddings |
| `/v1/images/*` | inference.do-ai.run | Image generation |
| `/v1/audio/*` | inference.do-ai.run | Audio TTS/STT |
| `/cloud/{path}` | cloud-api.hanzo.svc:8000 | Cloud API |
| `/commerce/{path}` | commerce.hanzo.svc:8001 | Commerce/Billing |
| `/auth/{path}` | iam.hanzo.svc:8000 | IAM/Auth |
| `/analytics/{path}` | analytics.hanzo.svc:80 | Analytics |
| `/bot/{path}` | bot-gateway.hanzo.svc:80 | Bot/Operative |
| `/operative/{path}` | operative.hanzo.svc:80 | Operative |
| `/kms/{path}` | kms.hanzo.svc:80 | Key Management |
| `/agents/{path}` | agents.hanzo.svc:8080 | Agent Framework |
| `/console/{path}` | console.hanzo.svc:80 | Console |
| `/web3/{path}` | bootnode-api.bootnode.svc:80 | Web3/Blockchain |

### Console Billing — Provider-Agnostic (2026-02-12)
- All Stripe SDK references purged from console codebase
- Billing delegated to Hanzo Commerce service via HTTP API
- tRPC procedures renamed: `createStripeCheckoutSession` → `createCheckoutSession`, etc.
- `cloudConfig.stripe.*` DB fields preserved (require migration to rename)
- All old exports kept as `@deprecated` aliases for backward compatibility
- Key file: `console/web/src/ee/features/billing/server/billingService.ts`
