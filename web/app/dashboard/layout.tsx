"use client"

// Unified Dashboard Layout - Single layout for all dashboard pages
// Includes navigation, organization switching, team management

import { UnifiedNavigation } from "@/components/unified-navigation"
import { ProtectedRoute } from "@/lib/auth"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-background text-foreground">
        <UnifiedNavigation />

        {/* Main Content Area */}
        <main className="pl-64 pt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {children}
          </div>
        </main>
      </div>
    </ProtectedRoute>
  )
}
