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
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (/[\\/]node_modules[\\/](wagmi|viem|@wagmi|@coinbase|ox|abitype)/.test(id)) {
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
