"use client"

import { useState, useEffect } from "react"
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BarChart3,
  Clock,
  Zap,
  RefreshCw,
  Bell,
  Eye,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react"

interface HealthOverview {
  total_services: number
  healthy: number
  unhealthy: number
  degraded: number
  uptime_percent: number
  services: { name: string; healthy: boolean; replicas: number; ready_replicas: number; latency_ms: number | null }[]
  checked_at: string
}

interface MetricsData {
  requests_per_sec: number
  latency_p50_ms: number
  latency_p95_ms: number
  latency_p99_ms: number
  error_rate: number
  active_connections: number
  total_requests_24h: number
}

interface PlatformEvent {
  id: string
  type: string
  service: string | null
  message: string
  metadata: Record<string, any>
  timestamp: string
}

interface Alert {
  id: string
  severity: "critical" | "warning" | "info"
  service: string
  message: string
  fired_at: string
  resolved_at: string | null
}

function StatCard({
  label,
  value,
  unit,
  trend,
  icon: Icon,
}: {
  label: string
  value: string | number
  unit?: string
  trend?: "up" | "down" | "flat"
  icon: any
}) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-bold">{value}</span>
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
        {trend && (
          <span className={`ml-auto flex items-center text-xs ${
            trend === "up" ? "text-green-400" : trend === "down" ? "text-red-400" : "text-muted-foreground"
          }`}>
            {trend === "up" && <ArrowUpRight className="h-3 w-3" />}
            {trend === "down" && <ArrowDownRight className="h-3 w-3" />}
            {trend === "flat" && <Minus className="h-3 w-3" />}
          </span>
        )}
      </div>
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: "bg-red-500/10 text-red-400 border-red-500/20",
    warning: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    info: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${styles[severity] || styles.info}`}>
      {severity}
    </span>
  )
}

export default function ObservabilityPage() {
  const [health, setHealth] = useState<HealthOverview | null>(null)
  const [metrics, setMetrics] = useState<MetricsData | null>(null)
  const [events, setEvents] = useState<PlatformEvent[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [healthRes, metricsRes, eventsRes, alertsRes] = await Promise.allSettled([
        fetch("/api/v1/o11y/health").then((r) => r.ok ? r.json() : null),
        fetch("/api/v1/o11y/metrics").then((r) => r.ok ? r.json() : null),
        fetch("/api/v1/o11y/events?limit=20").then((r) => r.ok ? r.json() : []),
        fetch("/api/v1/o11y/alerts").then((r) => r.ok ? r.json() : []),
      ])

      if (healthRes.status === "fulfilled" && healthRes.value) setHealth(healthRes.value)
      if (metricsRes.status === "fulfilled" && metricsRes.value) setMetrics(metricsRes.value)
      if (eventsRes.status === "fulfilled") setEvents(eventsRes.value || [])
      if (alertsRes.status === "fulfilled") setAlerts(alertsRes.value || [])
    } catch {
      // silently handle
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Observability</h1>
          <p className="text-muted-foreground mt-1">
            Platform health, metrics, alerts, and events
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="https://grafana.internal/d/bootnode"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 bg-card border border-border rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <BarChart3 className="h-4 w-4" />
            Grafana
          </a>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 bg-card border border-border rounded-md px-3 py-2 text-sm hover:bg-accent transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Health overview cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          label="Total Services"
          value={health?.total_services ?? "-"}
          icon={Eye}
        />
        <StatCard
          label="Healthy"
          value={health?.healthy ?? "-"}
          icon={CheckCircle2}
          trend={health ? (health.healthy === health.total_services ? "up" : "down") : undefined}
        />
        <StatCard
          label="Active Alerts"
          value={alerts.length}
          icon={Bell}
          trend={alerts.length > 0 ? "down" : "flat"}
        />
        <StatCard
          label="Uptime"
          value={health?.uptime_percent ?? "-"}
          unit="%"
          icon={Activity}
        />
      </div>

      {/* Metrics row */}
      {metrics && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Metrics</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
            <StatCard label="Req/s" value={metrics.requests_per_sec.toFixed(1)} icon={Zap} />
            <StatCard label="p50" value={metrics.latency_p50_ms.toFixed(0)} unit="ms" icon={Clock} />
            <StatCard label="p95" value={metrics.latency_p95_ms.toFixed(0)} unit="ms" icon={Clock} />
            <StatCard label="p99" value={metrics.latency_p99_ms.toFixed(0)} unit="ms" icon={Clock} />
            <StatCard label="Error Rate" value={(metrics.error_rate * 100).toFixed(2)} unit="%" icon={AlertTriangle} />
            <StatCard label="Connections" value={metrics.active_connections} icon={Activity} />
            <StatCard label="24h Requests" value={metrics.total_requests_24h.toLocaleString()} icon={BarChart3} />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Active alerts */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Active Alerts</h2>
          <div className="bg-card border border-border rounded-lg divide-y divide-border">
            {alerts.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-400" />
                <p>No active alerts</p>
              </div>
            ) : (
              alerts.map((alert) => (
                <div key={alert.id} className="p-4 flex items-start gap-3">
                  <SeverityBadge severity={alert.severity} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium">{alert.message}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {alert.service} &middot; {new Date(alert.fired_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent events */}
        <div>
          <h2 className="text-lg font-semibold mb-4">Recent Events</h2>
          <div className="bg-card border border-border rounded-lg divide-y divide-border">
            {events.length === 0 ? (
              <div className="p-8 text-center text-muted-foreground">
                <Activity className="h-8 w-8 mx-auto mb-2" />
                <p>No recent events</p>
              </div>
            ) : (
              events.map((event) => (
                <div key={event.id} className="p-4 flex items-start gap-3">
                  <span className="text-xs bg-card border border-border px-2 py-0.5 rounded-full">
                    {event.type}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{event.message}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {event.service && `${event.service} · `}
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Service health table */}
      {health && (
        <div>
          <h2 className="text-lg font-semibold mb-4">Service Health</h2>
          <div className="bg-card border border-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-muted/50">
                  <th className="text-left p-3 font-medium">Service</th>
                  <th className="text-left p-3 font-medium">Status</th>
                  <th className="text-left p-3 font-medium">Replicas</th>
                  <th className="text-left p-3 font-medium">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {health.services.map((svc) => (
                  <tr key={svc.name} className="hover:bg-muted/30 transition-colors">
                    <td className="p-3 font-mono text-xs">{svc.name}</td>
                    <td className="p-3">
                      {svc.healthy ? (
                        <span className="flex items-center gap-1.5 text-green-400 text-xs">
                          <CheckCircle2 className="h-3 w-3" /> Healthy
                        </span>
                      ) : svc.replicas > 0 ? (
                        <span className="flex items-center gap-1.5 text-red-400 text-xs">
                          <XCircle className="h-3 w-3" /> Unhealthy
                        </span>
                      ) : (
                        <span className="flex items-center gap-1.5 text-muted-foreground text-xs">
                          <Minus className="h-3 w-3" /> Not deployed
                        </span>
                      )}
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {svc.ready_replicas}/{svc.replicas}
                    </td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {svc.latency_ms != null ? `${svc.latency_ms.toFixed(0)}ms` : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
