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
  Globe,
  KeyRound,
  Lock,
  Network,
  RefreshCw,
  Server,
  Shield,
  ShieldCheck,
  Users,
  Wallet,
  Zap,
} from "lucide-react"
import { getBrand } from "@/lib/brand"

export default function MPCProductPage() {
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
              <KeyRound className="mr-1 h-3 w-3" />
              MPC Key Management
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              No single point{" "}
              <span className="bg-gradient-to-r from-violet-500 to-purple-500 bg-clip-text text-transparent">
                of compromise
              </span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
              Launch a distributed MPC node cluster for institutional-grade key
              management. Threshold signatures across 15+ chains—no single node
              ever holds the full private key. Powered by Lux MPC.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <Button size="xl" asChild>
                <Link href="/contact">
                  Request Access
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button size="xl" variant="outline" asChild>
                <Link href="/docs/mpc">Read the Docs</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="border-b bg-muted/30 py-12">
        <div className="container">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <StatItem label="Supported Chains" value="15+" />
            <StatItem label="Signing Latency" value="<500ms" />
            <StatItem label="Key Schemes" value="3" />
            <StatItem label="Uptime SLA" value="99.99%" />
          </div>
        </div>
      </section>

      {/* Why MPC */}
      <section className="border-b py-24">
        <div className="container">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
            <div className="flex flex-col justify-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Why MPC over traditional wallets?
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Hardware wallets create a single point of failure. Multisig
                wallets are expensive on-chain. MPC splits the private key across
                distributed nodes so no single party—or attacker—can sign alone.
              </p>
              <ul className="mt-8 space-y-4">
                {[
                  {
                    title: "No single point of compromise",
                    desc: "Keys are split into threshold shares across independent nodes. Even if t-1 nodes are compromised, the key is safe.",
                  },
                  {
                    title: "Byzantine fault tolerance",
                    desc: "The cluster continues signing even when some nodes go offline. Configurable t-of-n threshold (e.g., 3-of-5).",
                  },
                  {
                    title: "Chain-agnostic",
                    desc: "One MPC cluster signs for Bitcoin, Ethereum, Solana, XRP, Lux, TON, and 10+ more chains. ECDSA and EdDSA.",
                  },
                  {
                    title: "Key resharing",
                    desc: "Rotate participants, change the threshold, or add new nodes—without generating new keys or moving funds.",
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
              <Card className="border-violet-500/20 bg-gradient-to-br from-violet-500/5 to-purple-500/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Lock className="h-5 w-5 text-violet-500" />
                    CGGMP21 (ECDSA)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    State-of-the-art threshold ECDSA protocol for Bitcoin,
                    Ethereum, Polygon, BNB, XRP, and all secp256k1 chains.
                    Replaces the older GG18 scheme with stronger security
                    proofs and fewer communication rounds.
                  </p>
                </CardContent>
              </Card>
              <Card className="border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-fuchsia-500/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="h-5 w-5 text-purple-500" />
                    FROST (EdDSA)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Threshold Schnorr signatures for Ed25519 chains like
                    Solana and TON. Supports Bitcoin Taproot. Efficient
                    two-round signing with native aggregation.
                  </p>
                </CardContent>
              </Card>
              <Card className="border-fuchsia-500/20 bg-gradient-to-br from-fuchsia-500/5 to-pink-500/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <RefreshCw className="h-5 w-5 text-fuchsia-500" />
                    LSS (Resharing)
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Linear Secret Sharing enables dynamic resharing—change
                    participants, rotate shares, or adjust the threshold
                    without regenerating keys or moving assets on-chain.
                  </p>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Supported Chains */}
      <section className="border-b bg-muted/30 py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              One cluster, every chain
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              A single MPC deployment generates wallets and signs transactions
              across all supported networks.
            </p>
          </div>
          <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <ChainCard
              protocol="ECDSA"
              chains={[
                "Bitcoin (BTC)",
                "Ethereum (ETH)",
                "Lux Network (LUX)",
                "XRP Ledger (XRPL)",
                "Polygon",
                "BNB Chain",
                "Arbitrum",
                "Base",
                "Optimism",
              ]}
            />
            <ChainCard
              protocol="EdDSA"
              chains={[
                "Solana (SOL)",
                "TON",
              ]}
            />
            <ChainCard
              protocol="Coming Soon"
              chains={[
                "Cosmos (ATOM)",
                "Sui",
                "Aptos",
                "Polkadot",
              ]}
            />
          </div>
        </div>
      </section>

      {/* What's Included */}
      <section className="border-b py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Production-grade MPC infrastructure
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              {brand.name} deploys and manages the full MPC stack: nodes, messaging,
              encrypted storage, API, and monitoring.
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<Server className="h-6 w-6" />}
              title="Managed Node Cluster"
              description={`${brand.name} provisions a Kubernetes StatefulSet of MPC nodes with stable DNS, persistent encrypted storage, health checks, and auto-recovery.`}
            />
            <FeatureCard
              icon={<KeyRound className="h-6 w-6" />}
              title="Distributed Key Generation"
              description="Keys are generated collaboratively across all nodes. No single node—or operator—ever sees the full private key. Zero-knowledge proofs verify each share."
            />
            <FeatureCard
              icon={<Zap className="h-6 w-6" />}
              title="Threshold Signing"
              description="Only t-of-n nodes are needed to produce a valid signature. Sub-second signing latency for both ECDSA and EdDSA across all supported chains."
            />
            <FeatureCard
              icon={<RefreshCw className="h-6 w-6" />}
              title="Key Resharing"
              description="Rotate participants, change threshold, or add new nodes without regenerating keys. Assets stay at the same addresses throughout."
            />
            <FeatureCard
              icon={<ShieldCheck className="h-6 w-6" />}
              title="Encrypted at Rest & In Transit"
              description="Key shares are encrypted with AES-256 in BadgerDB. Node-to-node communication uses NATS with TLS. Post-quantum TLS available."
            />
            <FeatureCard
              icon={<Users className="h-6 w-6" />}
              title="JWT & OIDC Authentication"
              description="REST API secured with JWT tokens, OIDC login via Lux ID / Hanzo ID, role-based API keys, MFA support, and full audit logging."
            />
            <FeatureCard
              icon={<Globe className="h-6 w-6" />}
              title="REST API & Go Client"
              description="Full HTTP API for wallet creation, signing, and resharing. Go client library for direct integration. Etherscan-compatible bridge endpoint."
            />
            <FeatureCard
              icon={<Network className="h-6 w-6" />}
              title="NATS + Consul Messaging"
              description="Nodes coordinate via NATS pub/sub with JetStream for reliable delivery. Consul handles service discovery and health checks."
            />
            <FeatureCard
              icon={<Wallet className="h-6 w-6" />}
              title="Multi-Chain Wallets"
              description="One keygen ceremony produces addresses for all supported chains. Derive BTC, ETH, SOL, XRP, and LUX wallets from a single distributed key."
            />
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-b bg-muted/30 py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              From zero to signing in minutes
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              {brand.name} handles node provisioning, networking, and key ceremony
              orchestration. You call the API.
            </p>
          </div>
          <div className="mt-16 grid gap-6 md:grid-cols-4">
            <StepCard
              step="1"
              title="Configure"
              description="Choose your threshold (e.g., 3-of-5), select supported chains, and configure authentication. All through the dashboard or API."
            />
            <StepCard
              step="2"
              title="Deploy"
              description={`${brand.name} provisions MPC nodes as a Kubernetes StatefulSet with encrypted storage, NATS messaging, and Consul discovery.`}
            />
            <StepCard
              step="3"
              title="Generate Keys"
              description="Trigger a distributed keygen ceremony via the API. Nodes collaboratively generate key shares—no full key is ever assembled."
            />
            <StepCard
              step="4"
              title="Sign"
              description="Submit signing requests via REST API. Any t-of-n nodes produce a valid ECDSA or EdDSA signature in under 500ms."
            />
          </div>
        </div>
      </section>

      {/* Code Example */}
      <section className="border-b py-24">
        <div className="container">
          <div className="grid gap-12 lg:grid-cols-2 lg:gap-16">
            <div className="flex flex-col justify-center">
              <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
                Simple API, serious security
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Create wallets and sign transactions with straightforward REST
                calls. The MPC protocol complexity is handled by the node cluster.
              </p>
              <div className="mt-8">
                <Button asChild>
                  <Link href="/docs/mpc/api">
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
                    <code>{`# Create a distributed wallet
curl -X POST https://mpc.yourorg.com/api/v1/wallets \\
  -H "Authorization: Bearer \$TOKEN" \\
  -d '{"name": "treasury", "chains": ["ETH", "BTC", "SOL"]}'

# Response: addresses for every chain
{
  "wallet_id": "w_8f3a...",
  "addresses": {
    "ETH": "0x7c2e...9a1f",
    "BTC": "bc1q...xm4p",
    "SOL": "7Kf2...Rn3v"
  },
  "threshold": "3-of-5",
  "protocol": "CGGMP21+FROST"
}

# Sign an Ethereum transaction
curl -X POST https://mpc.yourorg.com/api/v1/sign \\
  -H "Authorization: Bearer \$TOKEN" \\
  -d '{
    "wallet_id": "w_8f3a...",
    "chain": "ETH",
    "tx": {
      "to": "0xdead...beef",
      "value": "1000000000000000000",
      "gas": 21000
    }
  }'`}</code>
                  </pre>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section className="border-b bg-muted/30 py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Built for institutions
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              From treasury management to cross-chain bridges, MPC key management
              provides the security foundation.
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <UseCaseCard
              title="Treasury Management"
              description="Multi-sig-grade security without on-chain overhead. CFOs and treasury teams sign with policy-controlled approval flows."
            />
            <UseCaseCard
              title="Cross-Chain Bridges"
              description="Secure bridge validators with threshold signatures. No single validator can authorize a withdrawal."
            />
            <UseCaseCard
              title="Custodial Wallets"
              description="Offer institutional custody with distributed key management. SOC 2 and regulatory compliance built in."
            />
            <UseCaseCard
              title="DeFi Protocols"
              description="Protect protocol-owned liquidity with MPC-secured admin keys. Eliminate single-key risks for governance actions."
            />
            <UseCaseCard
              title="Exchange Hot Wallets"
              description="Replace single-key hot wallets with threshold signing. Faster than multisig, more secure than HSMs."
            />
            <UseCaseCard
              title="Automated Signing"
              description="Integrate MPC signing into CI/CD pipelines, bots, and automated trading systems with API key authentication."
            />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24">
        <div className="container">
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-20 sm:px-12 sm:py-28">
            <div className="absolute inset-0 bg-[linear-gradient(to_right,#ffffff1a_1px,transparent_1px),linear-gradient(to_bottom,#ffffff1a_1px,transparent_1px)] bg-[size:14px_24px]" />
            <div className="relative mx-auto max-w-2xl text-center">
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                Your keys. Distributed. Never exposed.
              </h2>
              <p className="mt-4 text-lg text-white/80">
                Talk to our team about deploying an MPC network for your
                organization. Custom thresholds, dedicated infrastructure, and
                white-glove onboarding.
              </p>
              <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
                <Button
                  size="xl"
                  className="bg-white text-violet-600 hover:bg-white/90"
                  asChild
                >
                  <Link href="/contact">
                    Request Access
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button
                  size="xl"
                  variant="outline"
                  className="border-white/30 bg-transparent text-white hover:bg-white/10"
                  asChild
                >
                  <Link href="/docs/mpc">Read the Docs</Link>
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

function ChainCard({
  protocol,
  chains,
}: {
  protocol: string
  chains: string[]
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <Badge variant="secondary" className="w-fit">
          {protocol}
        </Badge>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {chains.map((chain) => (
            <li
              key={chain}
              className="flex items-center text-sm text-muted-foreground"
            >
              <div className="mr-2 h-1.5 w-1.5 rounded-full bg-primary" />
              {chain}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

function UseCaseCard({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
      </CardContent>
    </Card>
  )
}
