import React, { lazy, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { Landing } from "./landing/Landing";
import { to, useNavigation } from "./router";
import { CursorProvider, SmoothScroll } from "./motion";
import Cursor from "./chrome/Cursor";
import Preloader from "./chrome/Preloader";
import "./index.css";

const App = lazy(() => import('./App'));

function Entry() {
  const { route, navigate } = useNavigation();
  if (route.kind !== 'landing') return <Suspense fallback={<p className="gutter py-12" role="status">Loading the application…</p>}><App /></Suspense>;
  return <SmoothScroll><CursorProvider><Cursor /><Preloader onDone={() => undefined} />
    <Landing onEnter={() => navigate(to.view('overview'))} onDocs={() => navigate(to.view('docs'))} />
  </CursorProvider></SmoothScroll>;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Entry />
  </React.StrictMode>,
);
