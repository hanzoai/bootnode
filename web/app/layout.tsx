import type { Metadata } from "next"
import { headers } from "next/headers"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import { ThemeProvider } from "@/components/theme-provider"
import { AuthProvider } from "@/lib/auth"
import { Providers } from "@/app/providers"
import { Toaster } from "@/components/ui/sonner"
import "@/app/globals.css"

// Runtime brand detection for SSR metadata (reads BRAND env var, not baked NEXT_PUBLIC_*)
const brands: Record<string, { name: string; tagline: string; domain: string; icon: string; defaultTheme: string }> = {
  bootnode: { name: "Bootnode", tagline: "Blockchain Infrastructure", domain: "bootno.de", icon: "/logo/bootnode-icon.svg", defaultTheme: "light" },
  hanzo: { name: "Hanzo Web3", tagline: "Web3 Infrastructure", domain: "web3.hanzo.ai", icon: "/logo/hanzo-icon.svg", defaultTheme: "dark" },
  lux: { name: "Lux Cloud", tagline: "Next-Gen Blockchain Infrastructure", domain: "cloud.lux.network", icon: "/logo/lux-icon.svg", defaultTheme: "dark" },
  pars: { name: "Pars Cloud", tagline: "Sovereign L1 Infrastructure", domain: "cloud.pars.network", icon: "/logo/pars-icon.svg", defaultTheme: "dark" },
  zoo: { name: "Zoo Labs", tagline: "Decentralized AI Infrastructure", domain: "web3.zoo.ngo", icon: "/logo/zoo-icon.svg", defaultTheme: "dark" },
}

// Detect brand from Host header. Returns null when no host match (caller
// then falls back to BRAND/NEXT_PUBLIC_BRAND env vars).
// IMPORTANT: Do NOT bake the env-var fallback in here — `dynamic = "force-dynamic"`
// makes layout requests runtime, so callers should read process.env directly
// at request time and avoid relying on this helper for the env-var path.
function getServerBrandKeyFromHost(host: string | null): string | null {
  if (host) {
    if (host.includes("lux.network") || host.includes("lux.cloud")) return "lux"
    if (host.includes("pars.network") || host.includes("pars.id")) return "pars"
    if (host.includes("zoo.ngo") || host.includes("zoo.network") || host.includes("zoo.cloud")) return "zoo"
    if (host.includes("hanzo.ai")) return "hanzo"
    if (host.includes("bootno.de") || host.includes("bootnode.io")) return "bootnode"
  }
  return null
}

async function getServerBrand() {
  // Prefer Host header; fall back to BRAND or NEXT_PUBLIC_BRAND env vars.
  // dynamic = "force-dynamic" plus headers() forces request-time evaluation,
  // so process.env reads pick up runtime values, not the Dockerfile default.
  const hdrs = await headers()
  const host = hdrs.get("host")
  const key = getServerBrandKeyFromHost(host) ||
    (process.env.BRAND || process.env.NEXT_PUBLIC_BRAND || "bootnode").toLowerCase()
  return brands[key] || brands.bootnode
}

// Force dynamic rendering so BRAND env var is read at runtime, not build time
export const dynamic = "force-dynamic"

export async function generateMetadata(): Promise<Metadata> {
  // Calling headers() forces Next.js to evaluate this at request time, never at build time.
  const hdrs = await headers()
  const host = hdrs.get("host")
  const key = getServerBrandKeyFromHost(host) ||
    (process.env.BRAND || process.env.NEXT_PUBLIC_BRAND || "bootnode").toLowerCase()
  const b = brands[key] || brands.bootnode
  return {
    title: {
      default: `${b.name} - ${b.tagline}`,
      template: `%s | ${b.name}`,
    },
    description: `Enterprise blockchain infrastructure powered by ${b.name}. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, Webhooks, and more.`,
    keywords: ["blockchain", "RPC", "API", "Web3", "Ethereum", "Solana", "NFT", "DeFi", "smart contracts", "developer tools", b.name.toLowerCase()],
    authors: [{ name: b.name }],
    openGraph: {
      type: "website",
      locale: "en_US",
      url: `https://${b.domain}`,
      siteName: b.name,
      title: `${b.name} - ${b.tagline}`,
      description: `Enterprise blockchain infrastructure powered by ${b.name}. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, and more.`,
    },
    twitter: {
      card: "summary_large_image",
      title: `${b.name} - ${b.tagline}`,
      description: `Enterprise blockchain infrastructure powered by ${b.name}. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, and more.`,
    },
    icons: {
      icon: b.icon,
      apple: b.icon,
      shortcut: b.icon,
    },
  }
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const b = await getServerBrand()
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body className="min-h-screen bg-background font-sans antialiased">
        <Providers>
          <AuthProvider>
            <ThemeProvider
              attribute="class"
              defaultTheme={b.defaultTheme}
              enableSystem={false}
              disableTransitionOnChange
            >
              {children}
              <Toaster />
            </ThemeProvider>
          </AuthProvider>
        </Providers>
      </body>
    </html>
  )
}
