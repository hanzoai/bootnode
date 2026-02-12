"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { HardDrive, Plus, Loader2, X, Camera, Link2, Unlink, ArrowUpRight } from "lucide-react"

interface Volume {
  id: string
  name: string
  size_gb: number
  region: string
  status: string
  filesystem_type: string
  attached_to: string | null
  mount_path: string | null
  created_at: string
  snapshots: { id: string; name: string; size_gb: number; created_at: string }[]
  tags: string[]
}

export default function VolumesPage() {
  const [volumes, setVolumes] = useState<Volume[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [creating, setCreating] = useState(false)

  // Form state
  const [name, setName] = useState("")
  const [sizeGb, setSizeGb] = useState(100)
  const [region, setRegion] = useState("nyc1")

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem("bootnode_token")
    const apiKey = localStorage.getItem("bootnode_api_key")
    if (token) return { "Authorization": `Bearer ${token}` }
    if (apiKey) return { "X-API-Key": apiKey }
    return {}
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

  async function fetchVolumes() {
    try {
      const res = await fetch(`${apiUrl}/v1/infra/volumes`, {
        headers: getAuthHeaders()
      })
      if (res.ok) {
        const data = await res.json()
        setVolumes(Array.isArray(data) ? data : [])
      } else {
        setError(`Failed to fetch volumes: ${res.status}`)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchVolumes()
  }, [])

  async function handleCreate() {
    if (!name.trim()) return
    setCreating(true)
    try {
      const res = await fetch(`${apiUrl}/v1/infra/volumes`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name: name.trim(),
          size_gb: sizeGb,
          region,
        })
      })
      if (res.ok) {
        const newVolume = await res.json()
        setVolumes(prev => [...prev, newVolume])
        setShowCreate(false)
        setName("")
        setSizeGb(100)
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setCreating(false)
    }
  }

  async function createSnapshot(volumeId: string, volumeName: string) {
    try {
      const res = await fetch(`${apiUrl}/v1/infra/snapshots`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name: `${volumeName} - ${new Date().toISOString().split('T')[0]}`,
          volume_id: volumeId,
        })
      })
      if (res.ok) {
        alert("Snapshot creation started")
        fetchVolumes()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const totalStorage = volumes.reduce((sum, v) => sum + v.size_gb, 0)
  const usedStorage = volumes.filter(v => v.status === "in_use").reduce((sum, v) => sum + v.size_gb, 0)

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Persistent Volumes</h1>
          <p className="text-muted-foreground">
            Manage block storage for blockchain data
          </p>
        </div>
        <Button onClick={() => setShowCreate(!showCreate)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Volume
        </Button>
      </div>

      {showCreate && (
        <Card>
          <CardHeader>
            <CardTitle>Create New Volume</CardTitle>
            <CardDescription>Create a persistent block storage volume</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium">Volume Name</label>
                <Input
                  placeholder="e.g., Ethereum Mainnet Data"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Size (GB)</label>
                <Input
                  type="number"
                  value={sizeGb}
                  onChange={(e) => setSizeGb(parseInt(e.target.value) || 100)}
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
            </div>
            <div className="flex gap-2">
              <Button onClick={handleCreate} disabled={creating || !name.trim()}>
                {creating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Volume
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
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Volumes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{loading ? "..." : volumes.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">In Use</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : volumes.filter(v => v.status === "in_use").length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Storage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : `${(totalStorage / 1000).toFixed(1)} TB`}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Snapshots</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {loading ? "..." : volumes.reduce((sum, v) => sum + v.snapshots.length, 0)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Volumes List */}
      <Card>
        <CardHeader>
          <CardTitle>Your Volumes</CardTitle>
          <CardDescription>Block storage volumes for blockchain data</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : error ? (
            <div className="rounded-md bg-destructive/10 p-4 text-destructive">{error}</div>
          ) : volumes.length === 0 ? (
            <div className="text-center text-muted-foreground p-12">
              No volumes yet. Click "Create Volume" to get started.
            </div>
          ) : (
            <div className="space-y-4">
              {volumes.map((volume) => (
                <div key={volume.id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <HardDrive className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium">{volume.name}</h4>
                          <Badge variant={volume.status === "in_use" ? "default" : "secondary"}>
                            {volume.status.replace("_", " ")}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <Badge variant="outline" className="text-xs">{volume.size_gb} GB</Badge>
                          <Badge variant="outline" className="text-xs">{volume.region}</Badge>
                          <Badge variant="outline" className="text-xs">{volume.filesystem_type}</Badge>
                          {volume.attached_to && (
                            <Badge variant="outline" className="text-xs">
                              <Link2 className="h-3 w-3 mr-1" />
                              {volume.attached_to}
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon" onClick={() => createSnapshot(volume.id, volume.name)} title="Create snapshot">
                        <Camera className="h-4 w-4" />
                      </Button>
                      {volume.attached_to ? (
                        <Button variant="ghost" size="icon" title="Detach volume">
                          <Unlink className="h-4 w-4" />
                        </Button>
                      ) : (
                        <Button variant="ghost" size="icon" title="Attach volume">
                          <Link2 className="h-4 w-4" />
                        </Button>
                      )}
                      <Button variant="ghost" size="icon" title="Resize volume">
                        <ArrowUpRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  {volume.snapshots.length > 0 && (
                    <div className="mt-4 pl-14">
                      <p className="text-sm text-muted-foreground mb-2">Snapshots ({volume.snapshots.length})</p>
                      <div className="flex flex-wrap gap-2">
                        {volume.snapshots.slice(0, 3).map((snap) => (
                          <Badge key={snap.id} variant="secondary" className="text-xs">
                            <Camera className="h-3 w-3 mr-1" />
                            {snap.name}
                          </Badge>
                        ))}
                        {volume.snapshots.length > 3 && (
                          <Badge variant="secondary" className="text-xs">
                            +{volume.snapshots.length - 3} more
                          </Badge>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
