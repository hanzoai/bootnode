"use client"

import { useState, useEffect } from "react"
import {
  Server,
  Search,
  ArrowLeftRight,
  ArrowUpDown,
  ShoppingBag,
  Wallet,
  Shield,
  Droplets,
  Coins,
  Globe,
  Boxes,
  Activity,
  RefreshCw,
  Play,
  Square,
  RotateCw,
  ChevronDown,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Minus,
} from "lucide-react"

interface ServiceInfo {
  name: string
  running: boolean
  replicas: number
  ready_replicas: number
  cpu_usage: number | null
  memory_usage: number | null
  image: string | null
  started_at: string | null
}

interface ServiceCategory {
  name: string
  icon: any
  services: string[]
}

const SERVICE_CATEGORIES: ServiceCategory[] = [
  {
    name: "Core",
    icon: Server,
    services: ["api", "web", "indexer", "bundler", "webhook-worker"],
  },
  {
    name: "Blockchain",
    icon: Boxes,
    services: ["explorer", "graph-node", "bridge", "exchange", "validator", "rpc-proxy", "staking"],
  },
  {
    name: "Security",
    icon: Shield,
    services: ["mpc", "mpc-postgres", "safe", "safe-transaction", "safe-config"],
  },
  {
    name: "Tools",
    icon: Globe,
    services: ["faucet", "market", "gateway", "graph-postgres", "graph-ipfs"],
  },
]

const NETWORKS = ["mainnet", "testnet", "devnet"]

function StatusBadge({ running, ready, total }: { running: boolean; ready: number; total: number }) {
  if (!running && total === 0) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Minus className="h-3 w-3" />
        Not deployed
      </span>
    )
  }
  if (!running) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-red-400">
        <XCircle className="h-3 w-3" />
        Stopped
      </span>
    )
  }
  if (ready < total) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-yellow-400">
        <AlertCircle className="h-3 w-3" />
        Degraded ({ready}/{total})
      </span>
    )
  }
  return (
    <span className="flex items-center gap-1.5 text-xs text-green-400">
      <CheckCircle2 className="h-3 w-3" />
      Running ({ready}/{total})
    </span>
  )
}

export default function ServicesPage() {
  const [services, setServices] = useState<ServiceInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [network, setNetwork] = useState("mainnet")
  const [error, setError] = useState<string | null>(null)

  const fetchServices = async () => {
    try {
      setLoading(true)
      const res = await fetch("/api/v1/infra/services")
      if (res.ok) {
        const data = await res.json()
        setServices(data.services || [])
        setError(null)
      } else {
        setError("Failed to load services")
      }
    } catch {
      setError("Failed to connect to API")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchServices()
  }, [network])

  const getServiceStatus = (name: string): ServiceInfo | undefined =>
    services.find((s) => s.name === name)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Services</h1>
          <p className="text-muted-foreground mt-1">
            Manage blockchain infrastructure services per network
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Network selector */}
          <div className="relative">
            <select
              value={network}
              onChange={(e) => setNetwork(e.target.value)}
              className="appearance-none bg-card border border-border rounded-md px-3 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            >
              {NETWORKS.map((n) => (
                <option key={n} value={n}>
                  {n.charAt(0).toUpperCase() + n.slice(1)}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 pointer-events-none text-muted-foreground" />
          </div>
          <button
            onClick={fetchServices}
            className="flex items-center gap-2 bg-card border border-border rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button className="flex items-center gap-2 bg-primary text-primary-foreground rounded-md px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors">
            <Play className="h-4 w-4" />
            Deploy Service
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Service categories */}
      {SERVICE_CATEGORIES.map((category) => (
        <div key={category.name}>
          <div className="flex items-center gap-2 mb-4">
            <category.icon className="h-5 w-5 text-muted-foreground" />
            <h2 className="text-lg font-semibold">{category.name}</h2>
            <span className="text-xs text-muted-foreground bg-card px-2 py-0.5 rounded-full">
              {category.services.length} services
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {category.services.map((svcName) => {
              const svc = getServiceStatus(svcName)
              const isRunning = svc?.running ?? false
              const replicas = svc?.replicas ?? 0
              const readyReplicas = svc?.ready_replicas ?? 0

              return (
                <div
                  key={svcName}
                  className="bg-card border border-border rounded-lg p-4 hover:border-primary/50 transition-colors"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-medium">{svcName}</h3>
                      {svc?.image && (
                        <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-[200px]">
                          {svc.image}
                        </p>
                      )}
                    </div>
                    <StatusBadge running={isRunning} ready={readyReplicas} total={replicas} />
                  </div>

                  {/* Metrics */}
                  {isRunning && (
                    <div className="flex gap-4 mb-3 text-xs text-muted-foreground">
                      {svc?.cpu_usage != null && (
                        <span>CPU: {(svc.cpu_usage * 100).toFixed(0)}%</span>
                      )}
                      {svc?.memory_usage != null && (
                        <span>Mem: {(svc.memory_usage * 100).toFixed(0)}%</span>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2 mt-auto pt-2 border-t border-border">
                    {isRunning ? (
                      <>
                        <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded hover:bg-accent">
                          <RotateCw className="h-3 w-3" />
                          Restart
                        </button>
                        <button className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors px-2 py-1 rounded hover:bg-accent">
                          <Activity className="h-3 w-3" />
                          Logs
                        </button>
                        <button className="flex items-center gap-1 text-xs text-red-400 hover:text-red-300 transition-colors px-2 py-1 rounded hover:bg-red-500/10 ml-auto">
                          <Square className="h-3 w-3" />
                          Stop
                        </button>
                      </>
                    ) : (
                      <button className="flex items-center gap-1 text-xs text-green-400 hover:text-green-300 transition-colors px-2 py-1 rounded hover:bg-green-500/10">
                        <Play className="h-3 w-3" />
                        Deploy
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
