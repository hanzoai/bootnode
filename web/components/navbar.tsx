"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  NavigationMenu,
  NavigationMenuContent,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
  NavigationMenuTrigger,
} from "@/components/ui/navigation-menu"
import {
  Database,
  Globe,
  Layers,
  Menu,
  Wallet,
  X,
} from "lucide-react"
import { BrandLogo } from "@/components/brand-logo"
import { CommandMenu } from "@/components/command-menu"

const products = [
  {
    title: "Node",
    href: "/products/node",
    description: "Multi-chain RPC with 99.999% uptime",
    icon: Globe,
  },
  {
    title: "Data",
    href: "/products/data",
    description: "Token, NFT, and Transfer APIs",
    icon: Database,
  },
  {
    title: "Wallets",
    href: "/products/wallets",
    description: "Smart wallets with account abstraction",
    icon: Wallet,
  },
  {
    title: "Rollups",
    href: "/products/rollups",
    description: "Launch custom rollups at scale",
    icon: Layers,
  },
]

const chains = [
  { name: "Ethereum", href: "/chains/ethereum" },
  { name: "Solana", href: "/chains/solana" },
  { name: "Base", href: "/chains/base" },
  { name: "Arbitrum", href: "/chains/arbitrum" },
  { name: "Polygon", href: "/chains/polygon" },
  { name: "View All 100+", href: "/chains" },
]

export function Navbar() {
  const [isOpen, setIsOpen] = React.useState(false)
  const pathname = usePathname()

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center">
        {/* Logo */}
        <Link href="/" className="mr-6">
          <BrandLogo />
        </Link>

        {/* Desktop Navigation */}
        <NavigationMenu className="hidden lg:flex">
          <NavigationMenuList>
            <NavigationMenuItem>
              <NavigationMenuTrigger>Products</NavigationMenuTrigger>
              <NavigationMenuContent>
                <ul className="grid w-[400px] gap-3 p-4 md:w-[500px] md:grid-cols-2">
                  {products.map((product) => (
                    <li key={product.title}>
                      <NavigationMenuLink asChild>
                        <Link
                          href={product.href}
                          className="flex select-none items-start gap-4 rounded-md p-3 leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                        >
                          <product.icon className="mt-1 h-5 w-5 text-muted-foreground" />
                          <div>
                            <div className="text-sm font-medium leading-none">
                              {product.title}
                            </div>
                            <p className="mt-1 line-clamp-2 text-sm leading-snug text-muted-foreground">
                              {product.description}
                            </p>
                          </div>
                        </Link>
                      </NavigationMenuLink>
                    </li>
                  ))}
                </ul>
              </NavigationMenuContent>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuTrigger>Chains</NavigationMenuTrigger>
              <NavigationMenuContent>
                <ul className="grid w-[200px] gap-1 p-2">
                  {chains.map((chain) => (
                    <li key={chain.name}>
                      <NavigationMenuLink asChild>
                        <Link
                          href={chain.href}
                          className={cn(
                            "block select-none rounded-md px-3 py-2 text-sm leading-none no-underline outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground",
                            chain.name === "View All 100+" && "font-medium text-primary"
                          )}
                        >
                          {chain.name}
                        </Link>
                      </NavigationMenuLink>
                    </li>
                  ))}
                </ul>
              </NavigationMenuContent>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink asChild>
                <Link
                  href="/docs"
                  className="group inline-flex h-9 w-max items-center justify-center rounded-md bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground focus:outline-none disabled:pointer-events-none disabled:opacity-50"
                >
                  Docs
                </Link>
              </NavigationMenuLink>
            </NavigationMenuItem>
            <NavigationMenuItem>
              <NavigationMenuLink asChild>
                <Link
                  href="/pricing"
                  className="group inline-flex h-9 w-max items-center justify-center rounded-md bg-background px-4 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground focus:outline-none disabled:pointer-events-none disabled:opacity-50"
                >
                  Pricing
                </Link>
              </NavigationMenuLink>
            </NavigationMenuItem>
          </NavigationMenuList>
        </NavigationMenu>

        {/* Search + Actions */}
        <div className="ml-auto flex items-center gap-4">
          <CommandMenu />
          <Button variant="ghost" size="sm" asChild className="hidden sm:flex">
            <Link href="/login">Sign In</Link>
          </Button>
          <Button size="sm" asChild>
            <Link href="/dashboard">Go to Dashboard</Link>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setIsOpen(!isOpen)}
          >
            {isOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isOpen && (
        <div className="container border-t pb-4 pt-4 lg:hidden">
          <nav className="flex flex-col gap-4">
            <Link
              href="/products"
              className="text-sm font-medium"
              onClick={() => setIsOpen(false)}
            >
              Products
            </Link>
            <Link
              href="/chains"
              className="text-sm font-medium"
              onClick={() => setIsOpen(false)}
            >
              Chains
            </Link>
            <Link
              href="/docs"
              className="text-sm font-medium"
              onClick={() => setIsOpen(false)}
            >
              Docs
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium"
              onClick={() => setIsOpen(false)}
            >
              Pricing
            </Link>
          </nav>
        </div>
      )}
    </header>
  )
}
