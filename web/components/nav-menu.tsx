"use client"

import { useState, useEffect, useRef, ReactNode } from "react"
import { ChevronDown } from "lucide-react"
import { useMediaQuery } from "@/hooks/use-media-query"
import { cn } from "@/lib/utils"

type NavMenuProps = {
  label: string
  children: ReactNode | ((closeMenu: () => void) => ReactNode)
}

export function NavMenu({ label, children }: NavMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const isDesktop = useMediaQuery("(min-width: 1024px)")
  const closeTimeoutRef = useRef<number | null>(null)

  const handleMouseEnter = () => {
    if (isDesktop) {
      if (closeTimeoutRef.current) {
        window.clearTimeout(closeTimeoutRef.current)
        closeTimeoutRef.current = null
      }
      setIsOpen(true)
    }
  }

  const handleMouseLeave = () => {
    if (isDesktop) {
      closeTimeoutRef.current = window.setTimeout(() => setIsOpen(false), 150)
    }
  }

  const closeMenu = () => setIsOpen(false)

  useEffect(() => {
    return () => {
      if (closeTimeoutRef.current) window.clearTimeout(closeTimeoutRef.current)
    }
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const childrenWithProps =
    typeof children === "function" ? children(closeMenu) : children

  return (
    <div
      className="relative"
      ref={menuRef}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button
        onClick={() => !isDesktop && setIsOpen(!isOpen)}
        className={cn(
          "inline-flex items-center outline-none focus:outline-none transition-colors text-sm font-medium cursor-pointer",
          isOpen
            ? "text-foreground"
            : "text-muted-foreground hover:text-foreground"
        )}
      >
        {label}
        <ChevronDown
          className={cn(
            "ml-1 h-4 w-4 transition-transform duration-300",
            isOpen && "rotate-180"
          )}
        />
      </button>

      {isOpen && isDesktop && (
        <div
          className="fixed left-0 w-full backdrop-blur-md z-50 border-b shadow-2xl bg-background/95 border-border/50"
          style={{ top: "4rem" }}
        >
          <div className="py-4">
            <div className="w-full max-w-[1400px] mx-auto px-4 md:px-6 lg:px-10">
              {childrenWithProps}
            </div>
          </div>
        </div>
      )}

      {isOpen && !isDesktop && (
        <div
          className="fixed inset-0 left-0 right-0 backdrop-blur-md z-50 w-screen bg-background/95"
          style={{ top: "4rem", height: "calc(100vh - 4rem)" }}
          onClick={closeMenu}
        >
          <div
            className="relative w-full h-full overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-4 sm:px-6 lg:px-8 py-6">{childrenWithProps}</div>
          </div>
        </div>
      )}
    </div>
  )
}
