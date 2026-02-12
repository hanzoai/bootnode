"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { billing } from "@/lib/api"
import {
  CreditCard,
  Check,
  Zap,
  Loader2,
  ArrowUpRight,
  AlertCircle,
} from "lucide-react"

interface Tier {
  name: string
  slug: string
  monthly_cu: number
  rate_limit_per_second: number
  max_apps: number
  max_webhooks: number
  price_per_million_cu: number
  features: string[]
  support_level: string
}

interface Subscription {
  tier: string
  status: string
  current_period_start: string | null
  current_period_end: string | null
}

interface UsageSummary {
  total_cu: number
  cost_cents: number
  period: string
}

export default function BillingPage() {
  const [loading, setLoading] = useState(true)
  const [tiers, setTiers] = useState<Tier[]>([])
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [upgrading, setUpgrading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchBillingData() {
      try {
        const [tiersData, subData, usageData] = await Promise.allSettled([
          billing.getTiers(),
          billing.getSubscription(),
          billing.getUsageSummary(),
        ])

        if (tiersData.status === "fulfilled") {
          setTiers(tiersData.value as Tier[])
        }
        if (subData.status === "fulfilled") {
          setSubscription(subData.value as Subscription)
        }
        if (usageData.status === "fulfilled") {
          setUsage(usageData.value as UsageSummary)
        }
      } catch (err) {
        console.error("Failed to fetch billing data:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchBillingData()
  }, [])

  async function handleUpgrade(tierSlug: string) {
    setUpgrading(tierSlug)
    setError(null)
    try {
      const result = await billing.createCheckout({
        tier: tierSlug,
        success_url: `${window.location.origin}/dashboard/organization/billing?upgraded=true`,
        cancel_url: `${window.location.origin}/dashboard/organization/billing`,
      }) as { checkout_url?: string }

      if (result.checkout_url) {
        window.location.href = result.checkout_url
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start checkout")
    } finally {
      setUpgrading(null)
    }
  }

  const currentTier = subscription?.tier || "free"

  // Fallback tiers if API hasn't returned them yet
  const displayTiers: Tier[] = tiers.length > 0 ? tiers : [
    {
      name: "Free", slug: "free", monthly_cu: 30_000_000,
      rate_limit_per_second: 25, max_apps: 5, max_webhooks: 5,
      price_per_million_cu: 0, support_level: "community",
      features: ["30M compute units/month", "25 req/s", "5 apps", "5 webhooks", "Community support"],
    },
    {
      name: "Pay As You Go", slug: "payg", monthly_cu: 0,
      rate_limit_per_second: 300, max_apps: 30, max_webhooks: 100,
      price_per_million_cu: 40, support_level: "email",
      features: ["Unlimited compute units", "300 req/s", "30 apps", "100 webhooks", "Email support", "Usage analytics"],
    },
    {
      name: "Growth", slug: "growth", monthly_cu: 100_000_000,
      rate_limit_per_second: 500, max_apps: 50, max_webhooks: 250,
      price_per_million_cu: 35, support_level: "priority",
      features: ["100M CU included", "500 req/s", "50 apps", "250 webhooks", "Priority support", "Advanced analytics"],
    },
    {
      name: "Enterprise", slug: "enterprise", monthly_cu: 0,
      rate_limit_per_second: 1000, max_apps: 0, max_webhooks: 500,
      price_per_million_cu: 0, support_level: "dedicated",
      features: ["Custom CU", "Custom rate limits", "Unlimited apps", "500+ webhooks", "Dedicated support", "SLA guarantee"],
    },
  ]

  function tierPrice(tier: Tier): string {
    if (tier.slug === "free") return "Free"
    if (tier.slug === "enterprise") return "Custom"
    if (tier.slug === "payg") return `$${(tier.price_per_million_cu / 100).toFixed(2)}/M CU`
    // Growth: show base price estimate
    return `$${(tier.price_per_million_cu / 100).toFixed(2)}/M CU`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Billing</h1>
        <p className="text-muted-foreground">
          Manage your subscription and usage
        </p>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4 flex items-center gap-2 text-destructive">
            <AlertCircle className="h-4 w-4" />
            {error}
          </CardContent>
        </Card>
      )}

      {/* Current Plan & Usage */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Current Plan
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3 mb-4">
              <Badge variant="default" className="text-base px-3 py-1">
                {currentTier.charAt(0).toUpperCase() + currentTier.slice(1)}
              </Badge>
              {subscription?.status && (
                <Badge variant={subscription.status === "active" ? "default" : "secondary"}>
                  {subscription.status}
                </Badge>
              )}
            </div>
            {subscription?.current_period_end && (
              <p className="text-sm text-muted-foreground">
                Current period ends {new Date(subscription.current_period_end).toLocaleDateString()}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-5 w-5" />
              Usage This Period
            </CardTitle>
          </CardHeader>
          <CardContent>
            {usage ? (
              <>
                <div className="text-2xl font-bold">
                  {((usage.total_cu || 0) / 1_000_000).toFixed(1)}M CU
                </div>
                <p className="text-sm text-muted-foreground">
                  {usage.cost_cents
                    ? `$${(usage.cost_cents / 100).toFixed(2)} estimated cost`
                    : "No charges this period"}
                </p>
              </>
            ) : (
              <>
                <div className="text-2xl font-bold text-muted-foreground">-</div>
                <p className="text-sm text-muted-foreground">No usage data available</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pricing Tiers */}
      <div>
        <h2 className="text-xl font-bold mb-4">Plans</h2>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {displayTiers.map((tier) => {
            const isCurrent = tier.slug === currentTier
            const isUpgrade = !isCurrent && tier.slug !== "free" && tier.slug !== "enterprise"
            return (
              <Card key={tier.slug} className={isCurrent ? "border-primary" : ""}>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    {tier.name}
                    {isCurrent && <Badge>Current</Badge>}
                  </CardTitle>
                  <CardDescription className="text-lg font-semibold text-foreground">
                    {tierPrice(tier)}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2 text-sm">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-start gap-2">
                        <Check className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>
                  {isCurrent ? (
                    <Button variant="outline" className="w-full" disabled>
                      Current Plan
                    </Button>
                  ) : tier.slug === "enterprise" ? (
                    <Button variant="outline" className="w-full" asChild>
                      <a href="mailto:sales@bootno.de">
                        Contact Sales
                        <ArrowUpRight className="ml-2 h-4 w-4" />
                      </a>
                    </Button>
                  ) : isUpgrade ? (
                    <Button
                      className="w-full"
                      onClick={() => handleUpgrade(tier.slug)}
                      disabled={upgrading !== null}
                    >
                      {upgrading === tier.slug ? (
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                      ) : null}
                      Upgrade
                    </Button>
                  ) : (
                    <Button variant="ghost" className="w-full" disabled>
                      -
                    </Button>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Info */}
      <Card className="bg-muted/50">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-muted-foreground mt-0.5" />
            <div>
              <p className="font-medium">Billing via Hanzo Commerce</p>
              <p className="text-sm text-muted-foreground">
                Payments are processed securely via Square through Hanzo Commerce.
                Compute units are tracked in real-time and billed at the end of each period.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
