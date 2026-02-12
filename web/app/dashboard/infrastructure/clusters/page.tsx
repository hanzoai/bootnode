"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Box, Plus, Loader2, X, Settings, Download, Scale } from "lucide-react"

interface Cluster {
  id: string
  name: string
  provider: string
  region: string
  status: string
  kubernetes_version: string
  node_count: number
  node_size: string
  endpoint: string | null
  created_at: string
  node_pools: { name: string; count: number; size: string }[]
  tags: string[]
}

export default function ClustersPage() {
  const [clusters, setClusters] = useState<Cluster[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)

  // Form state
  const [name, setName] = useState("")
  const [provider, setProvider] = useState("digitalocean")
  const [region, setRegion] = useState("nyc1")
  const [nodeCount, setNodeCount] = useState(3)
  const [nodeSize, setNodeSize] = useState("s-2vcpu-4gb")

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem("bootnode_token")
    const apiKey = localStorage.getItem("bootnode_api_key")
    if (token) return { "Authorization": `Bearer ${token}` }
    if (apiKey) return { "X-API-Key": apiKey }
    return {}
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  async function fetchClusters() {
    try {
      const res = await fetch(`${apiUrl}/v1/infra/clusters`, {
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const data = await res.json()
        setClusters(Array.isArray(data) ? data : [])
      } else {
        setError(`Failed to fetch clusters: ${res.status}`)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchClusters()
  }, [])

  async function handleCreate() {
    if (!name.trim()) return
    setCreating(true)
    try {
      const res = await fetch(`${apiUrl}/v1/infra/clusters`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name: name.trim(),
          provider,
          region,
          node_count: nodeCount,
          node_size: nodeSize,
        })
      })
      if (res.ok) {
        const newCluster = await res.json()
        setClusters(prev => [...prev, newCluster])
        setShowCreate(false)
        setName("")
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setCreating(false)
    }
  }

  async function downloadKubeconfig(clusterId: string) {
    try {
      const res = await fetch(`${apiUrl}/v1/infra/clusters/${clusterId}/kubeconfig`, {
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const data = await res.json()
        const blob = new Blob([data.kubeconfig], { type: "text/yaml" })
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `${clusterId}-kubeconfig.yaml`
        a.click()
      }
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Kubernetes Clusters</h1>
          <p className="text-muted-foreground">
            Manage K8s clusters for blockchain node deployment
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Cluster
        </Button>
      </div>

      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Cluster</CardTitle>
            <CardDescription>Deploy a new Kubernetes cluster</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <label className="text-sm font-medium">Cluster Name</label>
                <Input
                  placeholder="e.g., Production Cluster"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Provider</label>
                <Input
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  placeholder="digitalocean, aws, gcp"
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Region</label>
                <Input
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  placeholder="nyc1, sfo3, etc."
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Node Count</label>
                <Input
                  type="number"
                  value={nodeCount}
                  onChange={(e) => setNodeCount(parseInt(e.target.value) || 3)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Node Size</label>
                <Input
                  value={nodeSize}
                  onChange={(e) => setNodeSize(e.target.value)}
                  placeholder="s-2vcpu-4gb"
                  className="mt-1"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCreate} disabled={creating || !name.trim()}>
                {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Cluster
              </Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Clusters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? "..." : clusters.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Running</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : clusters.filter(c => c.status === "running").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Nodes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : clusters.reduce((sum, c) => sum + c.node_count, 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Clusters List */}
      <Card>
        <CardHeader>
          <CardTitle>Your Clusters</CardTitle>
          <CardDescription>Kubernetes clusters for blockchain infrastructure</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="rounded-md bg-destructive/10 p-4 text-destructive">{error}</div>
          ) : clusters.length === 0 ? (
            <div className="text-center text-muted-foreground p-12">
              No clusters yet. Click "Create Cluster" to get started.
            </div>
          ) : (
            <div className="space-y-4">
              {clusters.map((cluster) => (
                <div key={cluster.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Box className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{cluster.name}</h4>
                        <Badge variant={cluster.status === "running" ? "default" : "secondary"}>
                          {cluster.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">{cluster.provider}</Badge>
                        <Badge variant="outline" className="text-xs">{cluster.region}</Badge>
                        <Badge variant="outline" className="text-xs">k8s {cluster.kubernetes_version}</Badge>
                        <Badge variant="outline" className="text-xs">{cluster.node_count} nodes</Badge>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="icon" onClick={() => downloadKubeconfig(cluster.id)} title="Download kubeconfig">
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" title="Scale cluster">
                      <Scale className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" title="Settings">
                      <Settings className="h-4 w-4" />
                    </Button>
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
