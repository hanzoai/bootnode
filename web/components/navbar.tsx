"use client"

import { useState } from "react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  ArrowRight,
  Database,
  Globe,
  KeyRound,
  Layers,
  Menu,
  Search,
  Wallet,
  Webhook,
  X,
  Shield,
  Building2,
  Zap,
  Code2,
  Blocks,
  BarChart3,
  Server,
  Bot,
  Lock,
  Cpu,
  Network,
  Coins,
  FileText,
  BookOpen,
  GraduationCap,
  GitBranch,
  MessageCircle,
  LifeBuoy,
  Activity,
} from "lucide-react"
import { BrandLogo } from "@/components/brand-logo"
import { CommandMenu } from "@/components/command-menu"
import { NavMenu } from "@/components/nav-menu"
import { getBrand } from "@/lib/brand"
import { getSdkPackage } from "@/lib/sdk-package"

// Reusable icon link for mega-menu items
function IconLink({
  href,
  icon: Icon,
  label,
  description,
  closeMenu,
}: {
  href: string
  icon: React.ElementType
  label: string
  description?: string
  closeMenu: () => void
}) {
  return (
    <Link href={href} onClick={closeMenu} className="block">
      <div className="group flex items-start gap-2 py-1">
        <Icon className="h-3.5 w-3.5 mt-0.5 text-muted-foreground group-hover:text-foreground transition-colors flex-shrink-0" />
        <div>
          <span className="text-sm text-foreground/80 group-hover:text-foreground transition-colors">
            {label}
          </span>
          {description && (
            <p className="text-xs text-muted-foreground">{description}</p>
          )}
        </div>
      </div>
    </Link>
  )
}

// Products mega-menu content
function ProductsContent({ closeMenu }: { closeMenu: () => void }) {
  const brand = getBrand()
  const { pkg: sdkPackage } = getSdkPackage()
  return (
    <div className="w-full">
      {/* Featured hero cards */}
      <div className="mb-4 pb-4 border-b border-border">
        <div className="grid grid-cols-3 gap-3">
          <Link
            href="/products/node"
            onClick={closeMenu}
            className="group flex items-start gap-3 p-3 rounded-xl bg-gradient-to-br from-blue-500/5 to-cyan-500/5 border border-border hover:border-blue-500/30 transition-all"
          >
            <div className="w-9 h-9 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
              <Globe className="h-5 w-5 text-blue-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground">
                  Node (RPC)
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
              </div>
              <p className="text-xs text-muted-foreground leading-snug mt-0.5">
                Multi-chain JSON-RPC with 99.999% uptime
              </p>
            </div>
          </Link>
          <Link
            href="/products/explorer"
            onClick={closeMenu}
            className="group flex items-start gap-3 p-3 rounded-xl bg-gradient-to-br from-emerald-500/5 to-teal-500/5 border border-border hover:border-emerald-500/30 transition-all"
          >
            <div className="w-9 h-9 rounded-lg bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
              <Search className="h-5 w-5 text-emerald-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground">
                  Explorer
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
              </div>
              <p className="text-xs text-muted-foreground leading-snug mt-0.5">
                Deploy your own branded block explorer
              </p>
            </div>
          </Link>
          <Link
            href="/products/mpc"
            onClick={closeMenu}
            className="group flex items-start gap-3 p-3 rounded-xl bg-gradient-to-br from-violet-500/5 to-purple-500/5 border border-border hover:border-violet-500/30 transition-all"
          >
            <div className="w-9 h-9 rounded-lg bg-violet-500/10 flex items-center justify-center flex-shrink-0">
              <KeyRound className="h-5 w-5 text-violet-500" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground">
                  MPC
                </span>
                <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
              </div>
              <p className="text-xs text-muted-foreground leading-snug mt-0.5">
                Threshold key management, 15+ chains
              </p>
            </div>
          </Link>
        </div>
      </div>

      {/* Category grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-x-6 gap-y-4">
        {/* RPC & Nodes */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            RPC & Nodes
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/products/node" icon={Globe} label="Multi-Chain RPC" closeMenu={closeMenu} />
            <IconLink href="/chains/ethereum" icon={Cpu} label="Ethereum" closeMenu={closeMenu} />
            <IconLink href="/chains/solana" icon={Cpu} label="Solana" closeMenu={closeMenu} />
            <IconLink href="/chains/base" icon={Cpu} label="Base" closeMenu={closeMenu} />
            <IconLink href="/chains" icon={ArrowRight} label="All 100+ Chains" closeMenu={closeMenu} />
          </div>
        </div>

        {/* Data APIs */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            Data APIs
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/products/data" icon={Database} label="Token API" closeMenu={closeMenu} />
            <IconLink href="/products/data" icon={Blocks} label="NFT API" closeMenu={closeMenu} />
            <IconLink href="/products/data" icon={Code2} label="Transfers API" closeMenu={closeMenu} />
            <IconLink href="/products/webhooks" icon={Webhook} label="Webhooks" closeMenu={closeMenu} />
          </div>
        </div>

        {/* Wallets & AA */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            Wallets & AA
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/products/wallets" icon={Wallet} label="Smart Wallets" closeMenu={closeMenu} />
            <IconLink href="/products/wallets" icon={Zap} label="Gas Sponsorship" closeMenu={closeMenu} />
            <IconLink href="/products/wallets" icon={Lock} label="Session Keys" closeMenu={closeMenu} />
          </div>
        </div>

        {/* Infrastructure */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            Infrastructure
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/products/rollups" icon={Layers} label="Custom Rollups" closeMenu={closeMenu} />
            <IconLink href="/products/explorer" icon={Search} label="Block Explorer" closeMenu={closeMenu} />
            <IconLink href="/products/mpc" icon={KeyRound} label="MPC Network" closeMenu={closeMenu} />
            <IconLink href="/products/node" icon={Server} label="Archive Nodes" closeMenu={closeMenu} />
          </div>
        </div>

        {/* Security & Keys */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            Security
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/products/mpc" icon={Shield} label="CGGMP21 (ECDSA)" closeMenu={closeMenu} />
            <IconLink href="/products/mpc" icon={Shield} label="FROST (EdDSA)" closeMenu={closeMenu} />
            <IconLink href="/products/mpc" icon={KeyRound} label="Key Resharing" closeMenu={closeMenu} />
            <IconLink href="/products/mpc" icon={Network} label="Threshold Signing" closeMenu={closeMenu} />
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-border flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-md px-2.5 py-1 font-mono text-[10px] bg-secondary text-foreground">
            {`npm i ${sdkPackage}`}
          </div>
          <span className="text-[10px] text-muted-foreground">
            Install {brand.name} SDK
          </span>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-7 text-xs px-3 bg-transparent border-border text-foreground/80 hover:bg-accent hover:text-foreground"
            asChild
          >
            <Link href="/docs" onClick={closeMenu}>
              Docs
            </Link>
          </Button>
          <Button
            size="sm"
            className="bg-primary text-primary-foreground hover:bg-primary/90 h-7 text-xs px-3"
            asChild
          >
            <Link href="/dashboard" onClick={closeMenu}>
              All Products
              <ArrowRight className="ml-1 h-3 w-3" />
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}

// Solutions mega-menu content
function SolutionsContent({ closeMenu }: { closeMenu: () => void }) {
  return (
    <div className="w-full flex gap-6">
      {/* Left: featured panels */}
      <div className="w-64 flex-shrink-0 space-y-3">
        <Link
          href="/contact"
          onClick={closeMenu}
          className="block p-4 rounded-xl bg-gradient-to-br from-blue-500/5 to-cyan-500/5 border border-border/50 hover:border-border transition-all group"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 rounded-lg bg-foreground/10 flex items-center justify-center">
              <Building2 className="h-4 w-4 text-foreground" />
            </div>
            <h3 className="text-foreground font-semibold text-sm">Enterprise</h3>
          </div>
          <p className="text-muted-foreground text-xs leading-relaxed mb-2">
            Dedicated RPC, custom rollups, managed MPC clusters, and SLAs for
            scale.
          </p>
          <span className="text-xs font-medium text-foreground/70 group-hover:text-foreground transition-colors inline-flex items-center gap-1">
            Contact sales <ArrowRight className="h-3 w-3" />
          </span>
        </Link>

        <Link
          href="/pricing"
          onClick={closeMenu}
          className="block p-4 rounded-xl bg-gradient-to-br from-violet-500/5 to-purple-500/5 border border-border/50 hover:border-border transition-all group"
        >
          <div className="flex items-center gap-3 mb-2">
            <div className="w-8 h-8 rounded-lg bg-foreground/10 flex items-center justify-center">
              <Shield className="h-4 w-4 text-foreground" />
            </div>
            <h3 className="text-foreground font-semibold text-sm">
              Startup Program
            </h3>
          </div>
          <p className="text-muted-foreground text-xs leading-relaxed mb-2">
            Free tier with 100M compute units/mo. Scale as you grow.
          </p>
          <span className="text-xs font-medium text-foreground/70 group-hover:text-foreground transition-colors inline-flex items-center gap-1">
            Get started <ArrowRight className="h-3 w-3" />
          </span>
        </Link>
      </div>

      {/* Right: columns */}
      <div className="flex-1 grid grid-cols-3 gap-x-6 gap-y-4">
        {/* By Use Case */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            Use Cases
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/products/node" icon={Globe} label="DApp Backend" description="RPC + Data APIs for any dApp" closeMenu={closeMenu} />
            <IconLink href="/products/wallets" icon={Wallet} label="User Onboarding" description="Smart wallets, no seed phrase" closeMenu={closeMenu} />
            <IconLink href="/products/rollups" icon={Layers} label="Launch a Chain" description="Custom L2 with your gas token" closeMenu={closeMenu} />
            <IconLink href="/products/mpc" icon={KeyRound} label="Treasury Security" description="MPC key management for funds" closeMenu={closeMenu} />
            <IconLink href="/products/explorer" icon={Search} label="Chain Transparency" description="Branded explorer for your network" closeMenu={closeMenu} />
          </div>
        </div>

        {/* By Role */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            By Role
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/docs/quickstart" icon={Code2} label="Developers" description="SDKs, APIs, quickstarts" closeMenu={closeMenu} />
            <IconLink href="/products/rollups" icon={Building2} label="Foundations" description="Launch and manage L2s" closeMenu={closeMenu} />
            <IconLink href="/products/mpc" icon={Shield} label="Security Teams" description="MPC, audit trails, compliance" closeMenu={closeMenu} />
            <IconLink href="/products/data" icon={BarChart3} label="Data Teams" description="Indexed chain data + analytics" closeMenu={closeMenu} />
          </div>
        </div>

        {/* By Chain */}
        <div className="space-y-1.5">
          <h3 className="text-[10px] font-semibold uppercase tracking-wider mb-2 text-muted-foreground">
            By Chain
          </h3>
          <div className="space-y-0.5">
            <IconLink href="/chains/ethereum" icon={Coins} label="Ethereum" closeMenu={closeMenu} />
            <IconLink href="/chains/solana" icon={Coins} label="Solana" closeMenu={closeMenu} />
            <IconLink href="/chains/base" icon={Coins} label="Base" closeMenu={closeMenu} />
            <IconLink href="/chains/arbitrum" icon={Coins} label="Arbitrum" closeMenu={closeMenu} />
            <IconLink href="/chains/polygon" icon={Coins} label="Polygon" closeMenu={closeMenu} />
            <IconLink href="/chains" icon={ArrowRight} label="All 100+ Chains" closeMenu={closeMenu} />
          </div>
        </div>
      </div>
    </div>
  )
}

const chains = [
  { name: "Ethereum", href: "/chains/ethereum" },
  { name: "Solana", href: "/chains/solana" },
  { name: "Base", href: "/chains/base" },
  { name: "Arbitrum", href: "/chains/arbitrum" },
  { name: "Polygon", href: "/chains/polygon" },
  { name: "View All 100+", href: "/chains" },
]

export function Navbar() {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        {/* Logo */}
        <Link href="/" className="mr-6 flex-shrink-0">
          <BrandLogo />
        </Link>

        {/* Desktop Navigation */}
        <div className="hidden lg:flex items-center space-x-4 flex-1">
          <NavMenu label="Products">
            {(closeMenu) => <ProductsContent closeMenu={closeMenu} />}
          </NavMenu>

          <NavMenu label="Solutions">
            {(closeMenu) => <SolutionsContent closeMenu={closeMenu} />}
          </NavMenu>

          <Link
            href="/docs"
            className="text-muted-foreground hover:text-foreground transition-colors text-sm font-medium"
          >
            Docs
          </Link>

          <Link
            href="/pricing"
            className="text-muted-foreground hover:text-foreground transition-colors text-sm font-medium"
          >
            Pricing
          </Link>
        </div>

        {/* Search + Actions */}
        <div className="ml-auto flex items-center gap-4">
          <CommandMenu />
          <Button variant="ghost" size="sm" asChild className="hidden sm:flex">
            <Link href="/login">Sign In</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/dashboard">Go to Dashboard</Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="container border-t pb-4 pt-4 lg:hidden">
          <nav className="flex flex-col gap-4">
            <div className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Products
            </div>
            <Link href="/products/node" className="text-sm font-medium pl-2" onClick={() => setIsOpen(false)}>
              Node (RPC)
            </Link>
            <Link href="/products/data" className="text-sm font-medium pl-2" onClick={() => setIsOpen(false)}>
              Data APIs
            </Link>
            <Link href="/products/wallets" className="text-sm font-medium pl-2" onClick={() => setIsOpen(false)}>
              Smart Wallets
            </Link>
            <Link href="/products/explorer" className="text-sm font-medium pl-2" onClick={() => setIsOpen(false)}>
              Explorer
            </Link>
            <Link href="/products/mpc" className="text-sm font-medium pl-2" onClick={() => setIsOpen(false)}>
              MPC
            </Link>
            <Link href="/products/rollups" className="text-sm font-medium pl-2" onClick={() => setIsOpen(false)}>
              Rollups
            </Link>
            <Link href="/products/webhooks" className="text-sm font-medium pl-2" onClick={() => setIsOpen(false)}>
              Webhooks
            </Link>
            <div className="border-t pt-4 mt-2" />
            <Link href="/docs" className="text-sm font-medium" onClick={() => setIsOpen(false)}>
              Docs
            </Link>
            <Link href="/pricing" className="text-sm font-medium" onClick={() => setIsOpen(false)}>
              Pricing
            </Link>
            <Link href="/chains" className="text-sm font-medium" onClick={() => setIsOpen(false)}>
              Chains
            </Link>
          </nav>
        </div>
      )}
    </header>
  )
}
