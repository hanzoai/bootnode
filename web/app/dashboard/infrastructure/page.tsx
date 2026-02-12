"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Server, Box, HardDrive, Copy, Loader2, Shield } from "lucide-react"
import Link from "next/link"

interface InfraStats {
  clusters: { total: number; running: number; total_nodes: number }
  volumes: { total: number; in_use: number; total_storage_gb: number; used_storage_gb: number }
  snapshots: { total: number }
  regions: string[]
}

export default function InfrastructurePage() {
  const [stats, setStats] = useState<InfraStats | null>(null)
  const [loading, setLoading] = useState(true)

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem("bootnode_token")
    const apiKey = localStorage.getItem("bootnode_api_key")
    if (token) return { "Authorization": `Bearer ${token}` }
    if (apiKey) return { "X-API-Key": apiKey }
    return {}
  }

  useEffect(() => {
    async function fetchStats() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        const res = await fetch(`${apiUrl}/v1/infra/stats`, {
          headers: getAuthHeaders()
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
    fetchStats()
  }, [])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Infrastructure</h1>
        <p className="text-muted-foreground">
          Manage K8s clusters, nodes, volumes, and storage
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">K8s Clusters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : stats?.clusters.total || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats?.clusters.running || 0} running
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Nodes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : stats?.clusters.total_nodes || 0}
            </div>
            <p className="text-xs text-muted-foreground">across clusters</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Volumes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : stats?.volumes.total || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats?.volumes.in_use || 0} in use
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Storage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : `${((stats?.volumes.total_storage_gb || 0) / 1000).toFixed(1)} TB`}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats?.snapshots.total || 0} snapshots
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Infrastructure Categories */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Lux Validators
            </CardTitle>
            <CardDescription>
              Deploy and manage Lux validator fleets
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Run fleets of luxd validators across Kubernetes clusters.
              Mainnet, testnet, and devnet support with chain tracking.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/infrastructure/lux">
                Manage Fleets
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Blockchain Nodes
            </CardTitle>
            <CardDescription>
              Deploy and manage dedicated blockchain nodes
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Full nodes for Ethereum, Bitcoin, Solana, and more chains.
              Direct RPC access with dedicated resources.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/infrastructure/nodes">
                Manage Nodes
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Box className="h-5 w-5" />
              Kubernetes Clusters
            </CardTitle>
            <CardDescription>
              Manage K8s clusters for node deployment
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Create and scale Kubernetes clusters across regions.
              Automatic node pool management and upgrades.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/infrastructure/clusters">
                Manage Clusters
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Persistent Volumes
            </CardTitle>
            <CardDescription>
              Block storage for blockchain data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              High-performance NVMe storage for chain data.
              Automatic snapshots and cross-region replication.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/infrastructure/volumes">
                Manage Volumes
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Copy className="h-5 w-5" />
              Storage Cloning
            </CardTitle>
            <CardDescription>
              Rapidly clone volumes for fast deployment
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Copy-on-write cloning for instant node deployment.
              Clone from volumes or snapshots across regions.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/infrastructure/storage">
                Clone Storage
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* API Endpoints */}
      <Card>
        <CardHeader>
          <CardTitle>Infrastructure APIs</CardTitle>
          <CardDescription>Available endpoints for infrastructure management</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { method: "GET", path: "/v1/infra/clusters", description: "List K8s clusters" },
              { method: "POST", path: "/v1/infra/clusters", description: "Create cluster" },
              { method: "GET", path: "/v1/infra/clusters/{id}/kubeconfig", description: "Get kubeconfig" },
              { method: "GET", path: "/v1/infra/volumes", description: "List volumes" },
              { method: "POST", path: "/v1/infra/volumes", description: "Create volume" },
              { method: "POST", path: "/v1/infra/snapshots", description: "Create snapshot" },
              { method: "POST", path: "/v1/infra/clone", description: "Clone volume/snapshot" },
              { method: "GET", path: "/v1/infra/stats", description: "Infrastructure stats" },
            ].map((endpoint) => (
              <div key={endpoint.path + endpoint.method} className="flex items-center gap-3 p-3 border rounded-lg">
                <Badge variant="default" className="font-mono text-xs w-14 justify-center">
                  {endpoint.method}
                </Badge>
                <code className="text-sm font-mono flex-1">{endpoint.path}</code>
                <span className="text-sm text-muted-foreground">{endpoint.description}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
