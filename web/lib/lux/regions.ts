// DigitalOcean Kubernetes regions and Lux network configuration
// Used by the fleet management UI for cluster provisioning and monitoring.

// ---------------------------------------------------------------------------
// DOKS Regions
// ---------------------------------------------------------------------------

export interface DOKSRegion {
  slug: string;
  name: string;
  city: string;
  country: string;
  lat: number;
  lon: number;
  available: boolean;
}

export const DOKS_REGIONS: DOKSRegion[] = [
  { slug: "nyc1", name: "New York 1",      city: "New York",      country: "US", lat:  40.7128, lon:  -74.0060, available: true },
  { slug: "nyc3", name: "New York 3",      city: "New York",      country: "US", lat:  40.7128, lon:  -74.0060, available: true },
  { slug: "sfo2", name: "San Francisco 2", city: "San Francisco", country: "US", lat:  37.7749, lon: -122.4194, available: true },
  { slug: "sfo3", name: "San Francisco 3", city: "San Francisco", country: "US", lat:  37.7749, lon: -122.4194, available: true },
  { slug: "lon1", name: "London 1",        city: "London",        country: "UK", lat:  51.5074, lon:   -0.1278, available: true },
  { slug: "ams3", name: "Amsterdam 3",     city: "Amsterdam",     country: "NL", lat:  52.3676, lon:    4.9041, available: true },
  { slug: "fra1", name: "Frankfurt 1",     city: "Frankfurt",     country: "DE", lat:  50.1109, lon:    8.6821, available: true },
  { slug: "tor1", name: "Toronto 1",       city: "Toronto",       country: "CA", lat:  43.6532, lon:  -79.3832, available: true },
  { slug: "sgp1", name: "Singapore 1",     city: "Singapore",     country: "SG", lat:   1.3521, lon:  103.8198, available: true },
  { slug: "blr1", name: "Bangalore 1",     city: "Bangalore",     country: "IN", lat:  12.9716, lon:   77.5946, available: true },
  { slug: "syd1", name: "Sydney 1",        city: "Sydney",        country: "AU", lat: -33.8688, lon:  151.2093, available: true },
];

/** Look up a region by slug, returns undefined if not found. */
export function getRegion(slug: string): DOKSRegion | undefined {
  return DOKS_REGIONS.find((r) => r.slug === slug);
}

// ---------------------------------------------------------------------------
// Lux Network Configuration
// ---------------------------------------------------------------------------

export type LuxNetwork = "mainnet" | "testnet" | "devnet";

export interface LuxNetworkConfig {
  networkId: number;
  chainId: number;
  httpPort: number;
  stakingPort: number;
  namespace: string;
  color: string;
}

export const NETWORK_CONFIGS: Record<LuxNetwork, LuxNetworkConfig> = {
  mainnet: { networkId: 1, chainId: 96369, httpPort: 9630, stakingPort: 9631, namespace: "lux-mainnet", color: "#0066FF" },
  testnet: { networkId: 2, chainId: 96368, httpPort: 9640, stakingPort: 9641, namespace: "lux-testnet", color: "#00CC66" },
  devnet:  { networkId: 3, chainId: 96370, httpPort: 9650, stakingPort: 9651, namespace: "lux-devnet",  color: "#FF6600" },
};

export const NETWORK_NAMES: LuxNetwork[] = ["mainnet", "testnet", "devnet"] as const;

// ---------------------------------------------------------------------------
// API Client Helpers
// ---------------------------------------------------------------------------

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function authHeaders(): HeadersInit {
  const headers: HeadersInit = { "Content-Type": "application/json" };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

async function request<T = unknown>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** List all fleets, optionally filtered by cluster. */
export async function fetchFleets(clusterId?: string) {
  const qs = clusterId ? `?clusterId=${encodeURIComponent(clusterId)}` : "";
  return request(`/api/fleets${qs}`);
}

/** Get a single fleet by cluster + network. */
export async function fetchFleet(clusterId: string, network: LuxNetwork) {
  return request(`/api/fleets/${encodeURIComponent(clusterId)}/${network}`);
}

/** Create a new fleet. */
export async function createFleet(params: Record<string, unknown>) {
  return request("/api/fleets", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

/** Update an existing fleet. */
export async function updateFleet(
  clusterId: string,
  network: LuxNetwork,
  params: Record<string, unknown>,
) {
  return request(`/api/fleets/${encodeURIComponent(clusterId)}/${network}`, {
    method: "PUT",
    body: JSON.stringify(params),
  });
}

/** Delete a fleet. */
export async function deleteFleet(clusterId: string, network: LuxNetwork) {
  return request(`/api/fleets/${encodeURIComponent(clusterId)}/${network}`, {
    method: "DELETE",
  });
}

/** Scale a fleet to the given replica count. */
export async function scaleFleet(
  clusterId: string,
  network: LuxNetwork,
  replicas: number,
) {
  return request(`/api/fleets/${encodeURIComponent(clusterId)}/${network}/scale`, {
    method: "POST",
    body: JSON.stringify({ replicas }),
  });
}

/** Restart all nodes in a fleet. */
export async function restartFleet(clusterId: string, network: LuxNetwork) {
  return request(`/api/fleets/${encodeURIComponent(clusterId)}/${network}/restart`, {
    method: "POST",
  });
}

/** Fetch aggregate stats across all fleets. */
export async function fetchStats() {
  return request("/api/stats");
}

/** Fetch available Lux networks. */
export async function fetchNetworks() {
  return request("/api/networks");
}
