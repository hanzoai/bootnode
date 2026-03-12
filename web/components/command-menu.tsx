"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Command } from "cmdk"
import {
  ArrowRight,
  Bot,
  Database,
  FileText,
  Globe,
  KeyRound,
  Layers,
  Search,
  Wallet,
  Webhook,
  Zap,
  Server,
  Activity,
  Eye,
  Boxes,
  BarChart3,
  RotateCw,
  Play,
  Square,
  MessageSquare,
  Sparkles,
  ArrowUpRight,
  Terminal,
} from "lucide-react"
import { useBrand } from "@/components/brand-logo"
import { AiChat } from "@/components/ai-chat"

// Navigation pages
const pages = [
  { name: "Dashboard", href: "/dashboard", icon: Zap, group: "Navigation" },
  { name: "Documentation", href: "/docs", icon: FileText, group: "Navigation" },
  { name: "Pricing", href: "/pricing", icon: ArrowRight, group: "Navigation" },
  { name: "Node (RPC)", href: "/products/node", icon: Globe, group: "Products" },
  { name: "Token API", href: "/products/data", icon: Database, group: "Products" },
  { name: "NFT API", href: "/products/data", icon: Database, group: "Products" },
  { name: "Smart Wallets", href: "/products/wallets", icon: Wallet, group: "Products" },
  { name: "Explorer", href: "/products/explorer", icon: Search, group: "Products" },
  { name: "MPC", href: "/products/mpc", icon: KeyRound, group: "Products" },
  { name: "Webhooks", href: "/products/webhooks", icon: Webhook, group: "Products" },
  { name: "Rollups", href: "/products/rollups", icon: Layers, group: "Products" },
  { name: "Ethereum", href: "/chains/ethereum", icon: Globe, group: "Chains" },
  { name: "Solana", href: "/chains/solana", icon: Globe, group: "Chains" },
  { name: "Base", href: "/chains/base", icon: Globe, group: "Chains" },
  { name: "Arbitrum", href: "/chains/arbitrum", icon: Globe, group: "Chains" },
  { name: "Polygon", href: "/chains/polygon", icon: Globe, group: "Chains" },
  { name: "All Chains", href: "/chains", icon: Globe, group: "Chains" },
  { name: "Quickstart", href: "/docs/quickstart", icon: FileText, group: "Docs" },
  { name: "API Reference", href: "/docs/api", icon: FileText, group: "Docs" },
  { name: "SDKs", href: "/docs/sdks", icon: FileText, group: "Docs" },
]

// Infrastructure quick actions
const infraActions = [
  { name: "Services", href: "/dashboard/infrastructure/services", icon: Boxes, group: "Infrastructure" },
  { name: "Observability", href: "/dashboard/infrastructure/observability", icon: Eye, group: "Infrastructure" },
  { name: "Nodes", href: "/dashboard/infrastructure/nodes", icon: Server, group: "Infrastructure" },
  { name: "Monitoring", href: "/dashboard/infrastructure/monitoring", icon: Activity, group: "Infrastructure" },
  { name: "Fleet Status", href: "/dashboard/infrastructure/nodes", icon: BarChart3, group: "Infrastructure" },
]

// AI-powered actions (trigger chat with pre-filled prompts)
const aiActions = [
  { name: "Check fleet health", prompt: "Check the health of all fleets and services", icon: Activity, group: "AI Actions" },
  { name: "Show active alerts", prompt: "Are there any active alerts or incidents?", icon: Eye, group: "AI Actions" },
  { name: "Search logs", prompt: "Search recent logs for errors across all services", icon: Terminal, group: "AI Actions" },
  { name: "Scale validators", prompt: "How do I scale my validator fleet?", icon: ArrowUpRight, group: "AI Actions" },
  { name: "Deploy service", prompt: "Help me deploy a new infrastructure service", icon: Play, group: "AI Actions" },
  { name: "RPC status", prompt: "What's the current RPC endpoint status and latency?", icon: Zap, group: "AI Actions" },
]

export function CommandMenu() {
  const [open, setOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [chatPrompt, setChatPrompt] = useState<string | undefined>()
  const [mode, setMode] = useState<"search" | "ai">("search")
  const router = useRouter()
  const brand = useBrand()
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      // cmd+K = command palette
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        if (
          e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement
        ) {
          return
        }
        e.preventDefault()
        setOpen((o) => !o)
        setMode("search")
      }
      // cmd+J = AI chat directly
      if (e.key === "j" && (e.metaKey || e.ctrlKey)) {
        if (
          e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement
        ) {
          return
        }
        e.preventDefault()
        setChatPrompt(undefined)
        setChatOpen((o) => !o)
      }
      // "/" = search (not in input)
      if (e.key === "/" && !(
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )) {
        e.preventDefault()
        setOpen(true)
        setMode("search")
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const runCommand = useCallback((href: string) => {
    setOpen(false)
    router.push(href)
  }, [router])

  const runAiAction = useCallback((prompt: string) => {
    setOpen(false)
    setChatPrompt(prompt)
    setChatOpen(true)
  }, [])

  const switchToAi = useCallback(() => {
    setOpen(false)
    setChatPrompt(undefined)
    setChatOpen(true)
  }, [])

  const groups = pages.reduce(
    (acc, page) => {
      if (!acc[page.group]) acc[page.group] = []
      acc[page.group].push(page)
      return acc
    },
    {} as Record<string, typeof pages>
  )

  // Ecosystem links from brand
  const ecosystemLinks = brand.footerLinks.map((link) => ({
    name: link.name,
    href: link.href,
    icon: Globe,
    external: link.external,
  }))

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => { setOpen(true); setMode("search") }}
        className="relative hidden items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm text-muted-foreground hover:bg-accent md:flex md:w-[200px] lg:w-[300px]"
      >
        <Search className="h-4 w-4" />
        <span>Search or ask AI...</span>
        <kbd className="pointer-events-none absolute right-3 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      {/* Command palette dialog */}
      {open && (
        <div className="fixed inset-0 z-50">
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
          />
          <div className="fixed left-1/2 top-[15%] z-50 w-full max-w-xl -translate-x-1/2">
            <Command
              className="overflow-hidden rounded-xl border bg-background shadow-2xl"
              loop
            >
              <div className="flex items-center border-b px-3">
                <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                <Command.Input
                  ref={inputRef}
                  placeholder={`Search ${brand.name} or type a question...`}
                  className="flex h-12 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                  autoFocus
                />
                <button
                  onClick={switchToAi}
                  className="ml-2 flex items-center gap-1.5 shrink-0 rounded-md bg-primary/10 px-2.5 py-1.5 text-xs font-medium text-primary hover:bg-primary/20 transition-colors"
                  title="Open AI Chat (⌘J)"
                >
                  <Sparkles className="h-3 w-3" />
                  AI
                </button>
              </div>

              <Command.List className="max-h-[400px] overflow-y-auto p-2">
                <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                  No results found. Press the AI button to ask a question.
                </Command.Empty>

                {/* AI Actions */}
                <Command.Group
                  heading="AI Actions"
                  className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground"
                >
                  {aiActions.map((action) => (
                    <Command.Item
                      key={action.name}
                      value={`ai ${action.name}`}
                      onSelect={() => runAiAction(action.prompt)}
                      className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                    >
                      <action.icon className="h-4 w-4 text-primary" />
                      <span>{action.name}</span>
                      <Sparkles className="h-3 w-3 ml-auto text-primary/50" />
                    </Command.Item>
                  ))}
                </Command.Group>

                {/* Infrastructure */}
                <Command.Group
                  heading="Infrastructure"
                  className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground"
                >
                  {infraActions.map((item) => (
                    <Command.Item
                      key={item.href + item.name}
                      value={item.name}
                      onSelect={() => runCommand(item.href)}
                      className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                    >
                      <item.icon className="h-4 w-4 text-muted-foreground" />
                      {item.name}
                    </Command.Item>
                  ))}
                </Command.Group>

                {/* Navigation groups */}
                {Object.entries(groups).map(([group, items]) => (
                  <Command.Group
                    key={group}
                    heading={group}
                    className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground"
                  >
                    {items.map((item) => (
                      <Command.Item
                        key={item.href + item.name}
                        value={item.name}
                        onSelect={() => runCommand(item.href)}
                        className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                      >
                        <item.icon className="h-4 w-4 text-muted-foreground" />
                        {item.name}
                      </Command.Item>
                    ))}
                  </Command.Group>
                ))}

                {/* Ecosystem */}
                {ecosystemLinks.length > 0 && (
                  <Command.Group
                    heading="Ecosystem"
                    className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground"
                  >
                    {ecosystemLinks.map((item) => (
                      <Command.Item
                        key={item.href}
                        value={item.name}
                        onSelect={() => {
                          setOpen(false)
                          if (item.external) {
                            window.open(item.href, "_blank")
                          } else {
                            router.push(item.href)
                          }
                        }}
                        className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 text-sm aria-selected:bg-accent aria-selected:text-accent-foreground"
                      >
                        <item.icon className="h-4 w-4 text-muted-foreground" />
                        {item.name}
                      </Command.Item>
                    ))}
                  </Command.Group>
                )}
              </Command.List>

              {/* Footer */}
              <div className="flex items-center justify-between border-t border-border px-3 py-2 text-[10px] text-muted-foreground">
                <div className="flex items-center gap-3">
                  <span>
                    <kbd className="rounded border bg-muted px-1 font-mono">↑↓</kbd> Navigate
                  </span>
                  <span>
                    <kbd className="rounded border bg-muted px-1 font-mono">↵</kbd> Select
                  </span>
                  <span>
                    <kbd className="rounded border bg-muted px-1 font-mono">esc</kbd> Close
                  </span>
                </div>
                <span className="flex items-center gap-1">
                  <kbd className="rounded border bg-muted px-1 font-mono">⌘J</kbd> AI Chat
                </span>
              </div>
            </Command>
          </div>
        </div>
      )}

      {/* AI Chat Panel */}
      <AiChat
        isOpen={chatOpen}
        onClose={() => setChatOpen(false)}
        initialPrompt={chatPrompt}
      />
    </>
  )
}
