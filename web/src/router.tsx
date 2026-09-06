/**
 * Routing.
 *
 * Hand-rolled on the History API rather than pulled from a library. There are
 * eight routes and one parameter; a router dependency would be larger than the
 * thing it replaced, and the console already ships wagmi and viem.
 *
 * What this buys, which in-memory view state could not: a listing has an
 * address. `/app/listing/listing-672` can be sent to someone, opened in a new
 * tab, or reached with the back button, and a filtered market survives a
 * reload. Netlify's SPA catch-all already serves every path to the same shell,
 * so no server change is needed.
 *
 * Search state lives in the query string and is written with `replaceState`,
 * not `pushState`. Typing four characters into a filter should not put four
 * entries in the back stack.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

export type AppView =
  | "overview"
  | "market"
  | "listing"
  | "sell"
  | "claim"
  | "walkthrough"
  | "docs";

export type Route =
  | { kind: "landing" }
  | { kind: "app"; view: AppView; listingId: string | null };

/** Path segment for each view. `overview` is the bare `/app`. */
const SEGMENTS: Record<Exclude<AppView, "overview" | "listing">, string> = {
  market: "marketplace",
  sell: "sell",
  claim: "claim",
  walkthrough: "walkthrough",
  docs: "docs",
};

const BY_SEGMENT = new Map<string, AppView>(
  Object.entries(SEGMENTS).map(([view, segment]) => [segment, view as AppView]),
);

export function parse(pathname: string): Route {
  if (!pathname.startsWith("/app")) return { kind: "landing" };

  const rest = pathname.slice("/app".length).replace(/^\/+|\/+$/g, "");
  if (rest === "") return { kind: "app", view: "overview", listingId: null };

  // `rest` is non-empty here, so split always yields a first element, but the
  // compiler cannot see that under noUncheckedIndexedAccess.
  const [head = "", ...tail] = rest.split("/");

  if (head === "listing") {
    // A listing route without an id is not a listing route. Falling through to
    // the market is better than rendering a detail page with nothing in it.
    const id = tail.join("/");
    return id
      ? { kind: "app", view: "listing", listingId: decodeURIComponent(id) }
      : { kind: "app", view: "market", listingId: null };
  }

  const view = BY_SEGMENT.get(head);
  // An unknown path under /app lands on the overview rather than on a 404. The
  // console has no not-found screen and inventing one for a mistyped URL would
  // be more surface than the case deserves.
  return { kind: "app", view: view ?? "overview", listingId: null };
}

export function pathOf(route: Route): string {
  if (route.kind === "landing") return "/";
  if (route.view === "overview") return "/app";
  if (route.view === "listing") {
    return route.listingId
      ? `/app/listing/${encodeURIComponent(route.listingId)}`
      : "/app/marketplace";
  }
  return `/app/${SEGMENTS[route.view as keyof typeof SEGMENTS]}`;
}

/** Shorthands, so callers do not assemble route objects by hand. */
export const to = {
  landing: (): Route => ({ kind: "landing" }),
  view: (view: AppView): Route => ({ kind: "app", view, listingId: null }),
  listing: (listingId: string): Route => ({
    kind: "app",
    view: "listing",
    listingId,
  }),
};

export interface Navigation {
  route: Route;
  /** Push a new entry, or replace the current one. */
  navigate: (next: Route, options?: { replace?: boolean }) => void;
  /** The current query string, re-read on every navigation. */
  query: URLSearchParams;
  /**
   * Write the query string without touching the back stack. Keys set to null
   * or an empty string are removed, so a cleared filter leaves no `?f=` behind.
   */
  setQuery: (patch: Record<string, string | null>) => void;
}

export function useNavigation(): Navigation {
  const [href, setHref] = useState(
    () => window.location.pathname + window.location.search,
  );

  useEffect(() => {
    const onPop = () => setHref(window.location.pathname + window.location.search);
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const navigate = useCallback((next: Route, options?: { replace?: boolean }) => {
    const path = pathOf(next);
    // Navigating to where you already are should not stack a duplicate entry,
    // which otherwise makes the back button appear broken.
    if (path === window.location.pathname && !options?.replace) return;
    if (options?.replace) window.history.replaceState({}, "", path);
    else window.history.pushState({}, "", path);
    setHref(path);
  }, []);

  const setQuery = useCallback((patch: Record<string, string | null>) => {
    const params = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === "") params.delete(key);
      else params.set(key, value);
    }
    const search = params.toString();
    const path = window.location.pathname + (search ? `?${search}` : "");
    window.history.replaceState({}, "", path);
    setHref(path);
  }, []);

  const [pathname, search] = useMemo(() => {
    const i = href.indexOf("?");
    return i === -1 ? [href, ""] : [href.slice(0, i), href.slice(i + 1)];
  }, [href]);

  const route = useMemo(() => parse(pathname), [pathname]);
  const query = useMemo(() => new URLSearchParams(search), [search]);

  return { route, navigate, query, setQuery };
}
