/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Optional API origin. Empty uses the deployment's same-origin proxy. */
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
