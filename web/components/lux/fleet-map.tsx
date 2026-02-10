"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { cn } from "@/lib/utils"
import { WORLD_PATHS, generateGridLines, latLngToSVG } from "./world-paths"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface FleetRegion {
  slug: string
  name: string
  lat: number
  lon: number
  active: boolean
  nodeCount: number
  networks: string[]
  healthyNodes: number
}

export interface FleetMapProps {
  regions: FleetRegion[]
  onRegionClick?: (slug: string) => void
  className?: string
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SVG_W = 960
const SVG_H = 500

const COLOR_ACTIVE = "#0066FF"
const COLOR_ACTIVE_GLOW = "#0066FF"
const COLOR_INACTIVE = "#333333"
const COLOR_BG = "#0a0a0a"

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Mercator projection: lat/lon -> SVG x/y using the shared world-paths helper */
function toSvg(lat: number, lon: number) {
  return latLngToSVG(lat, lon)
}

/** Build P2P mesh connection lines between all active regions */
function buildConnections(regions: FleetRegion[]) {
  const active = regions.filter((r) => r.active)
  const lines: { x1: number; y1: number; x2: number; y2: number; key: string }[] = []

  for (let i = 0; i < active.length; i++) {
    for (let j = i + 1; j < active.length; j++) {
      const a = toSvg(active[i].lat, active[i].lon)
      const b = toSvg(active[j].lat, active[j].lon)
      lines.push({
        x1: a.x, y1: a.y,
        x2: b.x, y2: b.y,
        key: `${active[i].slug}-${active[j].slug}`,
      })
    }
  }
  return lines
}

/** Health status derived from nodeCount vs healthyNodes */
function healthStatus(r: FleetRegion): "healthy" | "degraded" | "partial" | "inactive" {
  if (!r.active) return "inactive"
  if (r.nodeCount === 0) return "inactive"
  if (r.healthyNodes === r.nodeCount) return "healthy"
  if (r.healthyNodes === 0) return "degraded"
  return "partial"
}

function healthLabel(r: FleetRegion): string {
  const s = healthStatus(r)
  switch (s) {
    case "healthy": return "Healthy"
    case "degraded": return "Degraded"
    case "partial": return "Partial"
    case "inactive": return "Inactive"
  }
}

function healthColor(r: FleetRegion): string {
  const s = healthStatus(r)
  switch (s) {
    case "healthy": return "#22c55e"
    case "degraded": return "#ef4444"
    case "partial": return "#eab308"
    case "inactive": return COLOR_INACTIVE
  }
}

// ---------------------------------------------------------------------------
// CSS Animations (injected once)
// ---------------------------------------------------------------------------

const FLEET_STYLES = `
@keyframes fleet-pulse {
  0%   { r: 4;  opacity: 0.8; }
  70%  { r: 16; opacity: 0; }
  100% { r: 16; opacity: 0; }
}
@keyframes fleet-pulse-2 {
  0%   { r: 4;  opacity: 0.5; }
  70%  { r: 22; opacity: 0; }
  100% { r: 22; opacity: 0; }
}
@keyframes fleet-dash {
  to { stroke-dashoffset: -20; }
}
@keyframes fleet-fadein {
  from { opacity: 0; transform: scale(0.6); }
  to   { opacity: 1; transform: scale(1); }
}
@keyframes fleet-glow-breathe {
  0%   { opacity: 0.6; }
  50%  { opacity: 1; }
  100% { opacity: 0.6; }
}
.fleet-pulse-ring {
  animation: fleet-pulse 2.4s ease-out infinite;
  pointer-events: none;
}
.fleet-pulse-ring-2 {
  animation: fleet-pulse-2 2.4s ease-out infinite;
  animation-delay: 0.8s;
  pointer-events: none;
}
.fleet-mesh-line {
  stroke-dasharray: 6 4;
  animation: fleet-dash 1.5s linear infinite;
}
.fleet-node-enter {
  animation: fleet-fadein 0.35s ease-out;
  cursor: pointer;
}
.fleet-tooltip-enter {
  pointer-events: none;
  animation: fleet-fadein 0.12s ease-out;
}
.fleet-breathe {
  animation: fleet-glow-breathe 3s ease-in-out infinite;
}
`

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FleetMap({ regions, onRegionClick, className }: FleetMapProps) {
  const [hovered, setHovered] = useState<string | null>(null)
  const [zoomTarget, setZoomTarget] = useState<{ x: number; y: number; slug: string } | null>(null)
  const stylesRef = useRef(false)

  // Inject keyframe CSS once
  useEffect(() => {
    if (stylesRef.current) return
    stylesRef.current = true
    const el = document.createElement("style")
    el.setAttribute("data-fleet-map", "")
    el.textContent = FLEET_STYLES
    document.head.appendChild(el)
    return () => {
      el.remove()
    }
  }, [])

  // Click: zoom to region. Click same region or double-click: zoom out.
  const handleRegionClick = useCallback(
    (slug: string, x: number, y: number) => {
      if (zoomTarget?.slug === slug) {
        // Already zoomed here -- zoom out
        setZoomTarget(null)
      } else {
        setZoomTarget({ x, y, slug })
      }
      onRegionClick?.(slug)
    },
    [zoomTarget, onRegionClick],
  )

  const handleDoubleClick = useCallback(() => {
    setZoomTarget(null)
  }, [])

  // Derived data
  const connections = buildConnections(regions)
  const gridLines = generateGridLines(SVG_W, SVG_H)

  // Stats
  const totalNodes = regions.reduce((s, r) => s + r.nodeCount, 0)
  const activeCount = regions.filter((r) => r.active).length
  const totalHealthy = regions.reduce((s, r) => s + r.healthyNodes, 0)
  const healthPct = totalNodes > 0 ? Math.round((totalHealthy / totalNodes) * 100) : 0

  // Zoom transform
  const zoomScale = 2.2
  const zoomTransform = zoomTarget
    ? `translate(${SVG_W / 2 - zoomTarget.x * zoomScale}px, ${SVG_H / 2 - zoomTarget.y * zoomScale}px) scale(${zoomScale})`
    : "translate(0px, 0px) scale(1)"

  // Hovered region info
  const hoveredRegion = hovered ? regions.find((r) => r.slug === hovered) : null
  const hoveredPt = hoveredRegion ? toSvg(hoveredRegion.lat, hoveredRegion.lon) : null

  return (
    <div
      className={cn(
        "relative w-full overflow-hidden rounded-xl border border-white/[0.06]",
        className,
      )}
      style={{ background: COLOR_BG }}
    >
      {/* ---- Stats overlay ---- */}
      <div
        className="absolute top-4 right-4 z-10 flex flex-col gap-1.5 rounded-lg px-4 py-3"
        style={{
          background: "rgba(10,10,10,0.88)",
          border: "1px solid rgba(255,255,255,0.08)",
          backdropFilter: "blur(8px)",
        }}
      >
        <div className="text-[10px] uppercase tracking-[0.15em] text-gray-500 font-medium">
          Lux Fleet Network
        </div>
        <div className="flex gap-6">
          <StatBadge label="Nodes" value={totalNodes} />
          <StatBadge label="Regions" value={`${activeCount}/${regions.length}`} />
          <StatBadge
            label="Health"
            value={`${healthPct}%`}
            color={healthPct >= 80 ? "#22c55e" : healthPct >= 50 ? "#eab308" : "#ef4444"}
          />
        </div>
      </div>

      {/* ---- Legend ---- */}
      <div
        className="absolute bottom-4 left-4 z-10 flex gap-4 rounded-lg px-3 py-2"
        style={{
          background: "rgba(10,10,10,0.88)",
          border: "1px solid rgba(255,255,255,0.08)",
          backdropFilter: "blur(8px)",
        }}
      >
        <LegendDot color={COLOR_ACTIVE} label="Active" />
        <LegendDot color={COLOR_INACTIVE} label="Inactive" />
      </div>

      {/* ---- SVG Map ---- */}
      <svg
        viewBox={`0 0 ${SVG_W} ${SVG_H}`}
        className="w-full h-auto select-none"
        style={{ display: "block" }}
        onDoubleClick={handleDoubleClick}
      >
        <defs>
          {/* Glow filter for active dots */}
          <filter id="fm-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feColorMatrix
              in="blur"
              type="matrix"
              values="0 0 0 0 0
                      0 0.4 0 0 0
                      0 0 1 0 0
                      0 0 0 0.7 0"
              result="blueglow"
            />
            <feMerge>
              <feMergeNode in="blueglow" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Subtle glow for mesh lines */}
          <filter id="fm-line-glow" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation="1.2" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Radial gradient for active dot centers */}
          <radialGradient id="fm-dot-gradient" cx="40%" cy="40%">
            <stop offset="0%" stopColor="#4d9fff" />
            <stop offset="100%" stopColor={COLOR_ACTIVE} />
          </radialGradient>
        </defs>

        {/* Zoomable group */}
        <g
          style={{
            transform: zoomTransform,
            transformOrigin: "center center",
            transition: "transform 0.7s cubic-bezier(0.25, 0.1, 0.25, 1)",
          }}
        >
          {/* Grid lines */}
          {gridLines.map((l, i) => (
            <line
              key={`g-${i}`}
              x1={l.x1} y1={l.y1} x2={l.x2} y2={l.y2}
              stroke="rgba(255,255,255,0.025)"
              strokeWidth={0.5}
            />
          ))}

          {/* Continent outlines */}
          {WORLD_PATHS.map((c) => (
            <path
              key={c.id}
              d={c.d}
              fill="#111111"
              stroke="rgba(255,255,255,0.07)"
              strokeWidth={0.6}
              strokeLinejoin="round"
            />
          ))}

          {/* P2P mesh connection lines */}
          {connections.map((c) => (
            <line
              key={c.key}
              x1={c.x1} y1={c.y1} x2={c.x2} y2={c.y2}
              stroke={`${COLOR_ACTIVE}26`}
              strokeWidth={0.7}
              className="fleet-mesh-line"
              filter="url(#fm-line-glow)"
            />
          ))}

          {/* Region markers */}
          {regions.map((r) => {
            const pt = toSvg(r.lat, r.lon)
            const isActive = r.active
            const isHovered = hovered === r.slug
            const dotColor = isActive ? COLOR_ACTIVE : COLOR_INACTIVE
            const dotR = isActive ? (isHovered ? 6.5 : 5) : (isHovered ? 4 : 3)

            return (
              <g
                key={r.slug}
                className="fleet-node-enter"
                onClick={() => handleRegionClick(r.slug, pt.x, pt.y)}
                onMouseEnter={() => setHovered(r.slug)}
                onMouseLeave={() => setHovered(null)}
              >
                {/* Outer pulse ring 1 */}
                {isActive && (
                  <circle
                    cx={pt.x} cy={pt.y} r={4}
                    fill="none"
                    stroke={COLOR_ACTIVE_GLOW}
                    strokeWidth={1.5}
                    className="fleet-pulse-ring"
                  />
                )}

                {/* Outer pulse ring 2 (offset) */}
                {isActive && (
                  <circle
                    cx={pt.x} cy={pt.y} r={4}
                    fill="none"
                    stroke={COLOR_ACTIVE_GLOW}
                    strokeWidth={0.8}
                    className="fleet-pulse-ring-2"
                  />
                )}

                {/* Ambient glow behind active dots */}
                {isActive && (
                  <circle
                    cx={pt.x} cy={pt.y} r={10}
                    fill={`${COLOR_ACTIVE}12`}
                    className="fleet-breathe"
                  />
                )}

                {/* Core dot */}
                <circle
                  cx={pt.x} cy={pt.y}
                  r={dotR}
                  fill={isActive ? "url(#fm-dot-gradient)" : dotColor}
                  filter={isActive ? "url(#fm-glow)" : undefined}
                  style={{ transition: "r 0.2s ease" }}
                />

                {/* Inner highlight */}
                {isActive && (
                  <circle
                    cx={pt.x - 1} cy={pt.y - 1}
                    r={1.5}
                    fill="rgba(255,255,255,0.3)"
                  />
                )}

                {/* Node count badge */}
                {isActive && r.nodeCount > 0 && (
                  <>
                    <rect
                      x={pt.x + 7}
                      y={pt.y - 15}
                      width={r.nodeCount >= 100 ? 28 : r.nodeCount >= 10 ? 22 : 16}
                      height={14}
                      rx={3}
                      fill="rgba(0,0,0,0.85)"
                      stroke={`${COLOR_ACTIVE}66`}
                      strokeWidth={0.6}
                    />
                    <text
                      x={pt.x + 7 + (r.nodeCount >= 100 ? 14 : r.nodeCount >= 10 ? 11 : 8)}
                      y={pt.y - 5.5}
                      fill="#e5e7eb"
                      fontSize={8.5}
                      fontFamily="var(--font-mono, ui-monospace, monospace)"
                      fontWeight={600}
                      textAnchor="middle"
                    >
                      {r.nodeCount}
                    </text>
                  </>
                )}
              </g>
            )
          })}

          {/* Tooltip */}
          {hoveredRegion && hoveredPt && (() => {
            const tooltipW = 190
            const tooltipH = hoveredRegion.active ? 90 : 36
            // Flip tooltip left if too close to right edge
            const flipX = hoveredPt.x + tooltipW + 20 > SVG_W
            const tx = flipX ? hoveredPt.x - tooltipW - 12 : hoveredPt.x + 14
            // Flip tooltip up if too close to bottom
            const flipY = hoveredPt.y + tooltipH > SVG_H - 20
            const ty = flipY ? hoveredPt.y - tooltipH - 5 : hoveredPt.y - 50

            return (
              <g className="fleet-tooltip-enter">
                {/* Tooltip background */}
                <rect
                  x={tx}
                  y={ty}
                  width={tooltipW}
                  height={tooltipH}
                  rx={6}
                  fill="rgba(8,8,8,0.95)"
                  stroke="rgba(255,255,255,0.1)"
                  strokeWidth={0.8}
                />

                {/* Region name */}
                <text
                  x={tx + 12} y={ty + 16}
                  fill="#f3f4f6" fontSize={10} fontWeight={600}
                >
                  {hoveredRegion.name}
                </text>

                {/* Slug */}
                <text
                  x={tx + 12} y={ty + 28}
                  fill="#6b7280" fontSize={8}
                  fontFamily="var(--font-mono, ui-monospace, monospace)"
                >
                  {hoveredRegion.slug}
                </text>

                {hoveredRegion.active && (
                  <>
                    {/* Node count */}
                    <text x={tx + 12} y={ty + 44} fill="#d1d5db" fontSize={8.5}>
                      Nodes: {hoveredRegion.nodeCount}
                      {"  |  "}
                      Healthy: {hoveredRegion.healthyNodes}
                    </text>

                    {/* Networks */}
                    <text x={tx + 12} y={ty + 58} fill="#9ca3af" fontSize={8}>
                      Networks: {hoveredRegion.networks.join(", ") || "none"}
                    </text>

                    {/* Health status */}
                    <text
                      x={tx + 12} y={ty + 74}
                      fill={healthColor(hoveredRegion)}
                      fontSize={9} fontWeight={600}
                    >
                      {healthLabel(hoveredRegion).toUpperCase()}
                      {"  "}
                      {hoveredRegion.nodeCount > 0
                        ? `${Math.round((hoveredRegion.healthyNodes / hoveredRegion.nodeCount) * 100)}%`
                        : ""}
                    </text>
                  </>
                )}
              </g>
            )
          })()}
        </g>
      </svg>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatBadge({
  label,
  value,
  color,
}: {
  label: string
  value: string | number
  color?: string
}) {
  return (
    <div className="flex flex-col items-center">
      <span
        className="text-lg font-bold font-mono tabular-nums"
        style={{ color: color ?? "#e5e7eb" }}
      >
        {value}
      </span>
      <span className="text-[9px] uppercase tracking-wider text-gray-500">{label}</span>
    </div>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        className="inline-block h-2 w-2 rounded-full"
        style={{
          background: color,
          boxShadow: color !== COLOR_INACTIVE ? `0 0 6px ${color}` : "none",
        }}
      />
      <span className="text-[9px] text-gray-400">{label}</span>
    </div>
  )
}

export default FleetMap
