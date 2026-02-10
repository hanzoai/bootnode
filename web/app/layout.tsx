import type { Metadata } from "next"
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
  zoo: { name: "Zoo Labs", tagline: "Decentralized AI Infrastructure", domain: "web3.zoo.ngo", icon: "/logo/zoo-icon.svg", defaultTheme: "dark" },
}

function getServerBrandKey() {
  return (process.env.BRAND || process.env.NEXT_PUBLIC_BRAND || "bootnode").toLowerCase()
}

function getServerBrand() {
  const key = getServerBrandKey()
  return brands[key] || brands.bootnode
}

// Force dynamic rendering so BRAND env var is read at runtime, not build time
export const dynamic = "force-dynamic"

export async function generateMetadata(): Promise<Metadata> {
  const b = getServerBrand()
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

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const b = getServerBrand()
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
