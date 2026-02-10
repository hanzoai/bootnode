"use client"

import Link from "next/link"
import { Separator } from "@/components/ui/separator"
import { BrandLogo, useBrand } from "@/components/brand-logo"
import { ExternalLink } from "lucide-react"

const footerLinks = {
  products: [
    { name: "Node (RPC)", href: "/products/node" },
    { name: "Token API", href: "/products/data" },
    { name: "NFT API", href: "/products/data" },
    { name: "Smart Wallets", href: "/products/wallets" },
    { name: "Webhooks", href: "/products/webhooks" },
    { name: "Rollups", href: "/products/rollups" },
  ],
  chains: [
    { name: "Ethereum", href: "/chains/ethereum" },
    { name: "Solana", href: "/chains/solana" },
    { name: "Base", href: "/chains/base" },
    { name: "Arbitrum", href: "/chains/arbitrum" },
    { name: "Polygon", href: "/chains/polygon" },
    { name: "View All", href: "/chains" },
  ],
  developers: [
    { name: "Documentation", href: "/docs" },
    { name: "API Reference", href: "/docs/api" },
    { name: "Quickstart", href: "/docs/quickstart" },
    { name: "SDKs", href: "/docs/sdks" },
    { name: "Tutorials", href: "/docs/tutorials" },
    { name: "llms.txt", href: "/llms.txt" },
  ],
}

export function Footer() {
  const brand = useBrand()

  return (
    <footer className="border-t bg-muted/30">
      <div className="container py-12 md:py-16">
        <div className="grid gap-8 sm:grid-cols-2 md:grid-cols-5">
          {/* Brand */}
          <div className="md:col-span-1">
            <Link href="/">
              <BrandLogo />
            </Link>
            <p className="mt-4 text-sm text-muted-foreground">
              {brand.tagline}
            </p>
          </div>

          {/* Products */}
          <div>
            <h3 className="font-semibold">Products</h3>
            <ul className="mt-4 space-y-2">
              {footerLinks.products.map((link) => (
                <li key={link.name}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Chains */}
          <div>
            <h3 className="font-semibold">Chains</h3>
            <ul className="mt-4 space-y-2">
              {footerLinks.chains.map((link) => (
                <li key={link.name}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Developers */}
          <div>
            <h3 className="font-semibold">Developers</h3>
            <ul className="mt-4 space-y-2">
              {footerLinks.developers.map((link) => (
                <li key={link.name}>
                  <Link
                    href={link.href}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    {link.name}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Ecosystem (brand-specific) */}
          <div>
            <h3 className="font-semibold">Ecosystem</h3>
            <ul className="mt-4 space-y-2">
              {brand.footerLinks.map((link) => (
                <li key={link.name}>
                  <a
                    href={link.href}
                    target={link.external ? "_blank" : undefined}
                    rel={link.external ? "noopener noreferrer" : undefined}
                    className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
                  >
                    {link.name}
                    {link.external && <ExternalLink className="h-3 w-3" />}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <Separator className="my-8" />

        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} {brand.name}. All rights reserved.
          </p>
          <div className="flex gap-4">
            <Link
              href="/privacy"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Privacy
            </Link>
            <Link
              href="/terms"
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Terms
            </Link>
          </div>
        </div>
      </div>
    </footer>
  )
}
