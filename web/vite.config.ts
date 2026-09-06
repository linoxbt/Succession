import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: true } },
  },
  build: {
    rollupOptions: {
      output: {
        // The wallet stack is by far the largest thing here and it changes on a
        // different clock to the app: splitting it out means a UI edit does not
        // invalidate 300 KB of vendor code in everyone's cache, and the two
        // chunks download in parallel rather than as one blocking file.
        //
        // It is still fetched on first load, because `WagmiProvider` wraps the
        // whole app so a connection survives navigation. Not shipping it at all
        // in recorded mode would mean mounting the provider tree conditionally
        // and remounting the app when a deployment appears — a bigger change
        // than the saving justifies while this is pre-deployment.
        // The wallet *SDKs* are deliberately absent from this list. wagmi loads
        // `@base-org/account`, `@walletconnect/ethereum-provider` and Reown's
        // AppKit through dynamic `import()` precisely so they cost nothing
        // until someone picks that connector. Naming them in a manualChunk
        // would undo that by pulling them into an eagerly preloaded file: with
        // `@coinbase` still matched here, installing Base Account's SDK took
        // this chunk from 273 KB to 1,013 KB, all of it on first paint, for a
        // popup most visitors never open.
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;

          // Top-level copies only. The wallet SDKs each vendor their own nested
          // `ox` — nine copies in total — and a pattern that matched
          // `/node_modules/ox/` anywhere caught all of them. Because
          // manualChunks overrides Rollup's own async placement, those nested
          // copies were hoisted out of the lazy SDK chunks and into this
          // eagerly preloaded one, which is what took it to 996 KB. Anything
          // reached through a nested node_modules belongs to a package that is
          // itself dynamically imported, so it stays where Rollup put it.
          if (id.split(/[\\/]node_modules[\\/]/).length - 1 !== 1) return undefined;

          // `ox` is deliberately not named here either. It is shared between
          // the app's own viem calls and the lazily loaded wallet SDKs, so
          // forcing the whole package into this chunk pulls in every module
          // those SDKs touch and eager-loads it. Left alone, Rollup splits it
          // and only the part the first paint actually needs arrives with it.
          if (/[\\/]node_modules[\\/](wagmi|viem|@wagmi|abitype)[\\/]/.test(id)) {
            return "wallet";
          }
          if (/[\\/]node_modules[\\/](react|react-dom|scheduler)[\\/]/.test(id)) {
            return "react";
          }
          return undefined;
        },
      },
    },
  },
});
