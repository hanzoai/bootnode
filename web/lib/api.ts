// Bootnode API Client
// Uses auth token from localStorage for authenticated requests

const getApiConfig = () => {
  let API_URL = "http://localhost:8000"

  if (typeof window !== 'undefined') {
    API_URL = process.env.NEXT_PUBLIC_API_URL ||
              (window as any).__BOOTNODE_API_URL__ ||
              localStorage.getItem("bootnode_api_url") ||
              API_URL
  }

  return { API_URL }
}

const getAuthToken = () => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem("bootnode_token")
}

const getApiKey = () => {
  if (typeof window === 'undefined') return null
  return localStorage.getItem("bootnode_api_key")
}

export async function api<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const { API_URL } = getApiConfig()
  const token = getAuthToken()
  const apiKey = getApiKey()

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...options?.headers as Record<string, string>,
  }

  // Use auth token if available, otherwise fall back to API key
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  } else if (apiKey) {
    headers["X-API-Key"] = apiKey
  }

  const res = await fetch(`${API_URL}/v1${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `API error ${res.status}`)
  }

  return res.json()
}

// Auth / Projects
export const auth = {
  createProject: (data: { name: string; owner_id: string }) =>
    api("/auth/projects", { method: "POST", body: JSON.stringify(data) }),
  getProject: (id: string) => api(`/auth/projects/${id}`),
  createKey: (data: { project_id: string; name: string; rate_limit?: number }) =>
    api("/auth/keys", { method: "POST", body: JSON.stringify(data) }),
  listKeys: (projectId: string) => api(`/auth/keys?project_id=${projectId}`),
  deleteKey: (keyId: string) => api(`/auth/keys/${keyId}`, { method: "DELETE" }),
}

// Chains
export const chains = {
  list: () => api("/chains"),
  get: (chain: string) => api(`/chains/${chain}`),
}

// RPC
export const rpc = {
  call: (chain: string, network: string, body: { jsonrpc: string; method: string; params: unknown[]; id: number }) =>
    api(`/rpc/${chain}/${network}`, { method: "POST", body: JSON.stringify(body) }),
}

// Wallets
export const wallets = {
  create: (data: { owner_address: string; chain: string; network?: string; salt?: string }) =>
    api("/wallets/create", { method: "POST", body: JSON.stringify(data) }),
  get: (address: string) => api(`/wallets/${address}`),
  list: () => api("/wallets"),
  estimateGas: (address: string, data: unknown) =>
    api(`/wallets/${address}/estimate`, { method: "POST", body: JSON.stringify(data) }),
  getNonce: (address: string) => api(`/wallets/${address}/nonce`),
}

// Webhooks
export const webhooks = {
  create: (data: { name: string; url: string; chain: string; event_type: string; network?: string; filters?: Record<string, unknown> }) =>
    api("/webhooks", { method: "POST", body: JSON.stringify(data) }),
  list: () => api("/webhooks"),
  get: (id: string) => api(`/webhooks/${id}`),
  update: (id: string, data: Partial<{ name: string; url: string; is_active: boolean; filters: Record<string, unknown> }>) =>
    api(`/webhooks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (id: string) => api(`/webhooks/${id}`, { method: "DELETE" }),
  deliveries: (id: string) => api(`/webhooks/${id}/deliveries`),
  test: (id: string) => api(`/webhooks/${id}/test`, { method: "POST" }),
}

// Gas
export const gas = {
  prices: (chain: string) => api(`/gas/${chain}/prices`),
  createPolicy: (data: { name: string; chain: string; network?: string; max_gas_per_op?: number; max_spend_per_day_usd?: number; allowed_contracts?: string[]; allowed_methods?: string[] }) =>
    api("/gas/policies", { method: "POST", body: JSON.stringify(data) }),
  listPolicies: () => api("/gas/policies"),
  getPolicy: (id: string) => api(`/gas/policies/${id}`),
  deletePolicy: (id: string) => api(`/gas/policies/${id}`, { method: "DELETE" }),
  sponsor: (data: unknown) => api("/gas/sponsor", { method: "POST", body: JSON.stringify(data) }),
  estimate: (data: unknown) => api("/gas/estimate", { method: "POST", body: JSON.stringify(data) }),
}

// Tokens
export const tokens = {
  balances: (chain: string, address: string, network?: string) =>
    api(`/tokens/${chain}/balances/${address}${network ? `?network=${network}` : ""}`),
  metadata: (chain: string, contract: string, network?: string) =>
    api(`/tokens/${chain}/metadata/${contract}${network ? `?network=${network}` : ""}`),
}

// NFTs
export const nfts = {
  metadata: (chain: string, contract: string, tokenId: string) =>
    api(`/nfts/${chain}/metadata/${contract}/${tokenId}`),
  collection: (chain: string, contract: string) =>
    api(`/nfts/${chain}/collection/${contract}`),
  owned: (chain: string, address: string, contracts: string[]) =>
    api(`/nfts/${chain}/owned/${address}?contracts=${contracts.join(",")}`),
  refresh: (chain: string, contract: string, tokenId: string) =>
    api(`/nfts/${chain}/refresh/${contract}/${tokenId}`, { method: "POST" }),
}

// Transfers
export const transfers = {
  byAddress: (chain: string, address: string, params?: { from_block?: number; to_block?: number }) => {
    const qs = params ? `?${new URLSearchParams(params as Record<string, string>)}` : ""
    return api(`/transfers/${chain}/address/${address}${qs}`)
  },
  byTx: (chain: string, txHash: string) => api(`/transfers/${chain}/tx/${txHash}`),
  send: (chain: string, data: { signed_tx: string }) =>
    api(`/transfers/${chain}/send`, { method: "POST", body: JSON.stringify(data) }),
}

// Billing
export const billing = {
  getUsage: () => api("/billing/usage"),
  getUsageSummary: (year?: number, month?: number) => {
    const params = year && month ? `?year=${year}&month=${month}` : ""
    return api(`/billing/usage/summary${params}`)
  },
  getSubscription: () => api("/billing/subscription"),
  upgrade: (data: { tier: string; hanzo_subscription_id?: string }) =>
    api("/billing/subscription/upgrade", { method: "POST", body: JSON.stringify(data) }),
  downgrade: (data: { tier: string }) =>
    api("/billing/subscription/downgrade", { method: "POST", body: JSON.stringify(data) }),
  getInvoices: (limit?: number) => api(`/billing/invoices${limit ? `?limit=${limit}` : ""}`),
  getTiers: () => api("/billing/tiers"),
  getTier: (name: string) => api(`/billing/tiers/${name}`),
  checkLimits: () => api("/billing/limits"),
  createCheckout: (data: { tier: string; nonce?: string; source_id?: string; success_url?: string; cancel_url?: string }) =>
    api("/billing/checkout", { method: "POST", body: JSON.stringify(data) }),
  captureCheckout: (orderId: string) =>
    api(`/billing/checkout/capture/${orderId}`, { method: "POST" }),
  syncUsage: () => api("/billing/sync", { method: "POST" }),
  getSyncStatus: () => api("/billing/sync/status"),
  // Unified IAM + Commerce
  getAccount: () => api("/billing/account"),
  getAccountSubscriptions: () => api("/billing/account/subscriptions"),
  getAccountInvoices: () => api("/billing/account/invoices"),
  getPaymentMethods: () => api("/billing/account/payment-methods"),
  syncAccount: () => api("/billing/account/sync", { method: "POST" }),
}

// Team
export const team = {
  list: () => api<{ members: TeamMember[]; total: number }>("/team"),
  invite: (data: { email: string; role: string }) =>
    api<TeamMember>("/team", { method: "POST", body: JSON.stringify(data) }),
  update: (memberId: string, data: { role?: string; name?: string }) =>
    api<TeamMember>(`/team/${memberId}`, { method: "PATCH", body: JSON.stringify(data) }),
  remove: (memberId: string) =>
    api(`/team/${memberId}`, { method: "DELETE" }),
}

// Types
export interface TeamMember {
  id: string
  email: string
  name: string | null
  role: string
  status: string
  avatar: string | null
  joined_at: string | null
  created_at: string
}
