/**
 * Wallet connection, against Base Sepolia.
 *
 * Two connectors, and no wallet-picker modal library: `baseAccount` for a Base
 * Account (passkey — no extension, no seed phrase, which is the shortest path
 * for someone opening this for the first time), and `injected` for whatever
 * browser wallet the visitor already has. Anything more is a dependency that
 * exists to render a grid of logos.
 *
 * `multiInjectedProviderDiscovery` stays on, unlike the docs' Next.js example:
 * that flag exists to stop EIP-6963 discovery from surfacing duplicates
 * alongside an explicitly configured wallet, and with only a generic `injected`
 * connector here, discovery is the thing that makes a visitor's actual wallet
 * appear at all.
 *
 * Storage is `localStorage`, not `cookieStorage` — this is a static SPA with no
 * server rendering, so there is no server that needs to read the connection
 * back, and `ssr: true` would make wagmi wait for a hydration pass that never
 * comes.
 */
import { createConfig, http } from "wagmi";
import { baseSepolia } from "wagmi/chains";
import { baseAccount, injected } from "wagmi/connectors";

/** An RPC override, for anyone rate-limited off the public endpoint. */
const RPC_URL = import.meta.env.VITE_BASE_SEPOLIA_RPC_URL as string | undefined;

export const CHAIN = baseSepolia;

export const config = createConfig({
  chains: [baseSepolia],
  connectors: [
    baseAccount({ appName: "Succession" }),
    injected({ shimDisconnect: true }),
  ],
  transports: {
    [baseSepolia.id]: http(RPC_URL || undefined),
  },
});

declare module "wagmi" {
  interface Register {
    config: typeof config;
  }
}

/** Basescan, for anything a judge should be able to open and read. */
export function explorerTx(hash: string): string {
  return `${CHAIN.blockExplorers.default.url}/tx/${hash}`;
}

export function explorerAddress(address: string): string {
  return `${CHAIN.blockExplorers.default.url}/address/${address}`;
}
