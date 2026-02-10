"use client"

import React, { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Select } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Plus,
  Loader2,
  RefreshCcw,
  Trash2,
  RotateCcw,
  Scale,
  Shield,
  Globe,
  Heart,
  ChevronDown,
  ChevronRight,
  Circle,
  AlertTriangle,
} from "lucide-react"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type FleetStatus = "running" | "degraded" | "error" | "deploying" | "stopped"
type NetworkType = "mainnet" | "testnet" | "devnet"

interface FleetNode {
  pod_name: string
  status: string
  ready: boolean
  external_ip: string | null
  c_chain_height: number | null
  peers: number | null
  node_id: string | null
  healthy: boolean | null
}

interface LuxFleetSummary {
  cluster_id: string
  network: NetworkType
  name: string
  status: FleetStatus
  replicas: number
  ready_replicas: number
  helm_revision: number
  image_tag: string
  created_at: string
}

interface LuxFleetResponse extends LuxFleetSummary {
  nodes: FleetNode[]
}

interface LuxFleetStats {
  total_fleets: number
  total_nodes: number
  healthy_nodes: number
}

interface Cluster {
  id: string
  name: string
  region: string
}

interface NetworkConfig {
  network: NetworkType
  chain_id: string
  default_image: string
}

// ---------------------------------------------------------------------------
// Constants & helpers
// ---------------------------------------------------------------------------

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {}
  const token = localStorage.getItem("bootnode_token")
  const apiKey = localStorage.getItem("bootnode_api_key")
  if (token) return { Authorization: `Bearer ${token}` }
  if (apiKey) return { "X-API-Key": apiKey }
  return {}
}

const STATUS_COLORS: Record<FleetStatus, string> = {
  running: "bg-green-500/15 text-green-500 border-green-500/30",
  degraded: "bg-yellow-500/15 text-yellow-500 border-yellow-500/30",
  error: "bg-red-500/15 text-red-500 border-red-500/30",
  deploying: "bg-blue-500/15 text-blue-500 border-blue-500/30",
  stopped: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
}

const NETWORK_COLORS: Record<NetworkType, string> = {
  mainnet: "border-green-500/50 text-green-400",
  testnet: "border-blue-500/50 text-blue-400",
  devnet: "border-orange-500/50 text-orange-400",
}

function statusBadge(status: FleetStatus) {
  return (
    <Badge variant="outline" className={`${STATUS_COLORS[status]} capitalize`}>
      {status === "running" && <Circle className="mr-1 h-2 w-2 fill-green-500" />}
      {status === "degraded" && <AlertTriangle className="mr-1 h-3 w-3" />}
      {status === "error" && <Circle className="mr-1 h-2 w-2 fill-red-500" />}
      {status === "deploying" && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
      {status}
    </Badge>
  )
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function LuxFleetsPage() {
  // Data
  const [clusters, setClusters] = useState<Cluster[]>([])
  const [selectedCluster, setSelectedCluster] = useState<string>("")
  const [fleets, setFleets] = useState<LuxFleetSummary[]>([])
  const [fleetDetails, setFleetDetails] = useState<Record<string, LuxFleetResponse>>({})
  const [stats, setStats] = useState<LuxFleetStats | null>(null)
  const [networks, setNetworks] = useState<NetworkConfig[]>([])

  // UI
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expandedFleet, setExpandedFleet] = useState<string | null>(null)

  // Create dialog
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [formName, setFormName] = useState("")
  const [formNetwork, setFormNetwork] = useState<NetworkType>("testnet")
  const [formReplicas, setFormReplicas] = useState(5)
  const [formImageTag, setFormImageTag] = useState("luxd-v1.23.11")
  const [formChainTracking, setFormChainTracking] = useState(true)

  // Confirm dialogs
  const [confirmRestart, setConfirmRestart] = useState<string | null>(null)
  const [confirmDestroy, setConfirmDestroy] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Scale dropdown
  const [scaleTarget, setScaleTarget] = useState<string | null>(null)
  const [scaleValue, setScaleValue] = useState(5)

  // ------- API helpers ------------------------------------------------------

  async function apiFetch(path: string, opts?: RequestInit) {
    const res = await fetch(`${API_URL}${path}`, {
      ...opts,
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...(opts?.headers || {}),
      },
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }
    if (res.status === 204) return null
    return res.json()
  }

  // ------- Fetch data -------------------------------------------------------

  const fetchClusters = useCallback(async () => {
    try {
      const data = await apiFetch("/v1/infra/clusters")
      const list: Cluster[] = Array.isArray(data) ? data : []
      setClusters(list)
      if (list.length > 0 && !selectedCluster) {
        setSelectedCluster(list[0].id)
      }
    } catch {
      // best-effort
    }
  }, [selectedCluster])

  const fetchFleets = useCallback(
    async (silent = false) => {
      if (!selectedCluster) return
      if (!silent) setLoading(true)
      try {
        const data = await apiFetch(`/v1/lux/fleets?cluster_id=${selectedCluster}`)
        setFleets(Array.isArray(data) ? data : [])
        setError(null)
      } catch (e) {
        setError(String(e))
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [selectedCluster],
  )

  const fetchStats = useCallback(async () => {
    try {
      const data = await apiFetch("/v1/lux/stats")
      setStats(data)
    } catch {
      // best-effort
    }
  }, [])

  const fetchNetworks = useCallback(async () => {
    try {
      const data = await apiFetch("/v1/lux/networks")
      if (Array.isArray(data)) setNetworks(data)
    } catch {
      // best-effort
    }
  }, [])

  const fetchFleetDetail = useCallback(
    async (network: NetworkType) => {
      if (!selectedCluster) return
      try {
        const data: LuxFleetResponse = await apiFetch(
          `/v1/lux/fleets/${selectedCluster}/${network}`,
        )
        setFleetDetails((prev) => ({ ...prev, [`${selectedCluster}/${network}`]: data }))
      } catch {
        // best-effort
      }
    },
    [selectedCluster],
  )

  // ------- Initial load & polling -------------------------------------------

  useEffect(() => {
    fetchClusters()
    fetchStats()
    fetchNetworks()
  }, [fetchClusters, fetchStats, fetchNetworks])

  useEffect(() => {
    if (selectedCluster) {
      fetchFleets()
    }
  }, [selectedCluster, fetchFleets])

  useEffect(() => {
    if (!selectedCluster) return
    const interval = setInterval(() => {
      fetchFleets(true)
      fetchStats()
    }, 15000)
    return () => clearInterval(interval)
  }, [selectedCluster, fetchFleets, fetchStats])

  // Fetch node details when a fleet is expanded
  useEffect(() => {
    if (expandedFleet && selectedCluster) {
      const network = expandedFleet as NetworkType
      fetchFleetDetail(network)
    }
  }, [expandedFleet, selectedCluster, fetchFleetDetail])

  // ------- Fleet operations -------------------------------------------------

  async function handleCreate() {
    if (!formName.trim() || !selectedCluster) return
    setCreating(true)
    setCreateError(null)
    try {
      await apiFetch("/v1/lux/fleets", {
        method: "POST",
        body: JSON.stringify({
          name: formName.trim(),
          cluster_id: selectedCluster,
          network: formNetwork,
          replicas: formReplicas,
          image_tag: formImageTag.trim(),
          chain_tracking: formChainTracking,
        }),
      })
      setCreateOpen(false)
      resetForm()
      fetchFleets()
      fetchStats()
    } catch (e) {
      setCreateError(String(e))
    } finally {
      setCreating(false)
    }
  }

  function resetForm() {
    setFormName("")
    setFormNetwork("testnet")
    setFormReplicas(5)
    setFormImageTag("luxd-v1.23.11")
    setFormChainTracking(true)
    setCreateError(null)
  }

  async function handleScale(network: NetworkType, replicas: number) {
    setActionLoading(network)
    try {
      await apiFetch(
        `/v1/lux/fleets/${selectedCluster}/${network}/scale?replicas=${replicas}`,
        { method: "POST" },
      )
      setScaleTarget(null)
      fetchFleets()
    } catch (e) {
      console.error("Scale failed:", e)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleRestart(network: NetworkType) {
    setActionLoading(network)
    try {
      await apiFetch(`/v1/lux/fleets/${selectedCluster}/${network}/restart`, {
        method: "POST",
      })
      setConfirmRestart(null)
      fetchFleets()
    } catch (e) {
      console.error("Restart failed:", e)
    } finally {
      setActionLoading(null)
    }
  }

  async function handleDestroy(network: NetworkType) {
    setActionLoading(network)
    try {
      await apiFetch(`/v1/lux/fleets/${selectedCluster}/${network}`, {
        method: "DELETE",
      })
      setConfirmDestroy(null)
      setFleets((prev) => prev.filter((f) => f.network !== network))
      fetchStats()
    } catch (e) {
      console.error("Destroy failed:", e)
    } finally {
      setActionLoading(null)
    }
  }

  // ------- Render -----------------------------------------------------------

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Lux Fleet Dashboard</h1>
          <p className="text-muted-foreground">
            Deploy and manage luxd validator fleets across Kubernetes clusters
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Cluster selector */}
          <Select
            value={selectedCluster}
            onValueChange={setSelectedCluster}
            className="w-[220px]"
          >
            {clusters.length === 0 ? (
              <option value="" disabled>
                No clusters
              </option>
            ) : (
              clusters.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.region})
                </option>
              ))
            )}
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setRefreshing(true)
              fetchFleets()
              fetchStats()
            }}
            disabled={refreshing}
          >
            <RefreshCcw className={`mr-2 h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>

          {/* Create fleet */}
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Fleet
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[500px]">
              <DialogHeader>
                <DialogTitle>Create Lux Validator Fleet</DialogTitle>
                <DialogDescription>
                  Deploy a fleet of luxd validators to the selected cluster
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div>
                  <label className="text-sm font-medium">Fleet Name</label>
                  <Input
                    placeholder="e.g., lux-mainnet-validators"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    className="mt-1"
                  />
                </div>
                <div className="grid gap-4 grid-cols-2">
                  <div>
                    <label className="text-sm font-medium">Network</label>
                    <Select
                      value={formNetwork}
                      onValueChange={(v) => setFormNetwork(v as NetworkType)}
                      className="mt-1"
                    >
                      <option value="mainnet">Mainnet</option>
                      <option value="testnet">Testnet</option>
                      <option value="devnet">Devnet</option>
                    </Select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Replicas</label>
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={formReplicas}
                      onChange={(e) => setFormReplicas(parseInt(e.target.value) || 5)}
                      className="mt-1"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Image Tag</label>
                  <Input
                    placeholder="luxd-v1.23.11"
                    value={formImageTag}
                    onChange={(e) => setFormImageTag(e.target.value)}
                    className="mt-1 font-mono"
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="text-sm font-medium">Chain Tracking</p>
                    <p className="text-xs text-muted-foreground">
                      Auto-configure C/P/X chain tracking for {formNetwork}
                    </p>
                  </div>
                  <Switch checked={formChainTracking} onCheckedChange={setFormChainTracking} />
                </div>
                {createError && (
                  <div className="rounded-md bg-destructive/10 p-3 text-destructive text-sm">
                    {createError}
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setCreateOpen(false)
                    resetForm()
                  }}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreate}
                  disabled={creating || !formName.trim() || !selectedCluster}
                >
                  {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Create Fleet
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Stats banner */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Fleets</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-muted-foreground" />
              <span className="text-2xl font-bold">
                {stats ? stats.total_fleets : <Loader2 className="h-5 w-5 animate-spin" />}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">across all clusters</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Nodes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-muted-foreground" />
              <span className="text-2xl font-bold">
                {stats ? stats.total_nodes : <Loader2 className="h-5 w-5 animate-spin" />}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">validator pods running</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Healthy Nodes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <Heart className="h-5 w-5 text-green-500" />
              <span className="text-2xl font-bold text-green-500">
                {stats ? stats.healthy_nodes : <Loader2 className="h-5 w-5 animate-spin" />}
              </span>
              {stats && stats.total_nodes > 0 && (
                <span className="text-sm text-muted-foreground">
                  / {stats.total_nodes} ({Math.round((stats.healthy_nodes / stats.total_nodes) * 100)}%)
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground">passing health checks</p>
          </CardContent>
        </Card>
      </div>

      {/* Fleet cards per network */}
      {loading ? (
        <div className="flex items-center justify-center p-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="p-6">
            <div className="rounded-md bg-destructive/10 p-4 text-destructive">{error}</div>
          </CardContent>
        </Card>
      ) : fleets.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center text-muted-foreground">
            No fleets deployed on this cluster. Click &quot;Create Fleet&quot; to get started.
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {fleets.map((fleet) => {
            const key = `${fleet.cluster_id}/${fleet.network}`
            const detail = fleetDetails[key]
            const isExpanded = expandedFleet === fleet.network
            const isActionLoading = actionLoading === fleet.network

            return (
              <Card key={key} className="border-zinc-800">
                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() =>
                          setExpandedFleet(isExpanded ? null : fleet.network)
                        }
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </Button>
                      <div>
                        <CardTitle className="flex items-center gap-2">
                          {fleet.name}
                          <Badge variant="outline" className={NETWORK_COLORS[fleet.network]}>
                            {fleet.network}
                          </Badge>
                        </CardTitle>
                        <CardDescription className="font-mono text-xs mt-1">
                          {fleet.image_tag}
                        </CardDescription>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {statusBadge(fleet.status)}
                      <div className="text-sm text-right">
                        <span className="font-bold">{fleet.ready_replicas}</span>
                        <span className="text-muted-foreground">/{fleet.replicas} ready</span>
                        <p className="text-xs text-muted-foreground">
                          Helm rev {fleet.helm_revision}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardHeader>

                {/* Fleet operations */}
                <CardContent className="pt-0 pb-4">
                  <div className="flex items-center gap-2 border-t border-zinc-800 pt-4">
                    {/* Scale */}
                    {scaleTarget === fleet.network ? (
                      <div className="flex items-center gap-2">
                        <Select
                          value={String(scaleValue)}
                          onValueChange={(v) => setScaleValue(parseInt(v))}
                          className="w-[80px]"
                        >
                          {Array.from({ length: 20 }, (_, i) => i + 1).map((n) => (
                            <option key={n} value={String(n)}>
                              {n}
                            </option>
                          ))}
                        </Select>
                        <Button
                          size="sm"
                          onClick={() => handleScale(fleet.network, scaleValue)}
                          disabled={isActionLoading}
                        >
                          {isActionLoading ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <Scale className="mr-1 h-3 w-3" />
                          )}
                          Apply
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setScaleTarget(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setScaleValue(fleet.replicas)
                          setScaleTarget(fleet.network)
                        }}
                      >
                        <Scale className="mr-2 h-3 w-3" />
                        Scale
                      </Button>
                    )}

                    {/* Restart */}
                    {confirmRestart === fleet.network ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-yellow-500">Restart all pods?</span>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleRestart(fleet.network)}
                          disabled={isActionLoading}
                        >
                          {isActionLoading ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <RotateCcw className="mr-1 h-3 w-3" />
                          )}
                          Confirm
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirmRestart(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setConfirmRestart(fleet.network)}
                      >
                        <RotateCcw className="mr-2 h-3 w-3" />
                        Restart
                      </Button>
                    )}

                    {/* Destroy */}
                    {confirmDestroy === fleet.network ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-red-500">
                          Permanently destroy this fleet?
                        </span>
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDestroy(fleet.network)}
                          disabled={isActionLoading}
                        >
                          {isActionLoading ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <Trash2 className="mr-1 h-3 w-3" />
                          )}
                          Destroy
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirmDestroy(null)}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-400 hover:text-red-300 border-red-500/30 hover:border-red-500/50"
                        onClick={() => setConfirmDestroy(fleet.network)}
                      >
                        <Trash2 className="mr-2 h-3 w-3" />
                        Destroy
                      </Button>
                    )}
                  </div>
                </CardContent>

                {/* Expanded: Node list table */}
                {isExpanded && (
                  <CardContent className="pt-0">
                    <div className="border-t border-zinc-800 pt-4">
                      <p className="text-sm font-medium text-muted-foreground mb-3">
                        Nodes ({detail?.nodes?.length ?? "..."})
                      </p>
                      {!detail ? (
                        <div className="flex items-center justify-center p-8">
                          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                        </div>
                      ) : detail.nodes.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center p-6">
                          No nodes reported. Fleet may still be deploying.
                        </p>
                      ) : (
                        <Table>
                          <TableHeader>
                            <TableRow>
                              <TableHead>Pod Name</TableHead>
                              <TableHead>Status</TableHead>
                              <TableHead>External IP</TableHead>
                              <TableHead className="text-right">C-Chain Height</TableHead>
                              <TableHead className="text-right">Peers</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {detail.nodes.map((node) => (
                              <TableRow key={node.pod_name}>
                                <TableCell>
                                  <div className="flex items-center gap-2">
                                    <Circle
                                      className={`h-2 w-2 fill-current ${
                                        node.healthy === true && node.ready
                                          ? "text-green-500"
                                          : node.healthy === false
                                            ? "text-red-500"
                                            : node.status === "Pending" ||
                                                node.status === "ContainerCreating"
                                              ? "text-yellow-500"
                                              : "text-zinc-500"
                                      }`}
                                    />
                                    <span className="font-mono text-xs">{node.pod_name}</span>
                                  </div>
                                </TableCell>
                                <TableCell>
                                  <span
                                    className={`text-sm ${
                                      node.ready ? "text-green-400" : "text-yellow-400"
                                    }`}
                                  >
                                    {node.status}
                                  </span>
                                </TableCell>
                                <TableCell>
                                  <span className="font-mono text-xs text-muted-foreground">
                                    {node.external_ip || "--"}
                                  </span>
                                </TableCell>
                                <TableCell className="text-right font-mono text-sm">
                                  {node.c_chain_height != null
                                    ? node.c_chain_height.toLocaleString()
                                    : "--"}
                                </TableCell>
                                <TableCell className="text-right font-mono text-sm">
                                  {node.peers != null ? node.peers : "--"}
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      )}
                    </div>
                  </CardContent>
                )}
              </Card>
            )
          })}
        </div>
      )}

      {/* Restart confirmation dialog */}
      <Dialog
        open={confirmRestart !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmRestart(null)
        }}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Confirm Restart</DialogTitle>
            <DialogDescription>
              This will perform a rolling restart of all pods in the{" "}
              <span className="font-mono font-bold">{confirmRestart}</span> fleet. Nodes will be
              temporarily unavailable during restart.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRestart(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirmRestart && handleRestart(confirmRestart as NetworkType)}
              disabled={actionLoading !== null}
            >
              {actionLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Restart Fleet
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Destroy confirmation dialog */}
      <Dialog
        open={confirmDestroy !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmDestroy(null)
        }}
      >
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Confirm Destroy</DialogTitle>
            <DialogDescription>
              This will permanently delete the{" "}
              <span className="font-mono font-bold">{confirmDestroy}</span> fleet and all its
              nodes. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDestroy(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => confirmDestroy && handleDestroy(confirmDestroy as NetworkType)}
              disabled={actionLoading !== null}
            >
              {actionLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Destroy Fleet
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* API reference */}
      <Card className="border-zinc-800">
        <CardHeader>
          <CardTitle>Fleet APIs</CardTitle>
          <CardDescription>Lux fleet management endpoints</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[
              { method: "GET", path: "/v1/lux/fleets?cluster_id=xxx", desc: "List fleets" },
              { method: "GET", path: "/v1/lux/fleets/{cluster_id}/{network}", desc: "Fleet detail with nodes" },
              { method: "POST", path: "/v1/lux/fleets", desc: "Create fleet" },
              { method: "PATCH", path: "/v1/lux/fleets/{cluster_id}/{network}", desc: "Update fleet config" },
              { method: "DELETE", path: "/v1/lux/fleets/{cluster_id}/{network}", desc: "Destroy fleet" },
              { method: "POST", path: "/v1/lux/fleets/{cluster_id}/{network}/scale?replicas=N", desc: "Scale replicas" },
              { method: "POST", path: "/v1/lux/fleets/{cluster_id}/{network}/restart", desc: "Rolling restart" },
              { method: "GET", path: "/v1/lux/stats", desc: "Fleet statistics" },
              { method: "GET", path: "/v1/lux/networks", desc: "Network configs" },
            ].map((ep) => (
              <div
                key={ep.method + ep.path}
                className="flex items-center gap-3 p-2.5 border border-zinc-800 rounded-lg"
              >
                <Badge
                  variant="default"
                  className={`font-mono text-xs w-16 justify-center ${
                    ep.method === "POST"
                      ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                      : ep.method === "DELETE"
                        ? "bg-red-500/20 text-red-400 border-red-500/30"
                        : ep.method === "PATCH"
                          ? "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
                          : ""
                  }`}
                >
                  {ep.method}
                </Badge>
                <code className="text-xs font-mono flex-1 text-muted-foreground">{ep.path}</code>
                <span className="text-xs text-muted-foreground">{ep.desc}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
