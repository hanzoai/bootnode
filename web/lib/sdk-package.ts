// Brand-aware SDK package + client class names.
// Used by docs samples and install snippets.

import { getBrandKey_ } from "@/lib/brand"

const PACKAGES: Record<string, { pkg: string; client: string }> = {
  bootnode: { pkg: "@bootnode/sdk", client: "BootnodeClient" },
  hanzo: { pkg: "@hanzo/web3-sdk", client: "HanzoClient" },
  lux: { pkg: "@luxfi/cloud-sdk", client: "LuxClient" },
  zoo: { pkg: "@zooai/cloud-sdk", client: "ZooClient" },
  pars: { pkg: "@parsnetwork/sdk", client: "ParsClient" },
}

export function getSdkPackage(): { pkg: string; client: string } {
  return PACKAGES[getBrandKey_()] ?? PACKAGES.bootnode
}
