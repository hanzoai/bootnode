import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import { ChainGrid } from "@/components/chain-grid"
import { CodeDemo } from "@/components/code-demo"
import { getBrand } from "@/lib/brand"
import {
  ArrowRight,
  Blocks,
  Code2,
  Database,
  Globe,
  Layers,
  Shield,
  Wallet,
  Webhook,
  Zap,
} from "lucide-react"

export default function HomePage() {
  const brand = getBrand()
  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b bg-gradient-to-b from-background to-muted/20">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:14px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
        <div className="container relative py-24 md:py-32 lg:py-40">
          <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
            <Badge variant="secondary" className="mb-4">
              <Zap className="mr-1 h-3 w-3" />
              100+ Chains Supported
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              Build anything{" "}
              <span
                className="bg-clip-text text-transparent"
                style={{ backgroundImage: `linear-gradient(to right, ${brand.colors.accent}, ${brand.colors.accentEnd})` }}
              >
                onchain
              </span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
              The complete blockchain development platform. Multi-chain RPC, Token
              APIs, NFT APIs, Smart Wallets, Account Abstraction, and more. Ship
              faster with {brand.name}.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <Button size="xl" asChild>
                <Link href="/dashboard">
                  Start Building
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button size="xl" variant="outline" asChild>
                <Link href="/docs">View Documentation</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Products Grid */}
      <section className="border-b py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to build Web3
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              From RPC endpoints to account abstraction, {brand.name} provides the
              complete infrastructure stack for blockchain developers.
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <ProductCard
              icon={<Globe className="h-6 w-6" />}
              title="Node"
              description="Build and scale your app on the most powerful web3 development platform with 99.999% uptime."
              href="/products/node"
            />
            <ProductCard
              icon={<Database className="h-6 w-6" />}
              title="Data"
              description="Access complete blockchain data through one unified API that grows with you. Tokens, NFTs, transfers."
              href="/products/data"
            />
            <ProductCard
              icon={<Wallet className="h-6 w-6" />}
              title="Wallets"
              description="Onboard users with secure, easy-to-use smart wallets. No seed phrase or gas required."
              href="/products/wallets"
            />
            <ProductCard
              icon={<Layers className="h-6 w-6" />}
              title="Rollups"
              description="Launch a custom rollup with native developer tools and scale to millions of users."
              href="/products/rollups"
            />
          </div>
        </div>
      </section>

      {/* Interactive Demo */}
      <section className="border-b bg-muted/30 py-24">
        <div className="container">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
            <div className="flex flex-col justify-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Query the blockchain instantly
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Get started in seconds with our JSON-RPC API. Access real-time
                blockchain data across 100+ networks with a single API key.
              </p>
              <div className="mt-8 space-y-4">
                <FeatureItem
                  icon={<Zap className="h-5 w-5 text-yellow-500" />}
                  title="Lightning Fast"
                  description="Sub-100ms response times with global edge caching"
                />
                <FeatureItem
                  icon={<Shield className="h-5 w-5 text-green-500" />}
                  title="99.999% Uptime"
                  description="Enterprise-grade reliability with automatic failover"
                />
                <FeatureItem
                  icon={<Globe className="h-5 w-5 text-blue-500" />}
                  title="100+ Chains"
                  description="Ethereum, Solana, Base, Arbitrum, and 96 more"
                />
              </div>
              <div className="mt-8">
                <Button asChild>
                  <Link href="/docs/quickstart">
                    Get Started
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>
            <CodeDemo />
          </div>
        </div>
      </section>

      {/* Supported Chains */}
      <section className="border-b py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              100+ chains, one API
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Access every major blockchain through a unified interface. From
              Ethereum to Solana, Bitcoin to Base—we've got you covered.
            </p>
          </div>
          <ChainGrid />
          <div className="mt-12 text-center">
            <Button variant="outline" size="lg" asChild>
              <Link href="/chains">
                View All Chains
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Features/Guides Section */}
      <section className="border-b py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Guides to get started
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Learn how to integrate {brand.name} into your project with our
              comprehensive guides and tutorials.
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <GuideCard
              title="Blockchain Basics"
              description="Get started by learning how to connect your app to Ethereum using our JSON-RPC API."
              href="/docs/quickstart"
              badge="Quickstart"
            />
            <GuideCard
              title="Smart Wallets"
              description="Create a Next.js app with embedded smart wallets, social login, and gas-less transactions."
              href="/docs/wallets/quickstart"
              badge="Tutorial"
            />
            <GuideCard
              title="Real-time Webhooks"
              description="Receive fast and reliable HTTP POST requests for onchain events across 100+ chains."
              href="/docs/webhooks/quickstart"
              badge="Quickstart"
            />
            <GuideCard
              title="Authentication"
              description="Add authentication and embedded smart wallets to your existing React project."
              href="/docs/auth/quickstart"
              badge="Tutorial"
            />
            <GuideCard
              title="WebSocket Subscriptions"
              description="Subscribe to pending transactions, log events, new blocks and more using WebSockets."
              href="/docs/websockets/quickstart"
              badge="Quickstart"
            />
            <GuideCard
              title="Account Abstraction"
              description="Enable existing EOAs to benefit from batching actions, sponsoring transactions, and more."
              href="/docs/aa/quickstart"
              badge="Guide"
            />
          </div>
        </div>
      </section>

      {/* API Products */}
      <section className="border-b bg-muted/30 py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Powerful APIs for every use case
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              From basic RPC calls to complex account abstraction flows, our APIs
              handle the heavy lifting so you can focus on building.
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <APICard
              icon={<Globe className="h-6 w-6" />}
              title="RPC API"
              description="JSON-RPC proxy with load balancing, caching, and automatic failover across 100+ chains."
              features={["Multi-chain support", "MEV protection", "Archive nodes"]}
            />
            <APICard
              icon={<Database className="h-6 w-6" />}
              title="Token API"
              description="Get ERC-20 token balances, metadata, prices, and transfer history in a single call."
              features={["Real-time prices", "Historical data", "Batch queries"]}
            />
            <APICard
              icon={<Blocks className="h-6 w-6" />}
              title="NFT API"
              description="Fetch NFT metadata, ownership, collections, and marketplace data across all chains."
              features={["Media resolution", "Rarity data", "Floor prices"]}
            />
            <APICard
              icon={<Code2 className="h-6 w-6" />}
              title="Transfers API"
              description="Query transaction history and token transfers with powerful filtering options."
              features={["Asset transfers", "Internal txs", "Cross-chain"]}
            />
            <APICard
              icon={<Webhook className="h-6 w-6" />}
              title="Webhooks"
              description="Get real-time notifications for onchain events without polling. HMAC signed."
              features={["Address activity", "NFT transfers", "Custom filters"]}
            />
            <APICard
              icon={<Wallet className="h-6 w-6" />}
              title="Smart Wallets"
              description="ERC-4337 account abstraction with gas sponsorship, batched transactions, and social login."
              features={["Gasless txs", "Session keys", "Social recovery"]}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24">
        <div className="container">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-20 sm:px-12 sm:py-28">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff1a_1px,transparent_1px),linear-gradient(to_bottom,#ffffff1a_1px,transparent_1px)] bg-[size:14px_24px]" />
            <div className="relative mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Ready to build the future?
              </h2>
              <p className="mt-4 text-lg text-white/80">
                Join thousands of developers building on {brand.name}. Get started for
                free with 100M compute units per month.
              </p>
              <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
                <Button
                  size="xl"
                  className="bg-white text-blue-600 hover:bg-white/90"
                  asChild
                >
                  <Link href="/dashboard">
                    Start Building Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  size="xl"
                  variant="outline"
                  className="border-white/30 bg-transparent text-white hover:bg-white/10"
                  asChild
                >
                  <Link href="/contact">Contact Sales</Link>
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

function ProductCard({
  icon,
  title,
  description,
  href,
}: {
  icon: React.ReactNode
  title: string
  description: string
  href: string
}) {
  return (
    <Link href={href}>
      <Card className="group h-full transition-colors hover:border-foreground/20">
        <CardHeader>
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
            {icon}
          </div>
          <CardTitle className="mt-4">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <span className="inline-flex items-center text-sm font-medium text-primary">
            Learn more
            <ArrowRight className="ml-1 h-4 w-4" />
          </span>
        </CardContent>
      </Card>
    </Link>
  )
}

function FeatureItem({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex gap-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted">
        {icon}
      </div>
      <div>
        <h3 className="font-semibold">{title}</h3>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}

function GuideCard({
  title,
  description,
  href,
  badge,
}: {
  title: string
  description: string
  href: string
  badge: string
}) {
  return (
    <Link href={href}>
      <Card className="group h-full transition-colors hover:border-foreground/20">
        <CardHeader>
          <Badge variant="secondary" className="w-fit">
            {badge}
          </Badge>
          <CardTitle className="mt-2">{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <span className="inline-flex items-center text-sm font-medium text-primary">
            Get started
            <ArrowRight className="ml-1 h-4 w-4 transition-transform group-hover:translate-x-1" />
          </span>
        </CardContent>
      </Card>
    </Link>
  )
}

function APICard({
  icon,
  title,
  description,
  features,
}: {
  icon: React.ReactNode
  title: string
  description: string
  features: string[]
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
          {icon}
        </div>
        <CardTitle className="mt-4">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {features.map((feature) => (
            <li
              key={feature}
              className="flex items-center text-sm text-muted-foreground"
            >
              <div className="mr-2 h-1.5 w-1.5 rounded-full bg-primary" />
              {feature}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
