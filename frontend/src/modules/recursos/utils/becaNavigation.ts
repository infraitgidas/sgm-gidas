type BecarioOrigin = {
  pathname: string;
  search: string;
  hash: string;
  state?: unknown;
};

// El retorno pertenece al detalle del becario; no acepta destinos externos.
export function getBecaNavigationState(state: unknown): { becarioReturnTo: BecarioOrigin } | undefined {
  if (!state || typeof state !== "object" || !("becarioReturnTo" in state)) return undefined;
  const origin = state.becarioReturnTo;
  if (!origin || typeof origin !== "object" || !("pathname" in origin) ||
    typeof origin.pathname !== "string" || !/^\/personal\/becario\/[1-9]\d*$/.test(origin.pathname)) return undefined;
  return { becarioReturnTo: {
    pathname: origin.pathname,
    search: "search" in origin && typeof origin.search === "string" && origin.search.startsWith("?") ? origin.search : "",
    hash: "hash" in origin && typeof origin.hash === "string" && origin.hash.startsWith("#") ? origin.hash : "",
    state: "state" in origin ? origin.state : undefined,
  } };
}
