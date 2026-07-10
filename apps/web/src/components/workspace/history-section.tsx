"use client";

import {
  History,
  Layers,
  Pencil,
  RefreshCw,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { listVersions, restoreVersion } from "@/features/api/client";
import type {
  ProjectVersionMeta,
  StoredProject,
  VersionChangeType,
} from "@/features/api/client";
import { cn } from "@/lib/utils";

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.round(diff / 1000);
  if (s < 60) return "just now";
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

const CHANGE_TYPE_META: Record<
  VersionChangeType,
  { icon: React.ComponentType<{ className?: string }>; label: string; color: string }
> = {
  generate: { icon: Sparkles, label: "Generate", color: "text-violet-500" },
  regenerate: { icon: RefreshCw, label: "Regenerate", color: "text-blue-500" },
  edit: { icon: Pencil, label: "Edit", color: "text-amber-500" },
  option: { icon: Layers, label: "Option", color: "text-teal-500" },
  restore: { icon: RotateCcw, label: "Restore", color: "text-rose-500" },
  sync: { icon: RefreshCw, label: "Sync", color: "text-sky-500" },
};

function VersionRow({
  meta,
  onRestore,
}: {
  meta: ProjectVersionMeta;
  onRestore: (versionId: string) => Promise<void>;
}) {
  const [confirmPending, setConfirmPending] = useState(false);
  const [busy, setBusy] = useState(false);
  const { icon: Icon, label, color } = CHANGE_TYPE_META[meta.change_type];

  async function handleRestoreClick() {
    if (!confirmPending) {
      setConfirmPending(true);
      setTimeout(() => setConfirmPending(false), 3000);
      return;
    }
    setBusy(true);
    try {
      await onRestore(meta.version_id);
    } finally {
      setBusy(false);
      setConfirmPending(false);
    }
  }

  return (
    <div className="flex items-start gap-3 rounded-lg border border-border bg-card px-3 py-2.5">
      {/* Thumbnail */}
      {meta.thumbnail ? (
        <div
          className="size-10 shrink-0 overflow-hidden rounded border border-border/60"
          dangerouslySetInnerHTML={{ __html: meta.thumbnail }}
        />
      ) : (
        <div className="size-10 shrink-0 rounded border border-border/60 bg-muted" />
      )}

      {/* Info */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <Icon className={cn("size-3 shrink-0", color)} />
          <span className={cn("text-[10px] font-semibold uppercase tracking-wide", color)}>
            {label}
          </span>
          <span className="ml-auto text-[10px] text-muted-foreground/60">
            {relativeTime(meta.created_at)}
          </span>
        </div>
        <p className="mt-0.5 truncate text-[11px] leading-4 text-foreground/80">
          {meta.summary}
        </p>
        <p className="mt-0.5 text-[10px] text-muted-foreground/60">
          {meta.room_count} rooms · {Math.round(meta.total_area)} ft²
        </p>
      </div>

      {/* Restore */}
      <Button
        variant="ghost"
        size="sm"
        disabled={busy}
        onClick={() => void handleRestoreClick()}
        className={cn(
          "h-auto shrink-0 self-center px-2 py-1 text-[10px]",
          confirmPending
            ? "border border-rose-400 text-rose-600 hover:bg-rose-50"
            : "text-muted-foreground hover:text-foreground",
        )}
      >
        {busy ? (
          <RefreshCw className="size-3 animate-spin" />
        ) : confirmPending ? (
          "Confirm"
        ) : (
          "Restore"
        )}
      </Button>
    </div>
  );
}

export function HistorySection({
  projectId,
  historyKey,
  onRestored,
}: {
  projectId: string | null;
  historyKey: number;
  onRestored: (stored: StoredProject) => void;
}) {
  const [versions, setVersions] = useState<ProjectVersionMeta[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    setLoading(true);
    listVersions(projectId)
      .then((v) => { if (!cancelled) setVersions(v); })
      .catch(() => {})
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [projectId, historyKey]);

  const handleRestore = useCallback(
    async (versionId: string) => {
      if (!projectId) return;
      const stored = await restoreVersion(projectId, versionId);
      onRestored(stored);
    },
    [projectId, onRestored],
  );

  if (!projectId) {
    return (
      <div className="flex items-center gap-2.5 rounded-lg border border-border bg-muted/40 px-3 py-2.5">
        <History className="size-4 text-muted-foreground" />
        <p className="text-xs leading-5 text-muted-foreground">
          Save a project to track version history.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col gap-2">
        {[0, 1].map((i) => (
          <div
            key={i}
            className="flex items-start gap-3 rounded-lg border border-border px-3 py-2.5"
            aria-hidden
          >
            <div className="size-10 rounded border border-border/60 bg-muted" />
            <div className="flex-1 space-y-1.5">
              <div className="h-3 w-16 rounded bg-muted" />
              <div className="h-3 w-32 rounded bg-muted" />
              <div className="h-3 w-20 rounded bg-muted" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <p className="text-[11px] leading-4 text-muted-foreground/70">
        No versions yet — generate or edit to start tracking history.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {versions.map((v) => (
        <VersionRow key={v.version_id} meta={v} onRestore={handleRestore} />
      ))}
    </div>
  );
}
