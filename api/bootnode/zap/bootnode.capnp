@0x910d483065cfe07c;

# Bootnode Cloud API - ZAP Schema
# High-performance blockchain infrastructure for AI agents
# Connect via: zap://api.bootno.de:9999
# =============================================================================
# Core Types
# =============================================================================
struct ChainConfig @0xb511f1e1d89fa8af {
  name @0 :Text;
  slug @1 :Text;
  chainId @2 :UInt64;
  network @3 :Text;
  isTestnet @4 :Bool;
}

struct Timestamp @0xfc34fff2290e18c7 {
  seconds @0 :Int64;
  nanos @1 :UInt32;
}

struct Metadata @0x9bebd03db05e8bce {
  entries @0 :List(Entry);
  struct Entry @0xe7ec9d8ce9709d49 {
    key @0 :Text;
    value @1 :Text;
  }

}

# =============================================================================
# RPC Types
# =============================================================================
struct RPCRequest @0xff9cffed18477c91 {
  chain @0 :Text;
  network @1 :Text = "mainnet";
  method @2 :Text;
  params @3 :List(Data);
}

struct RPCResponse @0xa12731311ba9cd5a {
  result @0 :Data;
  error @1 :Text;
  latencyMs @2 :UInt32;
}

# =============================================================================
# Token Types
# =============================================================================
struct TokenBalance @0xcd970c1c5230d11f {
  contractAddress @0 :Text;
  symbol @1 :Text;
  name @2 :Text;
  decimals @3 :UInt32;
  balance @4 :Text;
  balanceFormatted @5 :Float64;
  priceUsd @6 :Float64;
  valueUsd @7 :Float64;
}

struct TokenMetadata @0x89fb0e8fbf28db1c {
  contractAddress @0 :Text;
  symbol @1 :Text;
  name @2 :Text;
  decimals @3 :UInt32;
  totalSupply @4 :Text;
  logoUri @5 :Text;
}

struct TokenBalanceList @0xe6890bce0c8b7517 {
  balances @0 :List(TokenBalance);
  chain @1 :Text;
  network @2 :Text;
}

# =============================================================================
# NFT Types
# =============================================================================
struct NFTAttribute @0x9d67f54c60b654f2 {
  traitType @0 :Text;
  value @1 :Text;
  displayType @2 :Text;
}

struct NFTMetadata @0x9a74c009ecc4956a {
  contractAddress @0 :Text;
  tokenId @1 :Text;
  name @2 :Text;
  description @3 :Text;
  imageUri @4 :Text;
  animationUri @5 :Text;
  externalUrl @6 :Text;
  attributes @7 :List(NFTAttribute);
}

struct NFTList @0xaa3e8f9cd480bcad {
  nfts @0 :List(NFTMetadata);
  chain @1 :Text;
  network @2 :Text;
  total @3 :UInt32;
}

# =============================================================================
# Smart Wallet Types (ERC-4337)
# =============================================================================
struct SmartWallet @0xb6c7bb97622c76a1 {
  address @0 :Text;
  owner @1 :Text;
  chain @2 :Text;
  network @3 :Text;
  isDeployed @4 :Bool;
  nonce @5 :UInt64;
  entryPoint @6 :Text;
  factory @7 :Text;
}

struct UserOperation @0xd04ead91cb7c6b36 {
  sender @0 :Text;
  nonce @1 :UInt64;
  initCode @2 :Data;
  callData @3 :Data;
  callGasLimit @4 :UInt64;
  verificationGasLimit @5 :UInt64;
  preVerificationGas @6 :UInt64;
  maxFeePerGas @7 :UInt64;
  maxPriorityFeePerGas @8 :UInt64;
  paymasterAndData @9 :Data;
  signature @10 :Data;
}

struct UserOperationReceipt @0xea8c5e896f750df1 {
  userOpHash @0 :Text;
  transactionHash @1 :Text;
  success @2 :Bool;
  reason @3 :Text;
  actualGasCost @4 :UInt64;
  actualGasUsed @5 :UInt64;
}

# =============================================================================
# Webhook Types
# =============================================================================
enum WebhookEventType @0xbf71b28ebf7c0502 {
  addressActivity @0;
  tokenTransfer @1;
  nftTransfer @2;
  contractEvent @3;
  newBlock @4;
  pendingTransaction @5;
}

struct Webhook @0xd13fcfaa0d485f98 {
  id @0 :Text;
  url @1 :Text;
  eventType @2 :WebhookEventType;
  chain @3 :Text;
  network @4 :Text;
  active @5 :Bool;
  filters @6 :WebhookFilters;
  createdAt @7 :Timestamp;
}

struct WebhookFilters @0xd5fac19b2b2a1254 {
  addresses @0 :List(Text);
  topics @1 :List(Text);
  contractAddresses @2 :List(Text);
}

struct WebhookList @0xaf94ec9f28010a65 {
  webhooks @0 :List(Webhook);
  total @1 :UInt32;
}

# =============================================================================
# Gas Types
# =============================================================================
struct GasEstimate @0xcf670c46f9f17833 {
  chain @0 :Text;
  network @1 :Text;
  gasPrice @2 :Text;
  maxFee @3 :Text;
  maxPriorityFee @4 :Text;
  baseFee @5 :Text;
  estimatedTime @6 :UInt32;
}

# =============================================================================
# Server Info
# =============================================================================
struct ServerInfo @0x8f550a5bec9ab424 {
  name @0 :Text;
  version @1 :Text;
  capabilities @2 :Capabilities;
  struct Capabilities @0xee2961376a4ac07c {
    tools @0 :Bool;
    resources @1 :Bool;
    prompts @2 :Bool;
    logging @3 :Bool;
  }

}

struct ClientInfo @0xc430302c4544aa0e {
  name @0 :Text;
  version @1 :Text;
}

# =============================================================================
# Tool Interface
# =============================================================================
struct Tool @0x90fdd8e6f5e64b1e {
  name @0 :Text;
  description @1 :Text;
  schema @2 :Data;
  annotations @3 :Metadata;
}

struct ToolList @0xa7a259e334721959 {
  tools @0 :List(Tool);
}

struct ToolCall @0x92892f3229dafcf3 {
  id @0 :Text;
  name @1 :Text;
  args @2 :Data;
  metadata @3 :Metadata;
}

struct ToolResult @0x8e4b4994ce992ac8 {
  id @0 :Text;
  content @1 :Data;
  error @2 :Text;
  metadata @3 :Metadata;
}

# =============================================================================
# Resource Interface
# =============================================================================
struct Resource @0xdfa86c7ffc9628e4 {
  uri @0 :Text;
  name @1 :Text;
  description @2 :Text;
  mimeType @3 :Text;
  annotations @4 :Metadata;
}

struct ResourceList @0x8fcb7d5ee1450b49 {
  resources @0 :List(Resource);
}

struct ResourceContent @0xc5f4c7b76d45b83b {
  uri @0 :Text;
  mimeType @1 :Text;
  content :union {
    text @2 :Text;
    blob @3 :Data;
  }
}

# =============================================================================
# Main Bootnode Interface
# =============================================================================
interface Bootnode @0xadbe8d0aa6c04798 {
  init @0 (client :ClientInfo) -> (server :ServerInfo);
  listTools @1 () -> (tools :ToolList);
  callTool @2 (call :ToolCall) -> (result :ToolResult);
  listResources @3 () -> (resources :ResourceList);
  readResource @4 (uri :Text) -> (content :ResourceContent);
  rpcCall @5 (request :RPCRequest) -> (response :RPCResponse);
  rpcBatch @6 (requests :List(RPCRequest)) -> (responses :List(RPCResponse));
  getTokenBalances @7 (address :Text, chain :Text, network :Text) -> (balances :TokenBalanceList);
  getTokenMetadata @8 (contract :Text, chain :Text, network :Text) -> (metadata :TokenMetadata);
  getNFTsOwned @9 (address :Text, chain :Text, network :Text) -> (nfts :NFTList);
  getNFTMetadata @10 (contract :Text, tokenId :Text, chain :Text, network :Text) -> (metadata :NFTMetadata);
  createWallet @11 (owner :Text, chain :Text, network :Text) -> (wallet :SmartWallet);
  getWallet @12 (address :Text, chain :Text, network :Text) -> (wallet :SmartWallet);
  sendUserOperation @13 (op :UserOperation, chain :Text, network :Text) -> (hash :Text);
  getUserOperationReceipt @14 (hash :Text, chain :Text, network :Text) -> (receipt :UserOperationReceipt);
  createWebhook @15 (url :Text, eventType :WebhookEventType, chain :Text, network :Text, filters :WebhookFilters) -> (webhook :Webhook);
  listWebhooks @16 () -> (webhooks :WebhookList);
  deleteWebhook @17 (id :Text) -> (success :Bool);
  estimateGas @18 (chain :Text, network :Text) -> (estimate :GasEstimate);
  listChains @19 () -> (chains :List(ChainConfig));
  getChain @20 (slug :Text) -> (chain :ChainConfig);
  log @21 (level :LogLevel, message :Text, data :Data) -> ();
  enum LogLevel @0xf191386de21db6f3 {
    debug @0;
    info @1;
    warn @2;
    error @3;
  }

}

