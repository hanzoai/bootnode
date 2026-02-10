"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Activity, Cpu, HardDrive, MemoryStick, Wifi, WifiOff, Loader2 } from "lucide-react"

interface NodeHealth {
  id: string
  name: string
  chain: string
  status: "healthy" | "degraded" | "down"
  cpu_percent: number
  memory_percent: number
  disk_percent: number
  block_height: number
  peers: number
  uptime_seconds: number
  last_check: string
}

interface MonitoringStats {
  total_nodes: number
  healthy: number
  degraded: number
  down: number
  nodes: NodeHealth[]
}

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400)
  const h = Math.floor((seconds % 86400) / 3600)
  if (d > 0) return `${d}d ${h}h`
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

function StatusBadge({ status }: { status: string }) {
  const variant = status === "healthy" ? "default" : status === "degraded" ? "secondary" : "destructive"
  return <Badge variant={variant}>{status}</Badge>
}

function UsageBar({ percent, label }: { percent: number; label: string }) {
  const color = percent > 90 ? "bg-destructive" : percent > 70 ? "bg-yellow-500" : "bg-green-500"
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span>{percent.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-muted">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(percent, 100)}%` }} />
      </div>
    </div>
  )
}

export default function MonitoringPage() {
  const [stats, setStats] = useState<MonitoringStats | null>(null)
  const [loading, setLoading] = useState(true)

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem("bootnode_token")
    const apiKey = localStorage.getItem("bootnode_api_key")
    if (token) return { Authorization: `Bearer ${token}` }
    if (apiKey) return { "X-API-Key": apiKey }
    return {}
  }

  useEffect(() => {
    async function fetchMonitoring() {
      try {
        const res = await fetch("http://localhost:8000/v1/monitoring/nodes", {
          headers: getAuthHeaders(),
        })
        if (res.ok) {
          setStats(await res.json())
        }
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetchMonitoring()
    const interval = setInterval(fetchMonitoring, 15000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Monitoring</h1>
        <p className="text-muted-foreground">Real-time health and performance of your infrastructure</p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Nodes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : stats?.total_nodes ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Wifi className="h-4 w-4 text-green-500" /> Healthy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : stats?.healthy ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4 text-yellow-500" /> Degraded
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-500">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : stats?.degraded ?? 0}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <WifiOff className="h-4 w-4 text-destructive" /> Down
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : stats?.down ?? 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Node Health Table */}
      <Card>
        <CardHeader>
          <CardTitle>Node Health</CardTitle>
          <CardDescription>Auto-refreshes every 15 seconds</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : !stats?.nodes?.length ? (
            <div className="text-center py-12 text-muted-foreground">
              <Activity className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No nodes to monitor yet.</p>
              <p className="text-sm mt-1">Deploy nodes from the Infrastructure page to see monitoring data.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {stats.nodes.map((node) => (
                <div key={node.id} className="border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="font-medium">{node.name}</span>
                      <Badge variant="outline">{node.chain}</Badge>
                      <StatusBadge status={node.status} />
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>Block #{node.block_height.toLocaleString()}</span>
                      <span>{node.peers} peers</span>
                      <span>Up {formatUptime(node.uptime_seconds)}</span>
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <UsageBar percent={node.cpu_percent} label="CPU" />
                    <UsageBar percent={node.memory_percent} label="Memory" />
                    <UsageBar percent={node.disk_percent} label="Disk" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
