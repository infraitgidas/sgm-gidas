import type { Location } from "react-router-dom";

type CatalogOrigin = Pick<Location, "pathname" | "search" | "hash"> & { state?: unknown };

function withoutMessages(state: unknown): Record<string, unknown> | undefined {
  if (!state || typeof state !== "object" || Array.isArray(state)) return undefined;
  const { successMessage, catalogosReturnTo, ...context } = state as Record<string, unknown>;
  void successMessage;
  void catalogosReturnTo;
  return Object.keys(context).length ? context : undefined;
}

export function getCatalogReturn(state: unknown): CatalogOrigin {
  const fallback = { pathname: "/inicio", search: "", hash: "" };
  if (!state || typeof state !== "object" || !("catalogosReturnTo" in state)) return fallback;
  const origin = state.catalogosReturnTo;
  if (!origin || typeof origin !== "object" || !("pathname" in origin)) return fallback;
  const pathname = origin.pathname;
  if (typeof pathname !== "string" || !pathname.startsWith("/") || pathname.startsWith("//")
    || /[\\\s?#]/.test(pathname)) return fallback;
  try {
    const decoded = decodeURIComponent(pathname);
    if (/[\\\s]/.test(decoded) || decoded.startsWith("//")
      || new URL(pathname, "https://gidas.local").pathname !== pathname
      || /^\/catalogos(?:\/|$)/i.test(decoded)) return fallback;
  } catch { return fallback; }
  return {
    pathname,
    search: "search" in origin && typeof origin.search === "string" && origin.search.startsWith("?") ? origin.search : "",
    hash: "hash" in origin && typeof origin.hash === "string" && origin.hash.startsWith("#") ? origin.hash : "",
    state: withoutMessages("state" in origin ? origin.state : undefined),
  };
}

export function buildCatalogNavigationState(location: Pick<Location, "pathname" | "search" | "hash" | "state">) {
  const origin = /^\/catalogos\/?$/.test(location.pathname)
    ? getCatalogReturn(location.state)
    : getCatalogReturn({ catalogosReturnTo: location });
  return { catalogosReturnTo: origin };
}
