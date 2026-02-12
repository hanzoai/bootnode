// White-label branding configuration
// Configure via environment variables for different deployments

export type BrandConfig = {
  name: string
  tagline: string
  description: string
  logo: string
  logoIcon: string
  logoWhite: string
  favicon: string
  domain: string
  apiUrl: string
  wsUrl: string
  statusUrl: string
  defaultTheme: "light" | "dark"
  colors: {
    primary: string
    primaryForeground: string
    accent: string           // Hero gradient start
    accentEnd: string        // Hero gradient end
  }
  social: {
    twitter?: string
    github?: string
    discord?: string
  }
  iam: {
    url: string
    clientId: string
    domain: string // e.g., hanzo.id, zoo.id
  }
  footerLinks: {
    name: string
    href: string
    external?: boolean
  }[]
}

// Brand presets
const brands: Record<string, BrandConfig> = {
  bootnode: {
    name: "Bootnode",
    tagline: "Blockchain Infrastructure for Developers",
    description: "The complete blockchain development platform. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, Webhooks, and more.",
    logo: "/logo/bootnode-logo.svg",
    logoIcon: "/logo/bootnode-icon.svg",
    logoWhite: "/logo/bootnode-logo-white.svg",
    favicon: "/logo/bootnode-icon.svg",
    domain: "bootno.de",
    apiUrl: "https://api.bootno.de",
    wsUrl: "wss://ws.bootno.de",
    statusUrl: "https://status.bootno.de",
    defaultTheme: "light",
    colors: {
      primary: "#000000",
      primaryForeground: "#ffffff",
      accent: "#3b82f6",     // blue-500
      accentEnd: "#06b6d4",  // cyan-500
    },
    social: {
      twitter: "https://twitter.com/bootnode",
      github: "https://github.com/bootnode",
    },
    iam: {
      url: "https://hanzo.id",
      clientId: "bootnode-platform",
      domain: "hanzo.id",
    },
    footerLinks: [
      { name: "GitHub", href: "https://github.com/bootnode", external: true },
      { name: "Twitter", href: "https://twitter.com/bootnode", external: true },
    ],
  },
  hanzo: {
    name: "Hanzo Web3",
    tagline: "Enterprise Blockchain Infrastructure",
    description: "Enterprise blockchain infrastructure powered by Hanzo AI. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, and more.",
    logo: "/logo/hanzo-logo.svg",
    logoIcon: "/logo/hanzo-icon.svg",
    logoWhite: "/logo/hanzo-logo-white.svg",
    favicon: "/logo/hanzo-icon.svg",
    domain: "web3.hanzo.ai",
    apiUrl: "https://api.web3.hanzo.ai",
    wsUrl: "wss://ws.web3.hanzo.ai",
    statusUrl: "https://status.hanzo.ai",
    defaultTheme: "dark",
    colors: {
      primary: "#fd4444",
      primaryForeground: "#ffffff",
      accent: "#fd4444",     // hanzo red
      accentEnd: "#ff6b6b",  // lighter red
    },
    social: {
      twitter: "https://twitter.com/hanaboratory",
      github: "https://github.com/hanzoai",
      discord: "https://discord.gg/hanzo",
    },
    iam: {
      url: "https://hanzo.id",
      clientId: "hanzo-web3",
      domain: "hanzo.id",
    },
    footerLinks: [
      { name: "Hanzo AI", href: "https://hanzo.ai", external: true },
      { name: "Hanzo Cloud", href: "https://cloud.hanzo.ai", external: true },
      { name: "Hanzo Chat", href: "https://chat.hanzo.ai", external: true },
      { name: "Hanzo Network", href: "https://hanzo.network", external: true },
      { name: "GitHub", href: "https://github.com/hanzoai", external: true },
    ],
  },
  lux: {
    name: "Lux Cloud",
    tagline: "Next-Gen Blockchain Infrastructure",
    description: "High-performance blockchain infrastructure for the Lux Network ecosystem.",
    logo: "/logo/lux-wordmark-dark.svg",
    logoIcon: "/logo/lux-icon.svg",
    logoWhite: "/logo/lux-wordmark-white.svg",
    favicon: "/logo/lux-icon.svg",
    domain: "cloud.lux.network",
    apiUrl: "https://api.cloud.lux.network",
    wsUrl: "wss://ws.cloud.lux.network",
    statusUrl: "https://status.lux.network",
    defaultTheme: "dark",
    colors: {
      primary: "#ffffff",
      primaryForeground: "#000000",
      accent: "#a8a8a8",     // monochrome silver
      accentEnd: "#ffffff",  // white
    },
    social: {
      twitter: "https://twitter.com/luxdefi",
      github: "https://github.com/luxfi",
    },
    iam: {
      url: "https://iam.lux.network",
      clientId: "lux-web3",
      domain: "lux.id",
    },
    footerLinks: [
      { name: "Lux Network", href: "https://lux.network", external: true },
      { name: "Lux Explorer", href: "https://explore.lux.network", external: true },
      { name: "Lux Bridge", href: "https://bridge.lux.network", external: true },
      { name: "Lux Wallet", href: "https://wallet.lux.network", external: true },
      { name: "Lux Exchange", href: "https://exchange.lux.network", external: true },
      { name: "GitHub", href: "https://github.com/luxfi", external: true },
    ],
  },
  pars: {
    name: "Pars Cloud",
    tagline: "Sovereign L1 Infrastructure",
    description: "Sovereign L1 blockchain infrastructure for the Pars Network. Post-quantum secure, SessionVM messaging, native DEX, and more.",
    logo: "/logo/pars-logo.svg",
    logoIcon: "/logo/pars-icon.svg",
    logoWhite: "/logo/pars-logo-white.svg",
    favicon: "/logo/pars-icon.svg",
    domain: "cloud.pars.network",
    apiUrl: "https://api.cloud.pars.network",
    wsUrl: "wss://ws.cloud.pars.network",
    statusUrl: "https://status.pars.network",
    defaultTheme: "dark",
    colors: {
      primary: "#00abff",
      primaryForeground: "#ffffff",
      accent: "#00abff",     // persian blue
      accentEnd: "#F59E0B",  // gold accent
    },
    social: {
      twitter: "https://twitter.com/parsnetwork",
      github: "https://github.com/pars-network",
    },
    iam: {
      url: "https://iam.lux.network",
      clientId: "lux-web3",
      domain: "pars.id",
    },
    footerLinks: [
      { name: "Pars Network", href: "https://pars.network", external: true },
      { name: "Pars Explorer", href: "https://explore.pars.network", external: true },
      { name: "Pars Wallet", href: "https://wallet.pars.network", external: true },
      { name: "SessionVM", href: "https://session.pars.network", external: true },
      { name: "GitHub", href: "https://github.com/pars-network", external: true },
    ],
  },
  zoo: {
    name: "Zoo Labs",
    tagline: "Decentralized AI Infrastructure",
    description: "Blockchain infrastructure for decentralized AI and science research.",
    logo: "/logo/zoo-logo.svg",
    logoIcon: "/logo/zoo-icon.svg",
    logoWhite: "/logo/zoo-logo-white.svg",
    favicon: "/logo/zoo-icon.svg",
    domain: "web3.zoo.ngo",
    apiUrl: "https://api.web3.zoo.ngo",
    wsUrl: "wss://ws.web3.zoo.ngo",
    statusUrl: "https://status.zoo.ngo",
    defaultTheme: "dark",
    colors: {
      primary: "#00cc66",
      primaryForeground: "#ffffff",
      accent: "#00cc66",     // emerald green
      accentEnd: "#10b981",  // lighter green
    },
    social: {
      twitter: "https://twitter.com/zoolabs",
      github: "https://github.com/zoolabs",
    },
    iam: {
      url: "https://iam.lux.network",
      clientId: "lux-web3",
      domain: "zoo.id",
    },
    footerLinks: [
      { name: "Zoo Labs", href: "https://zoo.ngo", external: true },
      { name: "Zoo AI Chat", href: "https://ai.zoo.ngo", external: true },
      { name: "Zoo Network", href: "https://zoo.network", external: true },
      { name: "Zen LM", href: "https://zenlm.ai", external: true },
      { name: "GitHub", href: "https://github.com/zooai", external: true },
    ],
  },
}

// Get brand from domain auto-detection or environment fallback
function getBrandKey(): string {
  // Client-side: detect from domain (highest priority)
  if (typeof window !== "undefined") {
    const hostname = window.location.hostname
    if (hostname.includes("lux.cloud") || hostname.includes("lux.network")) return "lux"
    if (hostname.includes("pars.network") || hostname.includes("pars.id")) return "pars"
    if (hostname.includes("zoo.ngo") || hostname.includes("zoo.id")) return "zoo"
    if (hostname.includes("hanzo.ai")) return "hanzo"
    if (hostname.includes("bootno.de") || hostname.includes("bootnode.io")) return "bootnode"
  }

  // Server-side: BRAND env var (runtime, not baked by Next.js unlike NEXT_PUBLIC_*)
  const runtimeBrand = process.env.BRAND?.toLowerCase()
  if (runtimeBrand && brands[runtimeBrand]) {
    return runtimeBrand
  }

  // Fall back to build-time NEXT_PUBLIC_BRAND
  const envBrand = process.env.NEXT_PUBLIC_BRAND?.toLowerCase()
  if (envBrand && brands[envBrand]) {
    return envBrand
  }

  return "bootnode"
}

// Export the active brand configuration
export function getBrand(): BrandConfig {
  return brands[getBrandKey()]
}

// Export brand key for conditional rendering
export function getBrandKey_(): string {
  return getBrandKey()
}

// Check if using Hanzo branding
export function isHanzoBrand(): boolean {
  return getBrandKey() === "hanzo"
}

// Get all available brands (for admin/testing)
export function getAllBrands(): Record<string, BrandConfig> {
  return brands
}

// Default export for convenience
export const brand = getBrand()
