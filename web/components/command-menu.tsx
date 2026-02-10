"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import { Command } from "cmdk"
import {
  ArrowRight,
  Database,
  FileText,
  Globe,
  Layers,
  Search,
  Wallet,
  Webhook,
  Zap,
} from "lucide-react"
import { useBrand } from "@/components/brand-logo"

const pages = [
  { name: "Dashboard", href: "/dashboard", icon: Zap, group: "Navigation" },
  { name: "Documentation", href: "/docs", icon: FileText, group: "Navigation" },
  { name: "Pricing", href: "/pricing", icon: ArrowRight, group: "Navigation" },
  { name: "Node (RPC)", href: "/products/node", icon: Globe, group: "Products" },
  { name: "Token API", href: "/products/data", icon: Database, group: "Products" },
  { name: "NFT API", href: "/products/data", icon: Database, group: "Products" },
  { name: "Smart Wallets", href: "/products/wallets", icon: Wallet, group: "Products" },
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

export function CommandMenu() {
  const [open, setOpen] = React.useState(false)
  const router = useRouter()
  const brand = useBrand()

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || e.key === "/") {
        // Don't trigger if typing in an input
        if (
          e.target instanceof HTMLInputElement ||
          e.target instanceof HTMLTextAreaElement
        ) {
          return
        }
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const runCommand = (href: string) => {
    setOpen(false)
    router.push(href)
  }

  const groups = pages.reduce(
    (acc, page) => {
      if (!acc[page.group]) acc[page.group] = []
      acc[page.group].push(page)
      return acc
    },
    {} as Record<string, typeof pages>
  )

  // Add brand ecosystem links
  const ecosystemLinks = brand.footerLinks.map((link) => ({
    name: link.name,
    href: link.href,
    icon: Globe,
    external: link.external,
  }))

  return (
    <>
      {/* Trigger button for mobile / click */}
      <button
        onClick={() => setOpen(true)}
        className="relative hidden items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm text-muted-foreground hover:bg-accent md:flex md:w-[200px] lg:w-[300px]"
      >
        <Search className="h-4 w-4" />
        <span>Search...</span>
        <kbd className="pointer-events-none absolute right-3 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>

      {/* Command dialog */}
      {open && (
        <div className="fixed inset-0 z-50">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => setOpen(false)}
          />
          <div className="fixed left-1/2 top-[20%] z-50 w-full max-w-lg -translate-x-1/2">
            <Command
              className="overflow-hidden rounded-xl border bg-background shadow-2xl"
              loop
            >
              <div className="flex items-center border-b px-3">
                <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
                <Command.Input
                  placeholder={`Search ${brand.name}...`}
                  className="flex h-12 w-full bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
                  autoFocus
                />
              </div>
              <Command.List className="max-h-[300px] overflow-y-auto p-2">
                <Command.Empty className="py-6 text-center text-sm text-muted-foreground">
                  No results found.
                </Command.Empty>
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
            </Command>
          </div>
        </div>
      )}
    </>
  )
}
