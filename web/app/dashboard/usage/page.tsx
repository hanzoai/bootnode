"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Activity,
  Globe,
  Database,
  Server,
} from "lucide-react"
import { useChains } from "@/lib/hooks"
import { getBrand } from "@/lib/brand"

const brand = getBrand()

export default function UsagePage() {
  const chainsQuery = useChains()
  const chainsList = Array.isArray(chainsQuery.data) ? chainsQuery.data : []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Usage</h1>
        <p className="text-muted-foreground">
          Monitor your API usage, compute units, and billing
        </p>
      </div>

      {/* Status Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Server className="h-4 w-4" />
              API Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="default">Connected</Badge>
            <p className="text-xs text-muted-foreground mt-1">
              {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Globe className="h-4 w-4" />
              Active Chains
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {chainsQuery.isLoading ? "..." : chainsList.length}
            </div>
            <p className="text-xs text-muted-foreground">chains configured</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Database className="h-4 w-4" />
              Analytics Backend
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Badge variant="outline">Datastore</Badge>
            <p className="text-xs text-muted-foreground mt-1">
              Detailed metrics available via API
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Chains List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="h-5 w-5" />
            Supported Chains
          </CardTitle>
          <CardDescription>
            Chains available through the {brand.name} API
          </CardDescription>
        </CardHeader>
        <CardContent>
          {chainsQuery.isLoading ? (
            <div className="flex items-center justify-center p-12">
              <div className="text-muted-foreground">Loading chains...</div>
            </div>
          ) : chainsQuery.error ? (
            <div className="rounded-md bg-destructive/10 p-4 text-destructive">
              {String(chainsQuery.error)}
            </div>
          ) : chainsList.length === 0 ? (
            <div className="text-center text-muted-foreground p-12">
              No chains configured yet.
            </div>
          ) : (
            <div className="space-y-3">
              {chainsList.map((chain: { chain_id?: string; name?: string; id?: string; networks?: string[]; rpc_url?: string; type?: string }, i: number) => (
                <div
                  key={chain.chain_id || chain.id || chain.name || i}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
                      <Globe className="h-4 w-4 text-primary" />
                    </div>
                    <div>
                      <h4 className="font-medium text-sm">{chain.name || chain.chain_id || chain.id}</h4>
                      {chain.chain_id && chain.name && (
                        <p className="text-xs text-muted-foreground">{chain.chain_id}</p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {chain.type && (
                      <Badge variant="outline" className="text-xs">{chain.type}</Badge>
                    )}
                    {chain.networks && chain.networks.map((net: string) => (
                      <Badge key={net} variant="secondary" className="text-xs">{net}</Badge>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Analytics Notice */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Detailed Usage Analytics
          </CardTitle>
          <CardDescription>
            Request volume, latency, and compute unit tracking
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border bg-muted/50 p-8 text-center space-y-3">
            <Activity className="h-12 w-12 text-muted-foreground mx-auto" />
            <h3 className="font-medium">Analytics Available via API</h3>
            <p className="text-sm text-muted-foreground max-w-lg mx-auto">
              Detailed usage analytics including request volume, latency percentiles,
              compute unit consumption, and per-chain breakdowns are available through
              the {brand.name} API. Connect Hanzo Datastore for historical data and dashboards.
            </p>
            <div className="flex justify-center gap-2 pt-2">
              <Badge variant="outline">Request Volume</Badge>
              <Badge variant="outline">Latency (p50/p99)</Badge>
              <Badge variant="outline">Compute Units</Badge>
              <Badge variant="outline">Per-Chain Stats</Badge>
              <Badge variant="outline">Error Rates</Badge>
            </div>
            <p className="text-xs text-muted-foreground pt-2">
              API endpoint: <code className="font-mono">GET /v1/usage/stats</code>
            </p>
          </div>
        </CardContent>
      </Card>

      {/* API Endpoints for Usage */}
      <Card>
        <CardHeader>
          <CardTitle>Usage API Endpoints</CardTitle>
          <CardDescription>
            Programmatically access your usage data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[
              { method: "GET", path: "/v1/chains", description: "List all supported chains" },
              { method: "GET", path: "/v1/gas/{chain}/prices", description: "Current gas prices per chain" },
              { method: "GET", path: "/v1/webhooks", description: "List webhooks and delivery stats" },
              { method: "GET", path: "/v1/wallets", description: "List deployed smart wallets" },
              { method: "GET", path: "/v1/auth/keys?project_id={id}", description: "List API keys for project" },
            ].map((endpoint) => (
              <div key={endpoint.path} className="flex items-center gap-3 p-3 border rounded-lg">
                <Badge variant={endpoint.method === "GET" ? "default" : "secondary"} className="font-mono text-xs w-12 justify-center">
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
