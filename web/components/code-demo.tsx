"use client"

import { useState } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Check, Copy, Play } from "lucide-react"
import { getBrand } from "@/lib/brand"

const CHAINS = ["Ethereum", "Solana", "Base", "Arbitrum", "Polygon"]
const METHODS = [
  "eth_getBlockByNumber",
  "eth_getBalance",
  "eth_call",
  "eth_getLogs",
]

export function CodeDemo() {
  const [selectedChain, setSelectedChain] = useState("Ethereum")
  const [selectedMethod, setSelectedMethod] = useState("eth_getBlockByNumber")
  const [copied, setCopied] = useState(false)
  const [response, setResponse] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const brand = getBrand()
  // Use api.web3.hanzo.ai for Hanzo branding (brand.name is "Hanzo Web3")
  const apiDomain = brand.name.includes("Hanzo") ? "api.web3.hanzo.ai" : `api.${brand.domain}`
  const code = `curl -X POST https://${apiDomain}/v1/rpc/${selectedChain.toLowerCase()}/mainnet \\
     -H "Content-Type: application/json" \\
     -H "X-API-Key: your_api_key" \\
     -d '{
  "jsonrpc": "2.0",
  "method": "${selectedMethod}",
  "params": [
    "latest",
    false
  ],
  "id": 1
}'`

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleRun = async () => {
    setLoading(true)
    // Simulate API response
    await new Promise((resolve) => setTimeout(resolve, 500))
    setResponse(JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      result: {
        number: "0x13a40f7",
        hash: "0x7f5c9...",
        timestamp: "0x66a4e3c0",
        transactions: ["0xabc...", "0xdef..."],
      },
    }, null, 2))
    setLoading(false)
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap gap-2">
        <div className="flex gap-1">
          {CHAINS.map((chain) => (
            <Button
              key={chain}
              variant={selectedChain === chain ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedChain(chain)}
            >
              {chain}
            </Button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {METHODS.map((method) => (
          <Badge
            key={method}
            variant={selectedMethod === method ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setSelectedMethod(method)}
          >
            {method}
          </Badge>
        ))}
      </div>

      {/* Code Block */}
      <div className="relative overflow-hidden rounded-lg border bg-zinc-950">
        <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
          <span className="text-sm font-medium text-zinc-400">Request</span>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-zinc-400 hover:text-white"
              onClick={handleCopy}
            >
              {copied ? (
                <>
                  <Check className="mr-1 h-4 w-4" />
                  Copied
                </>
              ) : (
                <>
                  <Copy className="mr-1 h-4 w-4" />
                  Copy
                </>
              )}
            </Button>
            <Button
              size="sm"
              className="h-8"
              onClick={handleRun}
              disabled={loading}
            >
              <Play className="mr-1 h-4 w-4" />
              {loading ? "Running..." : "Run"}
            </Button>
          </div>
        </div>
        <pre className="overflow-x-auto p-4">
          <code className="text-sm text-zinc-300">{code}</code>
        </pre>
      </div>

      {/* Response */}
      {response && (
        <div className="overflow-hidden rounded-lg border bg-zinc-950">
          <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
            <span className="text-sm font-medium text-zinc-400">Response</span>
            <Badge variant="success">200 OK</Badge>
          </div>
          <pre className="overflow-x-auto p-4">
            <code className="text-sm text-green-400">{response}</code>
          </pre>
        </div>
      )}
    </div>
  )
}
