"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import {
  ArrowRight,
  CheckCircle2,
  Code2,
  FileSearch,
  Globe,
  LayoutDashboard,
  Search,
  Shield,
  Zap,
  Database,
  BarChart3,
  Braces,
  Palette,
} from "lucide-react"
import { getBrand } from "@/lib/brand"

export default function ExplorerProductPage() {
  const brand = getBrand()

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden border-b bg-gradient-to-b from-background to-muted/20">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:14px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
        <div className="container relative py-24 md:py-32 lg:py-40">
          <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
            <Badge variant="secondary" className="mb-4">
              <Search className="mr-1 h-3 w-3" />
              Block Explorer
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              Your chain,{" "}
              <span className="bg-gradient-to-r from-emerald-500 to-teal-500 bg-clip-text text-transparent">
                fully visible
              </span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
              Deploy a branded block explorer for any EVM chain, rollup, or
              subnet. Full transaction search, contract verification, token
              tracking, and analytics—ready in minutes, managed by {brand.name}.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <Button size="xl" asChild>
                <Link href="/dashboard">
                  Deploy Explorer
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button size="xl" variant="outline" asChild>
                <Link href="/docs/explorer">Read the Docs</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-b bg-muted/30 py-12">
        <div className="container">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <StatItem label="Explorers Deployed" value="120+" />
            <StatItem label="Indexed Blocks" value="5B+" />
            <StatItem label="Verified Contracts" value="800K+" />
            <StatItem label="Time to Deploy" value="<5 min" />
          </div>
        </div>
      </section>

      {/* Why Your Own Explorer */}
      <section className="border-b py-24">
        <div className="container">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
            <div className="flex flex-col justify-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Why deploy your own explorer?
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Public explorers are generic. Your chain deserves a dedicated
                explorer with your branding, your analytics, and an API your
                developers can rely on.
              </p>
              <ul className="mt-8 space-y-4">
                {[
                  {
                    title: "Full brand control",
                    desc: "Your logo, colors, domain, and custom links. The explorer feels like part of your ecosystem, not a third-party tool.",
                  },
                  {
                    title: "Dedicated indexing",
                    desc: "No shared infrastructure. Your explorer indexes your chain with priority, delivering sub-second search results.",
                  },
                  {
                    title: "Developer API",
                    desc: "Every explorer includes a full REST API for contract verification, transaction lookup, token balances, and analytics export.",
                  },
                  {
                    title: "Works with any EVM chain",
                    desc: "Ethereum L1, OP Stack rollups, Arbitrum Orbit, Lux subnets, or any EVM-compatible network.",
                  },
                ].map((item) => (
                  <li key={item.title} className="flex items-start gap-3">
                    <CheckCircle2 className="mt-1 h-5 w-5 shrink-0 text-green-500" />
                    <div>
                      <div className="font-semibold">{item.title}</div>
                      <div className="text-sm text-muted-foreground">
                        {item.desc}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col justify-center gap-6">
              <Card className="border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-teal-500/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <FileSearch className="h-5 w-5 text-emerald-500" />
                    Transaction Search
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Search by address, transaction hash, block number, token
                    name, or ENS. Advanced filters for value ranges, method
                    signatures, and date ranges. Results in milliseconds.
                  </p>
                </CardContent>
              </Card>
              <Card className="border-teal-500/20 bg-gradient-to-br from-teal-500/5 to-cyan-500/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-teal-500" />
                    Contract Verification
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Solidity and Vyper source verification with multi-file and
                    JSON input support. Verified contracts get read/write UI,
                    ABI decoding, and event log parsing automatically.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* What's Included */}
      <section className="border-b bg-muted/30 py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything included out of the box
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              A production-ready block explorer with indexing, API, analytics, and
              branding—fully managed by {brand.name}.
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<Search className="h-6 w-6" />}
              title="Full-Text Search"
              description="Instant search across transactions, addresses, tokens, blocks, and verified contracts. Autocomplete and fuzzy matching included."
            />
            <FeatureCard
              icon={<Shield className="h-6 w-6" />}
              title="Contract Verification"
              description="Solidity and Vyper multi-file verification. Automatically generates read/write UI, event decoding, and ABI explorer for verified contracts."
            />
            <FeatureCard
              icon={<Database className="h-6 w-6" />}
              title="Token Tracking"
              description="ERC-20, ERC-721, and ERC-1155 token pages with holder lists, transfer history, and real-time supply tracking out of the box."
            />
            <FeatureCard
              icon={<BarChart3 className="h-6 w-6" />}
              title="On-Chain Analytics"
              description="Built-in charts for daily transactions, active addresses, gas usage, contract deployments, and token transfer volume."
            />
            <FeatureCard
              icon={<Braces className="h-6 w-6" />}
              title="REST & GraphQL API"
              description="Etherscan-compatible REST API plus a GraphQL endpoint. Your developers can integrate programmatic access from day one."
            />
            <FeatureCard
              icon={<Palette className="h-6 w-6" />}
              title="Custom Branding"
              description="Your logo, color scheme, favicon, domain, and footer links. White-label the explorer as a seamless part of your chain ecosystem."
            />
            <FeatureCard
              icon={<Zap className="h-6 w-6" />}
              title="Real-Time Indexing"
              description="New blocks and transactions appear within seconds. WebSocket subscriptions for live updates on addresses and contract events."
            />
            <FeatureCard
              icon={<LayoutDashboard className="h-6 w-6" />}
              title="Admin Dashboard"
              description={`Manage verified contracts, featured tokens, banner announcements, and API keys through the ${brand.name} dashboard.`}
            />
            <FeatureCard
              icon={<Globe className="h-6 w-6" />}
              title="Multi-Chain Ready"
              description="Deploy explorers for multiple chains from one account. Each explorer gets its own domain, branding, and indexer."
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-b py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Live in under five minutes
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Connect your chain's RPC, customize the look, and {brand.name} handles
              the rest.
            </p>
          </div>
          <div className="mt-16 grid gap-6 md:grid-cols-4">
            <StepCard
              step="1"
              title="Connect"
              description="Provide your chain's RPC endpoint and chain ID. Works with any EVM-compatible network."
            />
            <StepCard
              step="2"
              title="Brand"
              description="Upload your logo, choose colors, set your custom domain, and configure footer links."
            />
            <StepCard
              step="3"
              title="Index"
              description={`${brand.name} spins up a dedicated indexer. Historical blocks are backfilled while new blocks stream in real-time.`}
            />
            <StepCard
              step="4"
              title="Launch"
              description="Your explorer is live. Share the URL, enable the API, and let your community explore."
            />
          </div>
        </div>
      </section>

      {/* Code Example */}
      <section className="border-b bg-muted/30 py-24">
        <div className="container">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
            <div className="flex flex-col justify-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Etherscan-compatible API included
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Every explorer ships with a REST API that is compatible with the
                Etherscan API standard. Existing tools, scripts, and integrations
                work without changes.
              </p>
              <div className="mt-8">
                <Button asChild>
                  <Link href="/docs/explorer/api">
                    API Reference
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
            <div className="flex items-center">
              <Card className="w-full">
                <CardContent className="p-0">
                  <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-6 text-sm text-zinc-100">
                    <code>{`# Verify a contract
curl -X POST https://explorer.yourchain.com/api \\
  -d "module=contract" \\
  -d "action=verifysourcecode" \\
  -d "contractaddress=0x..." \\
  -d "sourceCode=@MyContract.sol" \\
  -d "compilerversion=v0.8.20"

# Get token holders
curl "https://explorer.yourchain.com/api\\
  ?module=token\\
  &action=tokenholderlist\\
  &contractaddress=0x...\\
  &page=1&offset=100"

# Transaction list for address
curl "https://explorer.yourchain.com/api\\
  ?module=account\\
  &action=txlist\\
  &address=0x...\\
  &startblock=0&endblock=latest"`}</code>
                  </pre>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24">
        <div className="container">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-20 sm:px-12 sm:py-28">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff1a_1px,transparent_1px),linear-gradient(to_bottom,#ffffff1a_1px,transparent_1px)] bg-[size:14px_24px]" />
            <div className="relative mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Every chain deserves a great explorer
              </h2>
              <p className="mt-4 text-lg text-white/80">
                Deploy a branded, fully-featured block explorer for your network
                in minutes. Free tier available for testnets.
              </p>
              <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
                <Button
                  size="xl"
                  className="bg-white text-emerald-600 hover:bg-white/90"
                  asChild
                >
                  <Link href="/dashboard">
                    Deploy Explorer
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  size="xl"
                  variant="outline"
                  className="border-white/30 bg-transparent text-white hover:bg-white/10"
                  asChild
                >
                  <Link href="/docs/explorer">Read the Docs</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  )
}

function StatItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="text-center">
      <div className="text-2xl font-bold md:text-3xl">{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{label}</div>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <CardTitle className="mt-4">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}

function StepCard({
  step,
  title,
  description,
}: {
  step: string
  title: string
  description: string
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary text-sm font-bold text-primary-foreground">
          {step}
        </div>
        <CardTitle className="mt-4">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}
