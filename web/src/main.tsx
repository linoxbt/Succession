import React from "react";
import ReactDOM from "react-dom/client";

// Declared before render: the reveal styles are scoped to `.js`, so a page
// whose scripts fail shows everything instead of nothing.
document.documentElement.classList.add("js");
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
