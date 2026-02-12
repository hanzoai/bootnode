"use client"

// Unified Dashboard Navigation - All features merged
// Complete platform navigation with organizations, teams, and all features

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuLabel, 
  DropdownMenuSeparator, 
  DropdownMenuTrigger 
} from "@/components/ui/dropdown-menu"
import { useAuth, OrgBadge } from "@/lib/auth"
import { getBrand } from "@/lib/brand"
import { 
  Activity, 
  Server, 
  Network, 
  Database, 
  Users, 
  Settings, 
  CreditCard, 
  Key, 
  Webhook, 
  BarChart3, 
  Coins, 
  Shield, 
  Building, 
  UserPlus,
  ChevronDown,
  Menu,
  X,
  Home,
  Zap,
  Globe,
  Code,
  FileText,
  Bell
} from "lucide-react"

interface NavigationItem {
  name: string
  href: string
  icon: any
  current?: boolean
  badge?: string
  description?: string
  children?: NavigationItem[]
}

export function UnifiedNavigation() {
  const { user, logout, isAdmin } = useAuth()
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [selectedOrg, setSelectedOrg] = useState<string>(user?.org || "hanzo")

  // Unified navigation structure
  const navigation: NavigationItem[] = [
    {
      name: "Overview",
      href: "/dashboard",
      icon: Home,
      description: "Platform overview and quick actions"
    },
    {
      name: "Infrastructure",
      href: "/dashboard/infrastructure",
      icon: Server,
      description: "Manage nodes, networks, and infrastructure",
      children: [
        { name: "Nodes", href: "/dashboard/infrastructure/nodes", icon: Server },
        { name: "Networks", href: "/dashboard/infrastructure/networks", icon: Network },
        { name: "Monitoring", href: "/dashboard/infrastructure/monitoring", icon: Activity },
      ]
    },
    {
      name: "API & Development", 
      href: "/dashboard/api",
      icon: Code,
      description: "API keys, webhooks, and developer tools",
      children: [
        { name: "API Keys", href: "/dashboard/api/keys", icon: Key },
        { name: "Webhooks", href: "/dashboard/api/webhooks", icon: Webhook },
        { name: "Documentation", href: "/dashboard/api/docs", icon: FileText },
        { name: "Playground", href: "/dashboard/api/playground", icon: Zap },
      ]
    },
    {
      name: "Analytics",
      href: "/dashboard/analytics", 
      icon: BarChart3,
      description: "Usage metrics, performance, and insights",
      children: [
        { name: "Usage", href: "/dashboard/analytics/usage", icon: Activity },
        { name: "Performance", href: "/dashboard/analytics/performance", icon: Zap },
        { name: "Billing", href: "/dashboard/analytics/billing", icon: CreditCard },
      ]
    },
    {
      name: "Assets",
      href: "/dashboard/assets",
      icon: Coins, 
      description: "Token balances, NFTs, and portfolio",
      children: [
        { name: "Tokens", href: "/dashboard/assets/tokens", icon: Coins },
        { name: "NFTs", href: "/dashboard/assets/nfts", icon: Globe },
        { name: "Transfers", href: "/dashboard/assets/transfers", icon: Activity },
      ]
    },
    {
      name: "Organization",
      href: "/dashboard/organization",
      icon: Building,
      description: "Team, members, and organization settings", 
      children: [
        { name: "Team", href: "/dashboard/organization/team", icon: Users },
        { name: "Settings", href: "/dashboard/organization/settings", icon: Settings },
        { name: "Billing", href: "/dashboard/organization/billing", icon: CreditCard },
        { name: "Security", href: "/dashboard/organization/security", icon: Shield },
      ]
    }
  ]

  // Admin-only navigation
  const adminNavigation: NavigationItem[] = [
    {
      name: "Admin",
      href: "/admin", 
      icon: Shield,
      description: "Platform administration and management",
      children: [
        { name: "Overview", href: "/admin", icon: Activity },
        { name: "All Nodes", href: "/admin/nodes", icon: Server },
        { name: "All Networks", href: "/admin/networks", icon: Network },
        { name: "All Users", href: "/admin/users", icon: Users },
        { name: "System Health", href: "/admin/health", icon: Shield },
      ]
    }
  ]

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === href
    return pathname.startsWith(href)
  }

  const organizations = [
    { id: "hanzo", name: "Hanzo", domain: "hanzo.id", color: "#0066ff" },
    { id: "zoo", name: "Zoo Labs", domain: "zoo.id", color: "#00cc66" },
    { id: "lux", name: "Lux Network", domain: "lux.id", color: "#8b5cf6" },
    { id: "pars", name: "Pars", domain: "pars.id", color: "#f59e0b" },
  ]

  const currentOrg = organizations.find(org => org.id === selectedOrg) || organizations[0]

  return (
    <>
      {/* Top Navigation Bar */}
      <nav className="bg-background border-b border-border fixed w-full top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              {/* Logo */}
              <Link href="/dashboard" className="flex items-center space-x-3">
                <img src={getBrand().logoIcon} alt={getBrand().name} className="w-8 h-8" />
                <span className="text-xl font-bold">{getBrand().name}</span>
              </Link>

              {/* Organization Selector */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="ml-6 flex items-center space-x-2">
                    <div 
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: currentOrg.color }}
                    />
                    <span>{currentOrg.name}</span>
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuLabel>Switch Organization</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  {organizations.map((org) => (
                    <DropdownMenuItem 
                      key={org.id}
                      onClick={() => setSelectedOrg(org.id)}
                      className="flex items-center space-x-2"
                    >
                      <div 
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: org.color }}
                      />
                      <div>
                        <div className="font-medium">{org.name}</div>
                        <div className="text-xs text-muted-foreground">{org.domain}</div>
                      </div>
                      {org.id === selectedOrg && <Badge variant="secondary">Current</Badge>}
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <UserPlus className="mr-2 h-4 w-4" />
                    Create Organization
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Right side */}
            <div className="flex items-center space-x-4">
              {/* Notifications */}
              <Button variant="ghost" size="sm">
                <Bell className="h-5 w-5" />
              </Button>

              {/* User Menu */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center space-x-2">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user?.avatar} />
                      <AvatarFallback>{user?.name?.charAt(0)}</AvatarFallback>
                    </Avatar>
                    <span className="hidden md:block">{user?.name}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>
                    <div>{user?.name}</div>
                    <div className="text-xs text-muted-foreground">{user?.email}</div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem>
                    <Settings className="mr-2 h-4 w-4" />
                    Profile Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Key className="mr-2 h-4 w-4" />
                    API Keys
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={logout}>
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>

              {/* Mobile menu button */}
              <Button 
                variant="ghost" 
                size="sm"
                className="md:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Side Navigation */}
      <div className="fixed inset-y-0 left-0 z-40 w-64 bg-sidebar border-r border-border pt-16 overflow-y-auto">
        <nav className="p-4 space-y-2">
          {/* Main Navigation */}
          {navigation.map((item) => (
            <NavItem key={item.name} item={item} isActive={isActive} />
          ))}

          {/* Admin Navigation (if admin) */}
          {isAdmin && (
            <>
              <div className="pt-4 mt-4 border-t border-border">
                <h3 className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  Administration
                </h3>
              </div>
              {adminNavigation.map((item) => (
                <NavItem key={item.name} item={item} isActive={isActive} />
              ))}
            </>
          )}
        </nav>

        {/* Organization Info */}
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-background border-t border-border">
          <div className="flex items-center space-x-3">
            <div 
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-sm font-bold"
              style={{ backgroundColor: currentOrg.color }}
            >
              {currentOrg.name.charAt(0)}
            </div>
            <div>
              <div className="font-medium text-sm">{currentOrg.name}</div>
              <div className="text-xs text-muted-foreground">{currentOrg.domain}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Navigation Overlay */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-30 md:hidden">
          <div className="absolute inset-0 bg-black opacity-25" onClick={() => setMobileMenuOpen(false)} />
          <div className="absolute left-0 top-16 w-64 h-full bg-background border-r border-border overflow-y-auto">
            <nav className="p-4 space-y-2">
              {navigation.concat(isAdmin ? adminNavigation : []).map((item) => (
                <NavItem 
                  key={item.name} 
                  item={item} 
                  isActive={isActive}
                  onClick={() => setMobileMenuOpen(false)}
                />
              ))}
            </nav>
          </div>
        </div>
      )}

      {/* Page Content Wrapper */}
      <div className="pl-64 pt-16">
        {/* This will wrap the page content */}
      </div>
    </>
  )
}

// Navigation Item Component
function NavItem({ 
  item, 
  isActive, 
  onClick 
}: { 
  item: NavigationItem
  isActive: (href: string) => boolean
  onClick?: () => void 
}) {
  const [isExpanded, setIsExpanded] = useState(isActive(item.href))
  const hasChildren = item.children && item.children.length > 0

  return (
    <div>
      <Link
        href={item.href}
        onClick={onClick}
        className={`
          flex items-center justify-between w-full px-3 py-2 text-sm font-medium rounded-md transition-colors
          ${isActive(item.href)
            ? 'bg-primary text-primary-foreground'
            : 'text-foreground/80 hover:bg-accent'
          }
        `}
      >
        <div className="flex items-center space-x-3">
          <item.icon className="h-5 w-5" />
          <span>{item.name}</span>
          {item.badge && (
            <Badge variant="secondary" className="ml-auto">
              {item.badge}
            </Badge>
          )}
        </div>
        {hasChildren && (
          <ChevronDown 
            className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            onClick={(e) => {
              e.preventDefault()
              setIsExpanded(!isExpanded)
            }}
          />
        )}
      </Link>

      {/* Sub-navigation */}
      {hasChildren && isExpanded && (
        <div className="ml-8 mt-1 space-y-1">
          {item.children!.map((child) => (
            <Link
              key={child.name}
              href={child.href}
              onClick={onClick}
              className={`
                flex items-center space-x-2 px-3 py-2 text-sm rounded-md transition-colors
                ${isActive(child.href)
                  ? 'bg-primary/10 text-primary'
                  : 'text-muted-foreground hover:bg-accent'
                }
              `}
            >
              <child.icon className="h-4 w-4" />
              <span>{child.name}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
