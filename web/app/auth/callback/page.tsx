// OAuth Callback Handler for Hanzo IAM
"use client"

import { Suspense, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useAuth } from "@/lib/auth"
import { getBrand } from "@/lib/brand"

function CallbackContent() {
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
  const [error, setError] = useState("")
  const router = useRouter()
  const searchParams = useSearchParams()
  const { loginWithToken } = useAuth()

  useEffect(() => {
    handleCallback()
  }, [])

  async function handleCallback() {
    try {
      const code = searchParams.get("code")
      const stateParam = searchParams.get("state")
      const errorParam = searchParams.get("error")

      if (errorParam) {
        throw new Error(`OAuth error: ${errorParam}`)
      }

      if (!code) {
        throw new Error("No authorization code received")
      }

      // Parse state to get return URL
      let returnUrl = "/dashboard"
      try {
        const state = JSON.parse(decodeURIComponent(stateParam || "{}"))
        returnUrl = state.returnUrl || "/dashboard"
      } catch {
        // State might be just the org name
      }

      // Exchange code for token via our API
      const brand = getBrand()
      const apiUrl = (typeof window !== "undefined" && window.location.hostname !== "localhost")
        ? brand.apiUrl
        : (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
      const response = await fetch(`${apiUrl}/v1/auth/oauth/callback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ code, state: stateParam }),
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || `Authentication failed: ${response.statusText}`)
      }

      const { access_token } = await response.json()

      await loginWithToken(access_token)

      setStatus("success")

      // Redirect to dashboard after successful login
      setTimeout(() => {
        router.push(returnUrl)
      }, 1500)

    } catch (err) {
      console.error("Auth callback error:", err)
      setError(err instanceof Error ? err.message : "Authentication failed")
      setStatus("error")

      // Redirect to login after error
      setTimeout(() => {
        router.push("/login")
      }, 3000)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        {status === "loading" && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
            <h1 className="text-xl font-semibold">Completing authentication...</h1>
            <p className="text-muted-foreground">Please wait while we verify your credentials</p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center mx-auto">
              <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-green-600">Authentication Successful!</h1>
            <p className="text-muted-foreground">Redirecting to your dashboard...</p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mx-auto">
              <svg className="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="text-xl font-semibold text-red-600">Authentication Failed</h1>
            <p className="text-muted-foreground">{error}</p>
            <p className="text-sm text-muted-foreground">Redirecting to login...</p>
          </>
        )}
      </div>
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
      </div>
    }>
      <CallbackContent />
    </Suspense>
  )
}
