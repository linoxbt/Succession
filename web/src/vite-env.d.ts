/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Override the public Base Sepolia RPC, for anyone it rate-limits. */
  readonly VITE_BASE_SEPOLIA_RPC_URL?: string;
  /** WalletConnect / Reown project id. The connector is omitted without it. */
  readonly VITE_REOWN_PROJECT_ID?: string;
  /** `mock` builds the console against local fixtures and makes no network
   *  call. Anything else, including unset, uses the real service. */
  readonly VITE_SERVICE?: "mock" | "http";
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
