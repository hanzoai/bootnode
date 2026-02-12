# Bootnode Cloud API - ZAP Schema
# High-performance blockchain infrastructure for AI agents
# Connect via: zap://api.bootno.de:9999

# =============================================================================
# Core Types
# =============================================================================

struct ChainConfig
  name Text
  slug Text
  chainId UInt64
  network Text
  isTestnet Bool

struct Timestamp
  seconds Int64
  nanos UInt32

struct Metadata
  entries List(Entry)

  struct Entry
    key Text
    value Text

# =============================================================================
# RPC Types
# =============================================================================

struct RPCRequest
  chain Text
  network Text = "mainnet"
  method Text
  params List(Data)

struct RPCResponse
  result Data
  error Text
  latencyMs UInt32

# =============================================================================
# Token Types
# =============================================================================

struct TokenBalance
  contractAddress Text
  symbol Text
  name Text
  decimals UInt32
  balance Text
  balanceFormatted Float64
  priceUsd Float64
  valueUsd Float64

struct TokenMetadata
  contractAddress Text
  symbol Text
  name Text
  decimals UInt32
  totalSupply Text
  logoUri Text

struct TokenBalanceList
  balances List(TokenBalance)
  chain Text
  network Text

# =============================================================================
# NFT Types
# =============================================================================

struct NFTAttribute
  traitType Text
  value Text
  displayType Text

struct NFTMetadata
  contractAddress Text
  tokenId Text
  name Text
  description Text
  imageUri Text
  animationUri Text
  externalUrl Text
  attributes List(NFTAttribute)

struct NFTList
  nfts List(NFTMetadata)
  chain Text
  network Text
  total UInt32

# =============================================================================
# Smart Wallet Types (ERC-4337)
# =============================================================================

struct SmartWallet
  address Text
  owner Text
  chain Text
  network Text
  isDeployed Bool
  nonce UInt64
  entryPoint Text
  factory Text

struct UserOperation
  sender Text
  nonce UInt64
  initCode Data
  callData Data
  callGasLimit UInt64
  verificationGasLimit UInt64
  preVerificationGas UInt64
  maxFeePerGas UInt64
  maxPriorityFeePerGas UInt64
  paymasterAndData Data
  signature Data

struct UserOperationReceipt
  userOpHash Text
  transactionHash Text
  success Bool
  reason Text
  actualGasCost UInt64
  actualGasUsed UInt64

# =============================================================================
# Webhook Types
# =============================================================================

enum WebhookEventType
  addressActivity
  tokenTransfer
  nftTransfer
  contractEvent
  newBlock
  pendingTransaction

struct Webhook
  id Text
  url Text
  eventType WebhookEventType
  chain Text
  network Text
  active Bool
  filters WebhookFilters
  createdAt Timestamp

struct WebhookFilters
  addresses List(Text)
  topics List(Text)
  contractAddresses List(Text)

struct WebhookList
  webhooks List(Webhook)
  total UInt32

# =============================================================================
# Gas Types
# =============================================================================

struct GasEstimate
  chain Text
  network Text
  gasPrice Text
  maxFee Text
  maxPriorityFee Text
  baseFee Text
  estimatedTime UInt32

# =============================================================================
# Server Info
# =============================================================================

struct ServerInfo
  name Text
  version Text
  capabilities Capabilities

  struct Capabilities
    tools Bool
    resources Bool
    prompts Bool
    logging Bool

struct ClientInfo
  name Text
  version Text

# =============================================================================
# Tool Interface
# =============================================================================

struct Tool
  name Text
  description Text
  schema Data
  annotations Metadata

struct ToolList
  tools List(Tool)

struct ToolCall
  id Text
  name Text
  args Data
  metadata Metadata

struct ToolResult
  id Text
  content Data
  error Text
  metadata Metadata

# =============================================================================
# Resource Interface
# =============================================================================

struct Resource
  uri Text
  name Text
  description Text
  mimeType Text
  annotations Metadata

struct ResourceList
  resources List(Resource)

struct ResourceContent
  uri Text
  mimeType Text
  union content
    text Text
    blob Data

# =============================================================================
# Main Bootnode Interface
# =============================================================================

interface Bootnode
  # Connection
  init (client ClientInfo) -> (server ServerInfo)

  # Tool operations (MCP-compatible)
  listTools () -> (tools ToolList)
  callTool (call ToolCall) -> (result ToolResult)

  # Resource operations (MCP-compatible)
  listResources () -> (resources ResourceList)
  readResource (uri Text) -> (content ResourceContent)

  # RPC - Direct blockchain access
  rpcCall (request RPCRequest) -> (response RPCResponse)
  rpcBatch (requests List(RPCRequest)) -> (responses List(RPCResponse))

  # Tokens - ERC-20 APIs
  getTokenBalances (address Text, chain Text, network Text) -> (balances TokenBalanceList)
  getTokenMetadata (contract Text, chain Text, network Text) -> (metadata TokenMetadata)

  # NFTs - ERC-721/1155 APIs
  getNFTsOwned (address Text, chain Text, network Text) -> (nfts NFTList)
  getNFTMetadata (contract Text, tokenId Text, chain Text, network Text) -> (metadata NFTMetadata)

  # Smart Wallets - ERC-4337
  createWallet (owner Text, chain Text, network Text) -> (wallet SmartWallet)
  getWallet (address Text, chain Text, network Text) -> (wallet SmartWallet)
  sendUserOperation (op UserOperation, chain Text, network Text) -> (hash Text)
  getUserOperationReceipt (hash Text, chain Text, network Text) -> (receipt UserOperationReceipt)

  # Webhooks
  createWebhook (url Text, eventType WebhookEventType, chain Text, network Text, filters WebhookFilters) -> (webhook Webhook)
  listWebhooks () -> (webhooks WebhookList)
  deleteWebhook (id Text) -> (success Bool)

  # Gas
  estimateGas (chain Text, network Text) -> (estimate GasEstimate)

  # Chains
  listChains () -> (chains List(ChainConfig))
  getChain (slug Text) -> (chain ChainConfig)

  # Logging
  log (level LogLevel, message Text, data Data) -> ()

  enum LogLevel
    debug
    info
    warn
    error
