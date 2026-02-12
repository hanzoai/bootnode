// Brand Configuration - White-label Ready
// This file is for standalone brand package exports
// For runtime brand detection, see web/lib/brand.ts

export type BrandOrg = "hanzo" | "lux" | "zoo" | "pars"

export interface BrandOrgConfig {
  name: string
  domain: string
  color: string
  iam: string
}

export interface BrandConfig {
  name: string
  tagline: string
  description: string

  // Colors aligned with logo
  colors: {
    primary: string
    secondary: string
    accent: string
    surface: string
    text: string
    textMuted: string
  }

  // Typography
  typography: {
    fontFamily: string
    monoFamily: string
  }

  // Logo variants
  logo: {
    main: string
    white: string
    mono: string
    icon: string
  }

  // URLs & Links
  urls: {
    app: string
    api: string
    docs: string
    status: string
    github: string
  }

  // Partner organizations (for multi-tenant IAM)
  orgs: Record<BrandOrg, BrandOrgConfig>

  // Supported networks
  networks: string[]

  // Platform features
  features: string[]

  // Social media
  social: {
    twitter?: string
    discord?: string
    telegram?: string
  }
}

// Hanzo Web3 Brand (default)
export const hanzoWeb3: BrandConfig = {
  name: "Hanzo Web3",
  tagline: "Enterprise Blockchain Infrastructure",
  description: "Enterprise blockchain infrastructure powered by Hanzo AI. Multi-chain RPC, Token APIs, NFT APIs, Smart Wallets, and more.",

  colors: {
    primary: "#000000",
    secondary: "#ffffff",
    accent: "#0066ff",
    surface: "#f5f5f5",
    text: "#1a1a1a",
    textMuted: "#6b7280",
  },

  typography: {
    fontFamily: "Geist Sans, system-ui, sans-serif",
    monoFamily: "Geist Mono, Consolas, monospace",
  },

  logo: {
    main: "/logo/hanzo-logo.svg",
    white: "/logo/hanzo-logo-white.svg",
    mono: "/logo/hanzo-logo-mono.svg",
    icon: "/logo/hanzo-icon.svg",
  },

  urls: {
    app: "https://web3.hanzo.ai",
    api: "https://api.web3.hanzo.ai",
    docs: "https://docs.web3.hanzo.ai",
    status: "https://status.hanzo.ai",
    github: "https://github.com/hanzoai",
  },

  orgs: {
    hanzo: {
      name: "Hanzo",
      domain: "hanzo.id",
      color: "#000000",
      iam: "https://hanzo.id",
    },
    zoo: {
      name: "Zoo Labs",
      domain: "zoo.id",
      color: "#00cc66",
      iam: "https://zoo.id",
    },
    lux: {
      name: "Lux Network",
      domain: "lux.id",
      color: "#8b5cf6",
      iam: "https://iam.lux.network",
    },
    pars: {
      name: "Pars",
      domain: "pars.id",
      color: "#f59e0b",
      iam: "https://pars.id",
    },
  },

  networks: [
    "Ethereum", "Polygon", "Arbitrum", "Optimism",
    "Base", "Avalanche", "BNB Chain", "Lux",
    "Bitcoin", "Solana"
  ],

  features: [
    "Multi-chain RPC Proxy",
    "Token & NFT APIs",
    "Smart Wallets (ERC-4337)",
    "Gas Management",
    "Webhook System",
    "Real-time Analytics",
    "Developer Dashboard",
    "Admin Management",
  ],

  social: {
    twitter: "@hanaboratory",
    discord: "https://discord.gg/hanzo",
    telegram: "https://t.me/hanzoai",
  },
}

// Lux Cloud Brand (white-label for Lux Network)
export const luxCloud: BrandConfig = {
  name: "Lux Cloud",
  tagline: "Next-Gen Blockchain Infrastructure",
  description: "High-performance blockchain infrastructure for the Lux Network ecosystem.",

  colors: {
    primary: "#8b5cf6",
    secondary: "#ffffff",
    accent: "#a78bfa",
    surface: "#f5f3ff",
    text: "#1a1a1a",
    textMuted: "#6b7280",
  },

  typography: {
    fontFamily: "Geist Sans, system-ui, sans-serif",
    monoFamily: "Geist Mono, Consolas, monospace",
  },

  logo: {
    main: "/logo/lux-logo.svg",
    white: "/logo/lux-logo-white.svg",
    mono: "/logo/lux-logo-mono.svg",
    icon: "/logo/lux-icon.svg",
  },

  urls: {
    app: "https://lux.cloud",
    api: "https://api.lux.cloud",
    docs: "https://docs.lux.cloud",
    status: "https://status.lux.cloud",
    github: "https://github.com/luxfi",
  },

  orgs: {
    hanzo: {
      name: "Hanzo",
      domain: "hanzo.id",
      color: "#000000",
      iam: "https://hanzo.id",
    },
    zoo: {
      name: "Zoo Labs",
      domain: "zoo.id",
      color: "#00cc66",
      iam: "https://zoo.id",
    },
    lux: {
      name: "Lux Network",
      domain: "lux.id",
      color: "#8b5cf6",
      iam: "https://iam.lux.network",
    },
    pars: {
      name: "Pars",
      domain: "pars.id",
      color: "#f59e0b",
      iam: "https://pars.id",
    },
  },

  networks: [
    "Lux", "Ethereum", "Polygon", "Arbitrum",
    "Optimism", "Base", "Avalanche", "BNB Chain"
  ],

  features: [
    "Multi-chain RPC Proxy",
    "Token & NFT APIs",
    "Smart Wallets (ERC-4337)",
    "Gas Management",
    "Webhook System",
    "Real-time Analytics",
    "Developer Dashboard",
  ],

  social: {
    twitter: "@luxdefi",
    discord: "https://discord.gg/luxnetwork",
    telegram: "https://t.me/luxnetwork",
  },
}

// Default export - Hanzo Web3
export default hanzoWeb3
