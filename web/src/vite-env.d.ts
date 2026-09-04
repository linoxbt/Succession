/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Override the public Base Sepolia RPC, for anyone it rate-limits. */
  readonly VITE_BASE_SEPOLIA_RPC_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
