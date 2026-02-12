import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DocsLayout } from "@/components/docs-layout"
import { ArrowRight } from "lucide-react"
import { docsConfig } from "@/lib/docs-config"

export const metadata = {
  title: "SDKs",
  description: `Official ${docsConfig.brandName} client libraries for TypeScript, Python, Go, and Rust.`,
}

export default function SDKsPage() {
  return (
    <DocsLayout>
      <div className="space-y-10">
        {/* Header */}
        <div>
          <h1 className="text-4xl font-bold mb-4">SDKs & Libraries</h1>
          <p className="text-lg text-muted-foreground">
            Official client libraries for every major language. Each SDK provides
            type-safe access to all {docsConfig.brandName} APIs with built-in retry logic,
            authentication, and error handling.
          </p>
        </div>

        {/* TypeScript */}
        <section className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-xl">TypeScript / JavaScript</CardTitle>
                </div>
                <Badge variant="secondary">v2.0.0</Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Works with Node.js 18+, Bun, Deno, and all modern browsers (via bundler).
                Full TypeScript types included.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold mb-2">Install</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`npm install @bootnode/sdk
# or
yarn add @bootnode/sdk
# or
pnpm add @bootnode/sdk`}</code>
                </pre>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-2">Usage</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`import { Bootnode } from "@bootnode/sdk";

const client = new Bootnode({
  apiKey: process.env.BOOTNODE_API_KEY!,
});

// JSON-RPC
const blockNumber = await client.rpc("ethereum", "mainnet", {
  jsonrpc: "2.0",
  id: 1,
  method: "eth_blockNumber",
  params: [],
});
console.log("Block:", parseInt(blockNumber.result, 16));

// Token API
const balances = await client.tokens.getBalances("ethereum", "0xd8dA...6045");
console.log("Tokens:", balances.tokens);

// NFT API
const nft = await client.nfts.getMetadata(
  "ethereum",
  "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
  "1234"
);
console.log("NFT:", nft.name);

// Wallets
const wallet = await client.wallets.create({
  owner: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
  chain: "base",
});
console.log("Smart wallet:", wallet.address);

// Webhooks
const webhook = await client.webhooks.create({
  url: "https://myapp.com/api/webhooks",
  chain: "ethereum",
  eventType: "address_activity",
  config: { addresses: ["0xd8dA...6045"] },
});
console.log("Webhook ID:", webhook.id);

// Gas prices
const gas = await client.gas.getPrices("ethereum");
console.log("Base fee:", gas.base_fee_gwei, "gwei");

// WebSocket subscriptions
const ws = client.ws("ethereum", "mainnet");
ws.subscribe("newHeads", (block) => {
  console.log("New block:", parseInt(block.number, 16));
});

// Bundler
const userOpHash = await client.bundler.sendUserOperation("base", "mainnet", {
  sender: wallet.address,
  nonce: "0x0",
  callData: "0x...",
  // ... other UserOp fields
});
console.log("UserOp hash:", userOpHash);`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Python */}
        <section className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-xl">Python</CardTitle>
                </div>
                <Badge variant="secondary">v2.0.0</Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Python 3.10+. Async-first with sync wrappers. Full type hints with Pydantic models.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold mb-2">Install</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`pip install bootnode
# or
uv add bootnode`}</code>
                </pre>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-2">Usage</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`import asyncio
from bootnode import Bootnode

client = Bootnode(api_key="${docsConfig.apiKeyPrefix}live_...")

async def main():
    # JSON-RPC
    result = await client.rpc("ethereum", "mainnet", {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_blockNumber",
        "params": [],
    })
    block = int(result["result"], 16)
    print(f"Block: {block}")

    # Token balances
    balances = await client.tokens.get_balances(
        "ethereum",
        "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"
    )
    for token in balances["tokens"]:
        print(f"  {token['symbol']}: {token['formatted_balance']}")

    # NFT metadata
    nft = await client.nfts.get_metadata(
        "ethereum",
        "0xBC4CA0EdA7647A8aB7C2061c2E118A18a936f13D",
        "1234"
    )
    print(f"NFT: {nft['name']}")

    # Create smart wallet
    wallet = await client.wallets.create(
        owner="0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
        chain="base"
    )
    print(f"Wallet: {wallet['address']}")

    # Gas prices
    gas = await client.gas.get_prices("ethereum")
    print(f"Base fee: {gas['base_fee_gwei']} gwei")

asyncio.run(main())

# Sync usage (for scripts):
from bootnode import BootnodeSync

sync_client = BootnodeSync(api_key="${docsConfig.apiKeyPrefix}live_...")
gas = sync_client.gas.get_prices("ethereum")
print(f"Base fee: {gas['base_fee_gwei']} gwei")`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Go */}
        <section className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-xl">Go</CardTitle>
                </div>
                <Badge variant="secondary">v1.0.0</Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Go 1.21+. Context-aware, idiomatic Go with strong types.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold mb-2">Install</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`go get github.com/bootnode/bootnode-go`}</code>
                </pre>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-2">Usage</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"strconv"

	"github.com/bootnode/bootnode-go"
)

func main() {
	client := bootnode.NewClient(os.Getenv("BOOTNODE_API_KEY"))
	ctx := context.Background()

	// JSON-RPC
	result, err := client.RPC(ctx, "ethereum", "mainnet", map[string]any{
		"jsonrpc": "2.0",
		"id":      1,
		"method":  "eth_blockNumber",
		"params":  []any{},
	})
	if err != nil {
		log.Fatal(err)
	}
	blockHex := result["result"].(string)
	block, _ := strconv.ParseInt(blockHex[2:], 16, 64)
	fmt.Printf("Block: %d\\n", block)

	// Token balances
	balances, err := client.Tokens.GetBalances(ctx, "ethereum",
		"0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
	if err != nil {
		log.Fatal(err)
	}
	for _, token := range balances.Tokens {
		fmt.Printf("  %s: %s\\n", token.Symbol, token.FormattedBalance)
	}

	// Create smart wallet
	wallet, err := client.Wallets.Create(ctx, bootnode.CreateWalletParams{
		Owner: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
		Chain: "base",
	})
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Wallet: %s\\n", wallet.Address)

	// Gas prices
	gas, err := client.Gas.GetPrices(ctx, "ethereum")
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("Base fee: %s gwei\\n", gas.BaseFeeGwei)
}`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Rust */}
        <section className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CardTitle className="text-xl">Rust</CardTitle>
                </div>
                <Badge variant="secondary">v0.9.0</Badge>
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                Rust 1.75+. Async with Tokio. Serde-based serialization. Zero-copy where possible.
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-semibold mb-2">Install</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`# Cargo.toml
[dependencies]
bootnode = "0.9"
tokio = { version = "1", features = ["full"] }
serde_json = "1"`}</code>
                </pre>
              </div>
              <div>
                <h4 className="text-sm font-semibold mb-2">Usage</h4>
                <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-sm text-zinc-100">
                  <code>{`use bootnode::Client;
use serde_json::json;

#[tokio::main]
async fn main() -> Result<(), bootnode::Error> {
    let client = Client::new(
        std::env::var("BOOTNODE_API_KEY")
            .expect("BOOTNODE_API_KEY must be set")
    );

    // JSON-RPC
    let result = client
        .rpc("ethereum", "mainnet", json!({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_blockNumber",
            "params": []
        }))
        .await?;

    let block_hex = result["result"].as_str().unwrap();
    let block = u64::from_str_radix(&block_hex[2..], 16).unwrap();
    println!("Block: {block}");

    // Token balances
    let balances = client
        .tokens()
        .get_balances("ethereum", "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        .await?;

    for token in &balances.tokens {
        println!("  {}: {}", token.symbol, token.formatted_balance);
    }

    // Create smart wallet
    let wallet = client
        .wallets()
        .create("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "base")
        .await?;
    println!("Wallet: {}", wallet.address);

    // Gas prices
    let gas = client.gas().get_prices("ethereum").await?;
    println!("Base fee: {} gwei", gas.base_fee_gwei);

    Ok(())
}`}</code>
                </pre>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Feature Matrix */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Feature Matrix</h2>
          <div className="overflow-x-auto border rounded-lg">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="text-left p-3 font-medium">Feature</th>
                  <th className="text-left p-3 font-medium">TypeScript</th>
                  <th className="text-left p-3 font-medium">Python</th>
                  <th className="text-left p-3 font-medium">Go</th>
                  <th className="text-left p-3 font-medium">Rust</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { feature: "JSON-RPC", ts: true, py: true, go: true, rs: true },
                  { feature: "Token API", ts: true, py: true, go: true, rs: true },
                  { feature: "NFT API", ts: true, py: true, go: true, rs: true },
                  { feature: "Wallets", ts: true, py: true, go: true, rs: true },
                  { feature: "Webhooks", ts: true, py: true, go: true, rs: true },
                  { feature: "Gas Manager", ts: true, py: true, go: true, rs: true },
                  { feature: "Bundler", ts: true, py: true, go: true, rs: true },
                  { feature: "WebSocket", ts: true, py: true, go: true, rs: true },
                  { feature: "Auto-retry", ts: true, py: true, go: true, rs: true },
                  { feature: "Streaming", ts: true, py: true, go: true, rs: true },
                ].map((row) => (
                  <tr key={row.feature} className="border-b last:border-0">
                    <td className="p-3 font-medium">{row.feature}</td>
                    <td className="p-3">{row.ts ? "Yes" : "Coming soon"}</td>
                    <td className="p-3">{row.py ? "Yes" : "Coming soon"}</td>
                    <td className="p-3">{row.go ? "Yes" : "Coming soon"}</td>
                    <td className="p-3">{row.rs ? "Yes" : "Coming soon"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Next Steps */}
        <section className="space-y-4">
          <h2 className="text-2xl font-semibold">Next Steps</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              { title: "Quickstart", href: "/docs/quickstart", desc: "Get your first call running" },
              { title: "API Reference", href: "/docs/api", desc: "Full endpoint documentation" },
              { title: "Examples", href: "/docs/examples", desc: "Common use cases" },
              { title: "Changelog", href: "/docs/changelog", desc: "Latest SDK updates" },
            ].map((item) => (
              <Link
                key={item.title}
                href={item.href}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted transition-colors group"
              >
                <div>
                  <p className="font-medium">{item.title}</p>
                  <p className="text-sm text-muted-foreground">{item.desc}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-foreground transition-colors" />
              </Link>
            ))}
          </div>
        </section>
      </div>
    </DocsLayout>
  )
}
