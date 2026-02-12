"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Copy, Loader2, X, HardDrive, Camera, CheckCircle, Clock, AlertCircle } from "lucide-react"

interface Volume {
  id: string
  name: string
  size_gb: number
  region: string
  status: string
  snapshots: { id: string; name: string; size_gb: number; created_at: string }[]
}

interface Snapshot {
  id: string
  name: string
  volume_id: string
  size_gb: number
  status: string
  created_at: string
  region: string
}

interface CloneJob {
  id: string
  name: string
  source_id: string
  source_type: string
  size_gb: number
  status: string
  progress: number
  estimated_completion: string | null
  created_at: string
}

export default function StoragePage() {
  const [volumes, setVolumes] = useState<Volume[]>([])
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [clones, setClones] = useState<CloneJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showClone, setShowClone] = useState(false)
  const [cloning, setCloning] = useState(false)

  // Clone form state
  const [cloneName, setCloneName] = useState("")
  const [sourceId, setSourceId] = useState("")
  const [targetRegion, setTargetRegion] = useState("")

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem("bootnode_token")
    const apiKey = localStorage.getItem("bootnode_api_key")
    if (token) return { "Authorization": `Bearer ${token}` }
    if (apiKey) return { "X-API-Key": apiKey }
    return {}
  }

  async function fetchData() {
    try {
      const headers = getAuthHeaders()
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const [volRes, snapRes, cloneRes] = await Promise.all([
        fetch(`${apiUrl}/v1/infra/volumes`, { headers }),
        fetch(`${apiUrl}/v1/infra/snapshots`, { headers }),
        fetch(`${apiUrl}/v1/infra/clone`, { headers }),
      ])

      if (volRes.ok) setVolumes(await volRes.json())
      if (snapRes.ok) setSnapshots(await snapRes.json())
      if (cloneRes.ok) setClones(await cloneRes.json())
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  async function handleClone() {
    if (!cloneName.trim() || !sourceId) return
    setCloning(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const res = await fetch(`${apiUrl}/v1/infra/clone`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders()
        },
        body: JSON.stringify({
          name: cloneName.trim(),
          source_id: sourceId,
          region: targetRegion || undefined,
        })
      })
      if (res.ok) {
        const newClone = await res.json()
        setClones(prev => [...prev, newClone])
        setShowClone(false)
        setCloneName("")
        setSourceId("")
        setTargetRegion("")
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setCloning(false)
    }
  }

  function getStatusIcon(status: string) {
    switch (status) {
      case "completed": return <CheckCircle className="h-4 w-4 text-green-500" />
      case "cloning": return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
      case "error": return <AlertCircle className="h-4 w-4 text-red-500" />
      default: return <Clock className="h-4 w-4 text-muted-foreground" />
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Storage Cloning</h1>
          <p className="text-muted-foreground">
            Rapidly clone volumes and snapshots for fast node deployment
          </p>
        </div>
        <Button onClick={() => setShowClone(!showClone)}>
          <Copy className="mr-2 h-4 w-4" />
          Clone Storage
        </Button>
      </div>

      {showClone && (
        <Card>
          <CardHeader>
            <CardTitle>Clone Volume or Snapshot</CardTitle>
            <CardDescription>
              Create a copy-on-write clone for instant provisioning
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div>
                <label className="text-sm font-medium">Clone Name</label>
                <Input
                  placeholder="e.g., ETH Mainnet Clone"
                  value={cloneName}
                  onChange={(e) => setCloneName(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Source (Volume or Snapshot)</label>
                <select
                  className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={sourceId}
                  onChange={(e) => setSourceId(e.target.value)}
                >
                  <option value="">Select source...</option>
                  <optgroup label="Volumes">
                    {volumes.map(v => (
                      <option key={v.id} value={v.id}>{v.name} ({v.size_gb} GB)</option>
                    ))}
                  </optgroup>
                  <optgroup label="Snapshots">
                    {snapshots.map(s => (
                      <option key={s.id} value={s.id}>{s.name} ({s.size_gb} GB)</option>
                    ))}
                  </optgroup>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Target Region (optional)</label>
                <Input
                  placeholder="Same as source"
                  value={targetRegion}
                  onChange={(e) => setTargetRegion(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={handleClone} disabled={cloning || !cloneName.trim() || !sourceId}>
                {cloning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Start Clone
              </Button>
              <Button variant="outline" onClick={() => setShowClone(false)}>
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Clone Jobs */}
      <Card>
        <CardHeader>
          <CardTitle>Clone Operations</CardTitle>
          <CardDescription>Active and recent clone jobs</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : clones.length === 0 ? (
            <div className="text-center text-muted-foreground p-12">
              No clone operations. Click "Clone Storage" to create one.
            </div>
          ) : (
            <div className="space-y-4">
              {clones.map((clone) => (
                <div key={clone.id} className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Copy className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{clone.name}</h4>
                        {getStatusIcon(clone.status)}
                        <Badge variant={clone.status === "completed" ? "default" : "secondary"}>
                          {clone.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="outline" className="text-xs">
                          {clone.source_type === "snapshot" ? <Camera className="h-3 w-3 mr-1" /> : <HardDrive className="h-3 w-3 mr-1" />}
                          {clone.source_id}
                        </Badge>
                        <Badge variant="outline" className="text-xs">{clone.size_gb} GB</Badge>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    {clone.status === "cloning" && (
                      <>
                        <div className="w-32 bg-secondary rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full transition-all"
                            style={{ width: `${clone.progress}%` }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">{clone.progress}%</p>
                      </>
                    )}
                    {clone.status === "completed" && (
                      <p className="text-sm text-muted-foreground">
                        {new Date(clone.created_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Available Sources */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Volumes
            </CardTitle>
            <CardDescription>Available for cloning</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : volumes.length === 0 ? (
              <p className="text-muted-foreground">No volumes available</p>
            ) : (
              <div className="space-y-2">
                {volumes.map((volume) => (
                  <div
                    key={volume.id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                    onClick={() => {
                      setSourceId(volume.id)
                      setCloneName(`${volume.name} Clone`)
                      setShowClone(true)
                    }}
                  >
                    <div>
                      <p className="font-medium">{volume.name}</p>
                      <p className="text-xs text-muted-foreground">{volume.region}</p>
                    </div>
                    <Badge variant="outline">{volume.size_gb} GB</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Snapshots
            </CardTitle>
            <CardDescription>Point-in-time copies for fast cloning</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : snapshots.length === 0 ? (
              <p className="text-muted-foreground">No snapshots available</p>
            ) : (
              <div className="space-y-2">
                {snapshots.map((snapshot) => (
                  <div
                    key={snapshot.id}
                    className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                    onClick={() => {
                      setSourceId(snapshot.id)
                      setCloneName(`${snapshot.name} Clone`)
                      setShowClone(true)
                    }}
                  >
                    <div>
                      <p className="font-medium">{snapshot.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(snapshot.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Badge variant="outline">{snapshot.size_gb} GB</Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
