"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Building, Users, Settings, Key, Loader2, CreditCard } from "lucide-react"
import Link from "next/link"
import { useAuth } from "@/lib/auth"

interface OrgStats {
  name: string
  tier: string
  teamMembers: number
  apiKeys: number
  projectId: string
}

export default function OrganizationPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState<OrgStats | null>(null)

  function getAuthHeaders(): Record<string, string> {
    if (typeof window === "undefined") return {}
    const token = localStorage.getItem("bootnode_token")
    const apiKey = localStorage.getItem("bootnode_api_key")
    if (token) return { "Authorization": `Bearer ${token}` }
    if (apiKey) return { "X-API-Key": apiKey }
    return {}
  }

  useEffect(() => {
    async function fetchOrgData() {
      try {
        const headers = getAuthHeaders()

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        const [teamRes, keysRes] = await Promise.all([
          fetch(`${apiUrl}/v1/team`, { headers }).catch(() => null),
          fetch(`${apiUrl}/v1/auth/keys`, { headers }).catch(() => null),
        ])

        const teamData = teamRes?.ok ? await teamRes.json() : { members: [], total: 0 }
        const keysData = keysRes?.ok ? await keysRes.json() : []

        // Get project name from user context or default
        const projectName = user?.name ? `${user.name}'s Project` : "My Project"

        setStats({
          name: projectName,
          tier: "Free",
          teamMembers: teamData.total || 0,
          apiKeys: Array.isArray(keysData) ? keysData.length : 0,
          projectId: user?.id || ""
        })
      } catch (err) {
        console.error("Failed to fetch org data:", err)
      } finally {
        setLoading(false)
      }
    }

    fetchOrgData()
  }, [user])

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Organization</h1>
        <p className="text-muted-foreground">
          Manage your organization, team members, and settings
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Organization</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <>
                <div className="text-lg font-bold">{stats?.name || "My Project"}</div>
                <Badge variant="outline" className="mt-1">{stats?.tier || "Free"} tier</Badge>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Team Members</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stats?.teamMembers || 0}</div>
                <p className="text-xs text-muted-foreground">active members</p>
              </>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">API Keys</CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <>
                <div className="text-2xl font-bold">{stats?.apiKeys || 0}</div>
                <p className="text-xs text-muted-foreground">active keys</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Team
            </CardTitle>
            <CardDescription>
              Manage team members and permissions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {stats?.teamMembers === 0
                ? "No team members yet. Invite your first collaborator."
                : `You have ${stats?.teamMembers} team member${stats?.teamMembers !== 1 ? "s" : ""}.`}
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/organization/team">
                Manage Team
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Settings
            </CardTitle>
            <CardDescription>
              Organization settings and preferences
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Configure organization name, CORS origins, and notifications.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/organization/settings">
                Organization Settings
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Keys
            </CardTitle>
            <CardDescription>
              Manage API access credentials
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              {stats?.apiKeys === 0
                ? "No API keys yet. Create one to get started."
                : `You have ${stats?.apiKeys} active API key${stats?.apiKeys !== 1 ? "s" : ""}.`}
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/api-keys">
                Manage API Keys
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Billing
            </CardTitle>
            <CardDescription>
              Subscription and payment settings
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge variant="outline">{stats?.tier || "Free"} Tier</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Upgrade to access more features and higher rate limits.
            </p>
            <Button variant="outline" className="w-full" asChild>
              <Link href="/dashboard/organization/billing">
                Manage Subscription
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
