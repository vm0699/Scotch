"use client";

import { useBackendStatus } from "@/features/api/use-backend-status";
import { cn } from "@/lib/utils";

const STATUS_STYLES = {
  checking: { dot: "bg-muted-foreground/40", label: "Checking backend…" },
  online: { dot: "bg-emerald-500", label: "Backend online" },
  offline: { dot: "bg-red-500", label: "Backend offline" },
} as const;

export function BackendStatusIndicator() {
  const status = useBackendStatus();
  const { dot, label } = STATUS_STYLES[status.state];
  const detail =
    status.state === "online"
      ? `${status.health.app} v${status.health.version}`
      : status.state === "offline"
        ? "Start it with: npm run dev:api"
        : undefined;

  return (
    <span className="flex items-center gap-2" title={detail}>
      <span className={cn("size-2 rounded-full", dot)} />
      <span className="hidden text-xs text-muted-foreground sm:block">
        {label}
      </span>
    </span>
  );
}
