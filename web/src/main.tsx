import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// Set before the first paint, and before React mounts. The console's palette
// hangs off this attribute, and an effect alone would let a direct load of
// /app show the light ground for a frame. It cannot be an inline script in
// index.html: the deployed CSP is `script-src 'self'`.
if (window.location.pathname.startsWith("/app")) {
  document.documentElement.dataset.surface = "app";
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
