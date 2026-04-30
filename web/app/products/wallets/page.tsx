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
  Fingerprint,
  Key,
  Layers,
  Lock,
  Rocket,
  Shield,
  Sparkles,
  Users,
  Wallet,
  Zap,
} from "lucide-react"
import { getBrand } from "@/lib/brand"
import { getSdkPackage } from "@/lib/sdk-package"
import { docsConfig } from "@/lib/docs-config"

export default function WalletsProductPage() {
  const brand = getBrand()
  const { pkg: sdkPackage, client: sdkClient } = getSdkPackage()

  return (
    <div className="flex min-h-screen flex-col">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden border-b bg-gradient-to-b from-background to-muted/20">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#4f4f4f2e_1px,transparent_1px),linear-gradient(to_bottom,#4f4f4f2e_1px,transparent_1px)] bg-[size:14px_24px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
        <div className="container relative py-24 md:py-32 lg:py-40">
          <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
            <Badge variant="secondary" className="mb-4">
              <Wallet className="mr-1 h-3 w-3" />
              ERC-4337 Account Abstraction
            </Badge>
            <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              Wallets that{" "}
              <span className="bg-gradient-to-r from-emerald-500 to-teal-500 bg-clip-text text-transparent">
                just work
              </span>
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl">
              Create smart wallets for your users with email, social login, or
              passkeys. No seed phrases, no gas popups, no friction. Built on
              ERC-4337 for maximum security and flexibility.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <Button size="xl" asChild>
                <Link href="/dashboard">
                  Create Your First Wallet
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button size="xl" variant="outline" asChild>
                <Link href="/docs/wallets">Read the Docs</Link>
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Key Benefits */}
      <section className="border-b bg-muted/30 py-12">
        <div className="container">
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            <StatItem label="Wallets Created" value="2M+" />
            <StatItem label="Gas Sponsored" value="$4.2M" />
            <StatItem label="Avg. Onboarding" value="<3 sec" />
            <StatItem label="Chains Supported" value="30+" />
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="border-b py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              Everything you need to onboard the next billion
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Smart Wallets handle the complexity of account abstraction
              so your users never have to think about gas, keys, or
              transactions.
            </p>
          </div>
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <FeatureCard
              icon={<Fingerprint className="h-6 w-6" />}
              title="Social Login & Passkeys"
              description="Let users sign up with Google, Apple, email, or device passkeys. A smart wallet is created behind the scenes with no seed phrase to back up and no extension to install."
            />
            <FeatureCard
              icon={<Zap className="h-6 w-6" />}
              title="Gasless Transactions"
              description="Sponsor gas for your users so they never see a gas popup. Configure per-transaction rules: sponsor all, sponsor under a threshold, or require the user to pay above a limit."
            />
            <FeatureCard
              icon={<Rocket className="h-6 w-6" />}
              title="Counterfactual Creation"
              description="Wallets are assigned a deterministic address before any onchain deployment. Users can receive funds immediately. The contract is deployed on their first outgoing transaction."
            />
            <FeatureCard
              icon={<Key className="h-6 w-6" />}
              title="Session Keys"
              description="Issue scoped, time-limited signing keys so your app can submit transactions on behalf of the user without repeated approvals. Ideal for games, trading, and automation."
            />
            <FeatureCard
              icon={<Layers className="h-6 w-6" />}
              title="Batched Transactions"
              description="Bundle multiple operations into a single UserOperation. Approve and swap, mint and transfer, or any combination of calls executed atomically in one transaction."
            />
            <FeatureCard
              icon={<Users className="h-6 w-6" />}
              title="Multi-Owner / Multisig"
              description="Add multiple owners or signers to a single smart wallet. Configure M-of-N thresholds for high-value operations. Perfect for teams, DAOs, and shared treasuries."
            />
            <FeatureCard
              icon={<Shield className="h-6 w-6" />}
              title="Recovery & Guardians"
              description="Set trusted guardians who can help recover access if the primary key is lost. Time-locked recovery prevents unauthorized takeover while keeping accounts recoverable."
            />
            <FeatureCard
              icon={<Lock className="h-6 w-6" />}
              title="Programmable Permissions"
              description="Define spending limits, allowed contracts, and permitted function selectors per signer. Fine-grained access control gives you the security model your app needs."
            />
            <FeatureCard
              icon={<Sparkles className="h-6 w-6" />}
              title="Cross-Chain Deployment"
              description="Deploy the same wallet address across 30+ EVM chains. Users get a unified identity that works on Ethereum, Base, Arbitrum, Optimism, Polygon, and more."
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
                Five lines to a smart wallet
              </h2>
              <p className="mt-4 text-lg text-muted-foreground">
                Create a wallet, sponsor gas, and submit a transaction. The
                {brand.name} SDK handles UserOperation bundling, paymaster
                signatures, and EntryPoint interaction under the hood.
              </p>
              <ul className="mt-8 space-y-3">
                {[
                  "TypeScript, Python, and REST API support",
                  "Compatible with viem, ethers.js, and wagmi",
                  "ERC-4337 v0.7 compliant EntryPoint",
                  "Bundler included at no extra cost",
                  "Paymaster with flexible sponsorship policies",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col gap-4">
              <CodeBlock
                title="TypeScript"
                code={`import { ${sdkClient} } from "${sdkPackage}";

const client = new ${sdkClient}({
  apiKey: "${docsConfig.apiKeyPrefix}YOUR_API_KEY",
  chain: "base",
});

// Create a smart wallet for a user
const wallet = await client.wallets.create({
  owner: "0xUserEOA...",
  salt: 0,
});

console.log(wallet.address);
// => "0x7F3a...deterministic address"

// Send a gasless transaction
const txHash = await client.wallets.sendTransaction({
  wallet: wallet.address,
  to: "0xRecipient...",
  data: "0x",
  value: "1000000000000000", // 0.001 ETH
  sponsor: true, // ${brand.name} pays the gas
});

console.log(txHash);
// => "0x8b3e1f..."`}
              />
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-b py-24">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
              How it works under the hood
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              {brand.name} Smart Wallets are ERC-4337 smart contract accounts.
              Here is what happens when your user sends a transaction.
            </p>
          </div>
          <div className="mt-16 grid gap-6 md:grid-cols-4">
            <StepCard
              step="1"
              title="User Signs"
              description="The user signs the intent with their key (passkey, social login, or EOA). No gas estimation or nonce management required on the client."
            />
            <StepCard
              step="2"
              title="Build UserOp"
              description={`The ${brand.name} SDK constructs a UserOperation with the call data, gas limits, and paymaster signature for gas sponsorship.`}
            />
            <StepCard
              step="3"
              title="Bundle & Submit"
              description={`The ${brand.name} bundler batches the UserOperation with others and submits it to the EntryPoint contract on chain.`}
            />
            <StepCard
              step="4"
              title="Confirm"
              description="The transaction is mined and your app receives a confirmation via webhook or polling. The user sees success in under 5 seconds."
            />
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
                Onboard users without the friction
              </h2>
              <p className="mt-4 text-lg text-white/80">
                Create your first smart wallet in minutes. Free tier includes
                1,000 sponsored transactions per month and unlimited wallet
                creation.
              </p>
              <div className="mt-10 flex flex-col justify-center gap-4 sm:flex-row">
                <Button
                  size="xl"
                  className="bg-white text-emerald-600 hover:bg-white/90"
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
                  <Link href="/contact">Talk to Sales</Link>
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

function CodeBlock({ title, code }: { title: string; code: string }) {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <div className="flex items-center border-b px-4 py-2">
        <span className="text-xs font-medium text-muted-foreground">
          {title}
        </span>
      </div>
      <pre className="overflow-x-auto p-4 text-sm leading-relaxed">
        <code>{code}</code>
      </pre>
    </div>
  )
}
