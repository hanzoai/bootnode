"use client"

import { useState, useEffect, Suspense, type FormEvent } from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Loader2 } from "lucide-react"
import { useAuth, HanzoLoginButton } from "@/lib/auth"
import { BrandLogo, useBrand } from "@/components/brand-logo"

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, isLoading: authLoading, isProduction, login, register } = useAuth()
  const brand = useBrand()

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [name, setName] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [mode, setMode] = useState<"login" | "register">("login")

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && user) {
      const returnUrl = searchParams.get("returnUrl") || "/dashboard"
      router.push(returnUrl)
    }
  }, [user, authLoading, router, searchParams])

  // Production mode: Redirect to brand-specific IAM
  useEffect(() => {
    if (isProduction && !authLoading && !user) {
      const returnUrl = searchParams.get("returnUrl") || "/dashboard"
      const callbackUrl = `${window.location.origin}/auth/callback`
      const iamUrl = brand.iam.url
      const authRedirect = `${iamUrl}/login?redirect_uri=${encodeURIComponent(callbackUrl)}&state=${encodeURIComponent(returnUrl)}`
      window.location.href = authRedirect
    }
  }, [isProduction, authLoading, user, searchParams, brand.iam.url])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      if (mode === "register") {
        await register(email, password, name)
      } else {
        await login(email, password)
      }
      const returnUrl = searchParams.get("returnUrl") || "/dashboard"
      router.push(returnUrl)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed")
    } finally {
      setLoading(false)
    }
  }

  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  // Show loading while redirecting in production
  if (isProduction) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-muted/20 px-4">
        <Link href="/" className="mb-8">
          <BrandLogo size="large" />
        </Link>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Redirecting to {brand.name} login...</p>
        </div>
      </div>
    )
  }

  // Development mode: Show email/password form
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background to-muted/20 px-4">
      <Link href="/" className="mb-8">
        <BrandLogo size="large" />
      </Link>

      <Card className="w-full max-w-sm">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">
            {mode === "login" ? "Sign in" : "Create account"}
          </CardTitle>
          <CardDescription>
            {mode === "login"
              ? "Enter your credentials to access the dashboard"
              : "Create a new account to get started"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs value={mode} onValueChange={(v) => setMode(v as "login" | "register")}>
            <TabsList className="grid w-full grid-cols-2 mb-4">
              <TabsTrigger value="login">Sign In</TabsTrigger>
              <TabsTrigger value="register">Register</TabsTrigger>
            </TabsList>

            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                  {error}
                </div>
              )}

              {mode === "register" && (
                <div className="space-y-2">
                  <label htmlFor="name" className="text-sm font-medium">
                    Name
                  </label>
                  <Input
                    id="name"
                    type="text"
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    required={mode === "register"}
                  />
                </div>
              )}

              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  required
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                  minLength={8}
                />
              </div>

              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {mode === "login" ? "Signing in..." : "Creating account..."}
                  </>
                ) : (
                  mode === "login" ? "Sign in" : "Create account"
                )}
              </Button>
            </form>
          </Tabs>

          {/* Quick login for local dev */}
          <div className="mt-6 space-y-2">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">Quick Login</span>
              </div>
            </div>
            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={loading}
              onClick={async () => {
                setMode("login")
                setEmail("z@lux.network")
                setPassword("admin")
                setLoading(true)
                setError("")
                try {
                  await login("z@lux.network", "admin")
                  const returnUrl = searchParams.get("returnUrl") || "/dashboard"
                  router.push(returnUrl)
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Login failed")
                } finally {
                  setLoading(false)
                }
              }}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in...
                </>
              ) : (
                <>Sign in as Admin (z@lux.network)</>
              )}
            </Button>
            <p className="text-center text-[10px] text-muted-foreground">
              Local dev only &mdash; z@lux.network / admin
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

function LoginFallback() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFallback />}>
      <LoginForm />
    </Suspense>
  )
}

