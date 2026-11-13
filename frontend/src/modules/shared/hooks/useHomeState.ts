import { useCallback, useEffect, useRef, useState, type Dispatch, type EffectCallback, type SetStateAction } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { homeStateKey, homeStorage, readHomeValue, writeHomeValue, type HomeValueOptions } from "@/modules/shared/utils/homeState";

/** Solo controles de consulta; nunca filas, credenciales, borradores ni acciones pendientes. */
export function useHomeState<T = undefined>(field: string, initial?: T,
  options: HomeValueOptions & { scope?: string } = {}): [T, Dispatch<SetStateAction<T>>] {
  const { user } = useAuth();
  const location = useLocation();
  const memoria = location.state?.memoriaFilter;
  const scope = JSON.stringify([location.pathname, location.search, options.scope ?? "",
    memoria ? [memoria.memoriaId, memoria.versionId, memoria.sectionKey] : null]);
  const key = homeStateKey(user?.id, scope, field);
  const read = () => readHomeValue(homeStorage(), key, field, initial as T, options);
  const [snapshot, setSnapshot] = useState(() => ({ key, value: read() }));
  const current = useRef(snapshot);
  if (current.current.key !== key) current.current = { key, value: read() };
  const value = current.current.value;
  const setValue = useCallback<Dispatch<SetStateAction<T>>>((action) => {
    // Un callback perteneciente al usuario/ruta anterior no puede escribir en el nuevo contexto.
    if (current.current.key !== key) return;
    const next = typeof action === "function"
      ? (action as (previous: T) => T)(current.current.value) : action;
    current.current = { key, value: next };
    writeHomeValue(homeStorage(), key, next);
    setSnapshot(current.current);
  }, [key]);
  return [value, setValue];
}

/** Reinicia la página solo si cambian los filtros, sin borrar la página recuperada al montar. */
export function useHomeFilterEffect(effect: EffectCallback, dependencies: readonly unknown[]): void {
  const signature = JSON.stringify(dependencies);
  const previous = useRef(signature);
  useEffect(() => {
    if (previous.current === signature) return;
    previous.current = signature;
    return effect();
  }, [signature]);
}
