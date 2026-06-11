"use client";

import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "./client";

const POLL_INTERVAL_MS = 15_000;

export type BackendStatus =
  | { state: "checking" }
  | { state: "online"; health: HealthResponse }
  | { state: "offline" };

export function useBackendStatus(): BackendStatus {
  const [status, setStatus] = useState<BackendStatus>({ state: "checking" });

  useEffect(() => {
    const controller = new AbortController();

    async function check() {
      try {
        const health = await getHealth(controller.signal);
        setStatus({ state: "online", health });
      } catch {
        if (!controller.signal.aborted) {
          setStatus({ state: "offline" });
        }
      }
    }

    void check();
    const timer = setInterval(check, POLL_INTERVAL_MS);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, []);

  return status;
}
