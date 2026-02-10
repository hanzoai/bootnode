// DOKS (DigitalOcean Kubernetes Service) region coordinates and types
// Used by fleet-map.tsx to position validator nodes on the world map

export interface DOKSRegion {
  name: string
  lat: number
  lng: number
  country: string
}

export const DOKS_REGIONS: Record<string, DOKSRegion> = {
  nyc1: { name: "New York 1", lat: 40.7128, lng: -74.006, country: "US" },
  nyc2: { name: "New York 2", lat: 40.7128, lng: -74.006, country: "US" },
  nyc3: { name: "New York 3", lat: 40.7128, lng: -74.006, country: "US" },
  sfo2: { name: "San Francisco 2", lat: 37.7749, lng: -122.4194, country: "US" },
  sfo3: { name: "San Francisco 3", lat: 37.7749, lng: -122.4194, country: "US" },
  lon1: { name: "London 1", lat: 51.5074, lng: -0.1278, country: "GB" },
  ams3: { name: "Amsterdam 3", lat: 52.3676, lng: 4.9041, country: "NL" },
  fra1: { name: "Frankfurt 1", lat: 50.1109, lng: 8.6821, country: "DE" },
  tor1: { name: "Toronto 1", lat: 43.6532, lng: -79.3832, country: "CA" },
  sgp1: { name: "Singapore 1", lat: 1.3521, lng: 103.8198, country: "SG" },
  blr1: { name: "Bangalore 1", lat: 12.9716, lng: 77.5946, country: "IN" },
  syd1: { name: "Sydney 1", lat: -33.8688, lng: 151.2093, country: "AU" },
  atl1: { name: "Atlanta 1", lat: 33.749, lng: -84.388, country: "US" },
}

export type NodeStatus = "healthy" | "syncing" | "degraded" | "available"

export interface FleetRegionInfo {
  regionId: string
  region: DOKSRegion
  status: NodeStatus
  fleetName?: string
  validatorCount: number
  blockHeight?: number
  healthPct?: number
}

export interface LuxFleet {
  id: string
  name: string
  region: string
  status: "running" | "deploying" | "degraded" | "stopped"
  validators: number
  blockHeight?: number
  healthPct?: number
  createdAt?: string
}

/** Map fleet status to node visual status */
export function fleetStatusToNodeStatus(s: LuxFleet["status"]): NodeStatus {
  switch (s) {
    case "running":
      return "healthy"
    case "deploying":
      return "syncing"
    case "degraded":
      return "degraded"
    default:
      return "available"
  }
}

/** Auth headers for API calls -- matches existing pattern in infrastructure/page.tsx */
export function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {}
  const token = localStorage.getItem("bootnode_token")
  const apiKey = localStorage.getItem("bootnode_api_key")
  if (token) return { Authorization: `Bearer ${token}` }
  if (apiKey) return { "X-API-Key": apiKey }
  return {}
}
