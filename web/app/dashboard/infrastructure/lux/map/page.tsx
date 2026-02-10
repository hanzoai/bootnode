"use client"

import { useState, useMemo } from "react"
import { cn } from "@/lib/utils"
import { FleetMap, type FleetRegion } from "@/components/lux/fleet-map"
import { DOKS_REGIONS, type LuxFleet } from "@/components/lux/region-data"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Globe, Plus, RefreshCw, Zap } from "lucide-react"

/** Convert LuxFleet[] to FleetRegion[] for the map component */
function fleetsToRegions(fleets: LuxFleet[]): FleetRegion[] {
  // Group fleets by region
  const byRegion = new Map<string, LuxFleet[]>()
  for (const f of fleets) {
    const existing = byRegion.get(f.region) ?? []
    existing.push(f)
    byRegion.set(f.region, existing)
  }

  const seenCoords = new Set<string>()
  const regions: FleetRegion[] = []

  // Active regions
  for (const [regionId, regionFleets] of byRegion) {
    const r = DOKS_REGIONS[regionId]
    if (!r) continue
    const nodeCount = regionFleets.reduce((s, f) => s + f.validators, 0)
    const healthPcts = regionFleets.filter((f) => f.healthPct != null).map((f) => f.healthPct!)
    const avgHealth = healthPcts.length > 0 ? healthPcts.reduce((s, v) => s + v, 0) / healthPcts.length : 100
    const healthyNodes = Math.round((avgHealth / 100) * nodeCount)
    const networks = regionFleets.some((f) => f.name.includes("testnet"))
      ? ["mainnet", "testnet"]
      : ["mainnet"]

    seenCoords.add(`${r.lat},${r.lng}`)
    regions.push({
      slug: regionId,
      name: r.name,
      lat: r.lat,
      lon: r.lng,
      active: true,
      nodeCount,
      networks,
      healthyNodes,
    })
  }

  // Inactive regions
  for (const [regionId, r] of Object.entries(DOKS_REGIONS)) {
    const key = `${r.lat},${r.lng}`
    if (!seenCoords.has(key)) {
      seenCoords.add(key)
      regions.push({
        slug: regionId,
        name: r.name,
        lat: r.lat,
        lon: r.lng,
        active: false,
        nodeCount: 0,
        networks: [],
        healthyNodes: 0,
      })
    }
  }

  return regions
}

// Demo fleets for development -- replaced by live API in production
const DEMO_FLEETS: LuxFleet[] = [
  { id: "f1", name: "lux-mainnet-us-east",  region: "nyc1", status: "running",   validators: 12, blockHeight: 8_421_003, healthPct: 99.8 },
  { id: "f2", name: "lux-mainnet-us-west",  region: "sfo3", status: "running",   validators: 8,  blockHeight: 8_420_998, healthPct: 99.5 },
  { id: "f3", name: "lux-mainnet-eu",       region: "fra1", status: "running",   validators: 10, blockHeight: 8_421_001, healthPct: 100 },
  { id: "f4", name: "lux-mainnet-london",   region: "lon1", status: "running",   validators: 6,  blockHeight: 8_421_000, healthPct: 98.2 },
  { id: "f5", name: "lux-mainnet-apac",     region: "sgp1", status: "deploying", validators: 4,  blockHeight: 8_418_200, healthPct: 72 },
  { id: "f6", name: "lux-testnet-toronto",  region: "tor1", status: "running",   validators: 3,  blockHeight: 2_100_450, healthPct: 100 },
  { id: "f7", name: "lux-mainnet-sydney",   region: "syd1", status: "degraded",  validators: 2,  blockHeight: 8_419_500, healthPct: 45 },
]

export default function LuxFleetMapPage() {
  const [useLive, setUseLive] = useState(false)
  const [demoFleets, setDemoFleets] = useState(DEMO_FLEETS)
  const [selectedRegion, setSelectedRegion] = useState<string | null>(null)

  // Available regions not yet running a fleet
  const availableRegions = useMemo(() => {
    const activeRegions = new Set(demoFleets.map((f) => f.region))
    return Object.entries(DOKS_REGIONS)
      .filter(([id]) => !activeRegions.has(id))
      .map(([id, r]) => ({ id, ...r }))
  }, [demoFleets])

  function addRandomFleet() {
    if (availableRegions.length === 0) return
    const target = availableRegions[Math.floor(Math.random() * availableRegions.length)]
    const newFleet: LuxFleet = {
      id: `f${Date.now()}`,
      name: `lux-fleet-${target.id}`,
      region: target.id,
      status: "deploying",
      validators: Math.floor(Math.random() * 8) + 2,
      blockHeight: 8_000_000 + Math.floor(Math.random() * 500_000),
      healthPct: 60 + Math.random() * 30,
    }
    setDemoFleets((prev) => [...prev, newFleet])
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Globe className="h-6 w-6" />
            Lux Fleet Map
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time geolocated validator nodes across DOKS regions
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setUseLive((v) => !v)}
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            {useLive ? "Demo Mode" : "Live Mode"}
          </Button>
          {!useLive && (
            <Button
              variant="outline"
              size="sm"
              onClick={addRandomFleet}
              disabled={availableRegions.length === 0}
            >
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Add Fleet
            </Button>
          )}
        </div>
      </div>

      {/* Map */}
      <FleetMap
        regions={fleetsToRegions(useLive ? [] : demoFleets)}
        onRegionClick={setSelectedRegion}
      />

      {/* Active Fleets Table */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Active Fleets
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(useLive ? [] : demoFleets).map((fleet) => (
                <div
                  key={fleet.id}
                  className={cn(
                    "flex items-center justify-between rounded-lg border p-3 text-sm transition-colors",
                    selectedRegion === fleet.region && "border-green-500/30 bg-green-500/5"
                  )}
                >
                  <div className="flex flex-col gap-0.5">
                    <span className="font-mono text-xs font-medium">{fleet.name}</span>
                    <span className="text-[11px] text-muted-foreground">
                      {DOKS_REGIONS[fleet.region]?.name ?? fleet.region}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs tabular-nums">{fleet.validators}v</span>
                    <Badge
                      variant={
                        fleet.status === "running" ? "success" :
                        fleet.status === "deploying" ? "warning" :
                        fleet.status === "degraded" ? "destructive" :
                        "secondary"
                      }
                      className="text-[10px] px-1.5"
                    >
                      {fleet.status}
                    </Badge>
                  </div>
                </div>
              ))}
              {useLive && (
                <p className="text-xs text-muted-foreground text-center py-4">
                  Polling /v1/lux/fleets every 10s...
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Available Regions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2">
              {availableRegions.map((r) => (
                <div
                  key={r.id}
                  className={cn(
                    "flex items-center justify-between rounded-lg border px-3 py-2 text-xs transition-colors cursor-pointer hover:border-gray-400",
                    selectedRegion === r.id && "border-blue-500/30 bg-blue-500/5"
                  )}
                  onClick={() => setSelectedRegion(r.id)}
                >
                  <span className="font-mono">{r.id}</span>
                  <span className="text-muted-foreground">{r.country}</span>
                </div>
              ))}
              {availableRegions.length === 0 && (
                <p className="col-span-2 text-xs text-muted-foreground text-center py-4">
                  All regions have active fleets
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
