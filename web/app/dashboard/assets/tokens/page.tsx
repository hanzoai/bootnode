"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Coins, Search, Loader2 } from "lucide-react"

interface TokenMetadata {
  contract_address: string
  name: string
  symbol: string
  decimals: number
  total_supply?: string
  logo_url?: string
}

export default function TokensPage() {
  const [chain, setChain] = useState("ethereum")
  const [contract, setContract] = useState("")
  const [loading, setLoading] = useState(false)
  const [token, setToken] = useState<TokenMetadata | null>(null)
  const [error, setError] = useState<string | null>(null)

  function getAuthHeaders(): Record<string, string> {
    const token = localStorage.getItem("bootnode_token")
    const apiKey = localStorage.getItem("bootnode_api_key")
    if (token) return { "Authorization": `Bearer ${token}` }
    if (apiKey) return { "X-API-Key": apiKey }
    return {}
  }

  async function handleSearch() {
    if (!contract.trim()) return
    setLoading(true)
    setError(null)
    setToken(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const res = await fetch(`${apiUrl}/v1/tokens/${chain}/metadata/${contract}`, {
        headers: getAuthHeaders()
      })
      if (!res.ok) {
        throw new Error(`Failed to fetch token: ${res.status}`)
      }
      const data = await res.json()
      setToken(data)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Tokens</h1>
        <p className="text-muted-foreground">
          Query ERC-20 token metadata and balances
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5" />
            Token Lookup
          </CardTitle>
          <CardDescription>
            Search for token metadata by contract address
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="text-sm font-medium">Chain</label>
              <Input
                value={chain}
                onChange={(e) => setChain(e.target.value)}
                placeholder="ethereum, polygon, base..."
                className="mt-1"
              />
            </div>
            <div className="md:col-span-2">
              <label className="text-sm font-medium">Contract Address</label>
              <div className="flex gap-2 mt-1">
                <Input
                  value={contract}
                  onChange={(e) => setContract(e.target.value)}
                  placeholder="0x..."
                  className="font-mono"
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                />
                <Button onClick={handleSearch} disabled={loading || !contract.trim()}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-destructive/10 p-4 text-destructive">{error}</div>
          )}

          {token && (
            <div className="p-4 border rounded-lg space-y-3">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <Coins className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <h3 className="font-bold text-lg">{token.name}</h3>
                  <p className="text-muted-foreground">{token.symbol}</p>
                </div>
              </div>
              <div className="grid gap-2 md:grid-cols-2">
                <div>
                  <p className="text-sm text-muted-foreground">Contract</p>
                  <code className="text-sm font-mono">{token.contract_address}</code>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Decimals</p>
                  <p className="font-medium">{token.decimals}</p>
                </div>
                {token.total_supply && (
                  <div>
                    <p className="text-sm text-muted-foreground">Total Supply</p>
                    <p className="font-medium">{token.total_supply}</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Popular Tokens</CardTitle>
          <CardDescription>Quick access to commonly queried tokens</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {[
              { symbol: "USDC", contract: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", chain: "ethereum" },
              { symbol: "USDT", contract: "0xdAC17F958D2ee523a2206206994597C13D831ec7", chain: "ethereum" },
              { symbol: "WETH", contract: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", chain: "ethereum" },
              { symbol: "DAI", contract: "0x6B175474E89094C44Da98b954EescdeCB5Bf6BB", chain: "ethereum" },
            ].map((t) => (
              <Button
                key={t.symbol}
                variant="outline"
                className="justify-start"
                onClick={() => { setChain(t.chain); setContract(t.contract); }}
              >
                <Coins className="mr-2 h-4 w-4" />
                {t.symbol}
                <Badge variant="secondary" className="ml-auto">{t.chain}</Badge>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
