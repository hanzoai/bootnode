import type { Metadata } from "next"
import { GeistSans } from "geist/font/sans"
import { GeistMono } from "geist/font/mono"
import { ThemeProvider } from "@/components/theme-provider"
import { AuthProvider } from "@/lib/auth"
import { Providers } from "@/app/providers"
import { Toaster } from "@/components/ui/sonner"
import "@/app/globals.css"

// Brand-aware metadata - uses NEXT_PUBLIC_BRAND env var
const brandName = process.env.NEXT_PUBLIC_BRAND === "bootnode" ? "Bootnode" :
                  process.env.NEXT_PUBLIC_BRAND === "hanzo" ? "Hanzo Web3" :
                  process.env.NEXT_PUBLIC_BRAND === "lux" ? "Lux Network" :
                  process.env.NEXT_PUBLIC_BRAND === "zoo" ? "Zoo Labs" : "Bootnode"

const brandTagline = process.env.NEXT_PUBLIC_BRAND === "bootnode" ? "Blockchain Infrastructure" :
                     process.env.NEXT_PUBLIC_BRAND === "hanzo" ? "Web3 Infrastructure" :
                     process.env.NEXT_PUBLIC_BRAND === "lux" ? "Next-Gen Blockchain Infrastructure" :
                     process.env.NEXT_PUBLIC_BRAND === "zoo" ? "Decentralized AI Infrastructure" : "Blockchain Infrastructure"

const brandDomain = process.env.NEXT_PUBLIC_BRAND === "bootnode" ? "bootno.de" :
                    process.env.NEXT_PUBLIC_BRAND === "hanzo" ? "web3.hanzo.ai" :
                    process.env.NEXT_PUBLIC_BRAND === "lux" ? "web3.lux.network" :
                    process.env.NEXT_PUBLIC_BRAND === "zoo" ? "web3.zoo.ngo" : "bootno.de"

const brandIcon = process.env.NEXT_PUBLIC_BRAND === "bootnode" ? "/logo/bootnode-icon.svg" :
                  process.env.NEXT_PUBLIC_BRAND === "hanzo" ? "/logo/hanzo-icon.svg" :
                  process.env.NEXT_PUBLIC_BRAND === "lux" ? "/logo/lux-icon.svg" :
                  process.env.NEXT_PUBLIC_BRAND === "zoo" ? "/logo/zoo-icon.svg" : "/logo/bootnode-icon.svg"

export const metadata: Metadata = {
  title: {
    default: `${brandName} - ${brandTagline}`,
    template: `%s | ${brandName}`,
  },
  description:
    `Enterprise blockchain infrastructure powered by ${brandName}. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, Webhooks, and more.`,
  keywords: [
    "blockchain",
    "RPC",
    "API",
    "Web3",
    "Ethereum",
    "Solana",
    "NFT",
    "DeFi",
    "smart contracts",
    "developer tools",
    brandName.toLowerCase(),
  ],
  authors: [{ name: brandName }],
  openGraph: {
    type: "website",
    locale: "en_US",
    url: `https://${brandDomain}`,
    siteName: brandName,
    title: `${brandName} - ${brandTagline}`,
    description:
      `Enterprise blockchain infrastructure powered by ${brandName}. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, and more.`,
  },
  twitter: {
    card: "summary_large_image",
    title: `${brandName} - ${brandTagline}`,
    description:
      `Enterprise blockchain infrastructure powered by ${brandName}. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, and more.`,
  },
  icons: {
    icon: brandIcon,
    apple: brandIcon,
    shortcut: brandIcon,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
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
              defaultTheme="light"
              enableSystem
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
