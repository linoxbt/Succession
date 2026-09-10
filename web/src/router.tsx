import { useCallback, useEffect, useMemo, useState } from "react";

export type AppView = "dashboard" | "guide" | "docs";
export type Route = { kind: "landing" } | { kind: "app"; view: AppView };

const SEGMENTS: Record<Exclude<AppView, "dashboard">, string> = {
  guide: "guide",
  docs: "docs",
};

export function parse(pathname: string): Route {
  if (!pathname.startsWith("/app")) return { kind: "landing" };
  const segment = pathname.slice(4).replace(/^\/+|\/+$/g, "").split("/")[0];
  if (segment === "guide") return { kind: "app", view: "guide" };
  if (segment === "docs") return { kind: "app", view: "docs" };
  return { kind: "app", view: "dashboard" };
}

export function pathOf(route: Route): string {
  if (route.kind === "landing") return "/";
  return route.view === "dashboard" ? "/app" : `/app/${SEGMENTS[route.view]}`;
}

export const to = {
  landing: (): Route => ({ kind: "landing" }),
  view: (view: AppView): Route => ({ kind: "app", view }),
};

export function useNavigation() {
  const [href, setHref] = useState(() => window.location.pathname);
  useEffect(() => {
    const onPop = () => setHref(window.location.pathname);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  const navigate = useCallback((next: Route) => {
    const path = pathOf(next);
    if (path === window.location.pathname) return;
    window.history.pushState({}, "", path);
    setHref(path);
  }, []);
  const route = useMemo(() => parse(href), [href]);
  return { route, navigate };
}
