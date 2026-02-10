// Bootnode Authentication
// - Development: Built-in email/password auth
// - Production: Hanzo IAM (hanzo.id, zoo.id, lux.id, pars.id)

"use client"

import { createContext, useContext, useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { getBrand } from "@/lib/brand"

interface BootnodeUser {
  id: string
  name: string
  email: string
  org: "hanzo" | "zoo" | "lux" | "pars" | "local"
  avatar?: string
  roles: string[]
  permissions: string[]
  createdAt?: string
}

interface AuthContextType {
  user: BootnodeUser | null
  isLoading: boolean
  isProduction: boolean
  login: (email: string, password: string) => Promise<void>
  loginWithToken: (token: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  hasRole: (role: string) => boolean
  hasPermission: (permission: string) => boolean
  isAdmin: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Check if we're in production mode
const isProductionMode = () => {
  if (typeof window === "undefined") return false
  return process.env.NEXT_PUBLIC_AUTH_MODE === "iam" ||
         window.location.hostname !== "localhost"
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}

interface AuthProviderProps {
  children: React.ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<BootnodeUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const isProduction = isProductionMode()

  const getApiUrl = useCallback(() => {
    if (typeof window !== "undefined" && window.location.hostname !== "localhost") {
      return getBrand().apiUrl
    }
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
  }, [])

  useEffect(() => {
    checkAuth()
  }, [])

  async function checkAuth() {
    try {
      const token = localStorage.getItem("bootnode_token")
      if (!token) {
        setIsLoading(false)
        return
      }

      const apiUrl = getApiUrl()
      const response = await fetch(`${apiUrl}/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })

      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      } else {
        // Token is invalid or expired
        localStorage.removeItem("bootnode_token")
      }
    } catch (error) {
      console.error("Auth check failed:", error)
      localStorage.removeItem("bootnode_token")
    } finally {
      setIsLoading(false)
    }
  }

  async function login(email: string, password: string) {
    try {
      const apiUrl = getApiUrl()
      const response = await fetch(`${apiUrl}/v1/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Login failed" }))
        throw new Error(error.detail || "Login failed")
      }

      const { access_token, user: userData } = await response.json()
      localStorage.setItem("bootnode_token", access_token)
      setUser(userData)
      toast.success("Successfully logged in!")
    } catch (error) {
      console.error("Login failed:", error)
      throw error
    }
  }

  async function loginWithToken(token: string) {
    try {
      localStorage.setItem("bootnode_token", token)
      await checkAuth()
      toast.success("Successfully logged in!")
    } catch (error) {
      console.error("Token login failed:", error)
      localStorage.removeItem("bootnode_token")
      throw error
    }
  }

  async function register(email: string, password: string, name: string) {
    try {
      const apiUrl = getApiUrl()
      const response = await fetch(`${apiUrl}/v1/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password, name }),
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Registration failed" }))
        throw new Error(error.detail || "Registration failed")
      }

      const { access_token, user: userData } = await response.json()
      localStorage.setItem("bootnode_token", access_token)
      setUser(userData)
      toast.success("Account created successfully!")
    } catch (error) {
      console.error("Registration failed:", error)
      throw error
    }
  }

  function logout() {
    localStorage.removeItem("bootnode_token")
    localStorage.removeItem("bootnode_project_id")
    setUser(null)
    toast.success("Successfully logged out!")
  }

  function hasRole(role: string): boolean {
    return user?.roles.includes(role) ?? false
  }

  function hasPermission(permission: string): boolean {
    return user?.permissions.includes(permission) ?? false
  }

  const isAdmin = user?.roles.includes("admin") ?? false

  const value = {
    user,
    isLoading,
    isProduction,
    login,
    loginWithToken,
    register,
    logout,
    hasRole,
    hasPermission,
    isAdmin,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Hanzo IAM Login Button Component (for production)
export function HanzoLoginButton({ org = "hanzo" }: { org?: "hanzo" | "zoo" | "lux" | "pars" }) {
  const handleLogin = () => {
    const iamUrl = process.env.NEXT_PUBLIC_IAM_URL || "https://iam.hanzo.ai"
    const clientId = process.env.NEXT_PUBLIC_IAM_CLIENT_ID || "bootnode-platform"
    const redirectUri = encodeURIComponent(`${window.location.origin}/auth/callback`)

    const authUrl = `${iamUrl}/oauth2/authorize?` +
      `response_type=code&` +
      `client_id=${clientId}&` +
      `redirect_uri=${redirectUri}&` +
      `scope=openid+profile+email&` +
      `state=${org}`

    window.location.href = authUrl
  }

  const orgConfig = {
    hanzo: { name: "Hanzo ID", color: "bg-blue-600 hover:bg-blue-700" },
    zoo: { name: "Zoo ID", color: "bg-green-600 hover:bg-green-700" },
    lux: { name: "Lux ID", color: "bg-purple-600 hover:bg-purple-700" },
    pars: { name: "Pars ID", color: "bg-orange-600 hover:bg-orange-700" },
  }

  const config = orgConfig[org]

  return (
    <button
      onClick={handleLogin}
      className={`inline-flex items-center justify-center gap-2 rounded-md ${config.color} px-4 py-2 text-sm font-medium text-white shadow transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50`}
    >
      Continue with {config.name}
    </button>
  )
}

// Organization Badge Component
export function OrgBadge({ org }: { org: string }) {
  const orgConfig = {
    hanzo: { name: "Hanzo", color: "bg-blue-500" },
    zoo: { name: "Zoo Labs", color: "bg-green-500" },
    lux: { name: "Lux Network", color: "bg-purple-500" },
    pars: { name: "Pars", color: "bg-orange-500" },
    local: { name: "Local", color: "bg-gray-500" },
  }

  const config = orgConfig[org as keyof typeof orgConfig] || orgConfig.local

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium text-white ${config.color}`}>
      {config.name}
    </span>
  )
}

// Protected Route Component
export function ProtectedRoute({
  children,
  requiredRole,
  requiredPermission
}: {
  children: React.ReactNode
  requiredRole?: string
  requiredPermission?: string
}) {
  const { user, isLoading, hasRole, hasPermission, isProduction } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isLoading && !user) {
      router.push("/login")
    }
  }, [user, isLoading, router])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Access Denied</h1>
          <p className="text-muted-foreground">You don't have the required role: {requiredRole}</p>
        </div>
      </div>
    )
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Access Denied</h1>
          <p className="text-muted-foreground">You don't have the required permission: {requiredPermission}</p>
        </div>
      </div>
    )
  }

  return <>{children}</>
}
