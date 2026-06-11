"use client";

import { StatusBadge } from "@/components/layout/status-badge";
import { API_BASE_URL } from "@/features/api/client";
import { useBackendStatus } from "@/features/api/use-backend-status";

export function BackendStatusCard() {
  const status = useBackendStatus();

  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border bg-card px-4 py-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <div>
        <div className="text-sm font-medium tracking-tight">Local engine</div>
        <div className="mt-0.5 font-mono text-xs text-muted-foreground">
          {API_BASE_URL}
        </div>
      </div>
      {status.state === "online" && (
        <StatusBadge variant="ok">v{status.health.version} · online</StatusBadge>
      )}
      {status.state === "offline" && (
        <StatusBadge variant="error">offline</StatusBadge>
      )}
      {status.state === "checking" && (
        <StatusBadge variant="info">checking…</StatusBadge>
      )}
    </div>
  );
}
