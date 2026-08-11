"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, api } from "./api";
import type { User } from "./types";

/** Polling do salao/fila: intervalo curto o suficiente para o staff confiar na tela. */
export function usePolling<T>(loader: () => Promise<T>, intervalMs = 7000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const refresh = useCallback(async () => {
    try {
      const result = await loaderRef.current();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao carregar dados.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const tick = () => {
      if (active) void refresh();
    };
    tick();
    const timer = window.setInterval(tick, intervalMs);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [refresh, intervalMs]);

  return { data, error, loading, refresh };
}

export function useSession() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .get<User>("/auth/me")
      .then((result) => active && setUser(result))
      .catch((err) => {
        if (active && !(err instanceof ApiError && err.status === 401)) {
          console.error(err);
        }
      })
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  return { user, loading };
}
