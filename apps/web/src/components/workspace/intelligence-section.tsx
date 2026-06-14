"use client";

import {
  Activity,
  ChevronDown,
  ChevronUp,
  Info,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { getIntelligence } from "@/features/api/client";
import type {
  AreaSummary,
  IntelligenceReport,
  SpatialCheck,
  VastuSuggestion,
} from "@/features/intelligence/types";
import { cn } from "@/lib/utils";

// ── Area Summary ──────────────────────────────────────────────────────────────

function AreaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between py-1 border-b border-border/40 last:border-b-0">
      <span className="text-[11px] text-muted-foreground">{label}</span>
      <span className="text-[11px] tabular-nums font-medium">{value}</span>
    </div>
  );
}

function AreaCard({ summary, unit }: { summary: AreaSummary; unit: string }) {
  const u2 = `${unit}²`;
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="px-3 py-2 bg-muted/40">
        <AreaRow label="Site area" value={`${summary.site_area.toLocaleString()} ${u2}`} />
        <AreaRow label="Built-up area" value={`${summary.built_up_area.toLocaleString()} ${u2}`} />
        <AreaRow label="Carpet area" value={`${summary.carpet_area.toLocaleString()} ${u2}`} />
        <AreaRow label="Open / setbacks" value={`${summary.circulation_area.toLocaleString()} ${u2}`} />
      </div>
      <div className="grid grid-cols-2 divide-x divide-border bg-muted/20">
        <div className="px-3 py-2 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">Coverage</p>
          <p className="text-sm font-semibold tabular-nums mt-0.5">
            {summary.coverage_ratio}
            <span className="text-[10px] font-normal text-muted-foreground">%</span>
          </p>
        </div>
        <div className="px-3 py-2 text-center">
          <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">Efficiency</p>
          <p className="text-sm font-semibold tabular-nums mt-0.5">
            {summary.floor_efficiency}
            <span className="text-[10px] font-normal text-muted-foreground">%</span>
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Spatial Checks ────────────────────────────────────────────────────────────

const CHECK_ICON = {
  info:    { Icon: Info,          cls: "text-sky-500" },
  warning: { Icon: TriangleAlert, cls: "text-amber-500" },
  error:   { Icon: XCircle,       cls: "text-red-500" },
} as const;

function CheckItem({ check }: { check: SpatialCheck | VastuSuggestion }) {
  const { Icon, cls } = CHECK_ICON[check.severity];
  return (
    <li className="flex items-start gap-2 rounded-lg border border-border/60 bg-muted/20 px-3 py-2">
      <Icon className={cn("mt-0.5 size-3.5 shrink-0", cls)} />
      <p className="text-[11px] leading-[1.45] text-foreground/80">{check.message}</p>
    </li>
  );
}

// ── Vastu Section ─────────────────────────────────────────────────────────────

function VastuToggle({
  enabled,
  onToggle,
}: {
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "flex w-full items-center justify-between rounded-lg border px-3 py-2 transition-colors",
        enabled
          ? "border-amber-200 bg-amber-50/60 text-amber-800"
          : "border-border bg-muted/30 text-muted-foreground hover:bg-muted/50",
      )}
    >
      <span className="flex items-center gap-2">
        <span className="text-base leading-none">🪔</span>
        <span className="text-xs font-medium">Vastu Shastra</span>
      </span>
      <span className="text-[10px]">{enabled ? "On" : "Off"}</span>
    </button>
  );
}

// ── Main Section ──────────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="flex flex-col gap-2 animate-pulse">
      <div className="h-24 rounded-lg bg-muted/60" />
      <div className="h-12 rounded-lg bg-muted/60" />
    </div>
  );
}

function EmptyChecks() {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-border bg-muted/30 px-3 py-2.5">
      <Activity className="size-3.5 text-muted-foreground shrink-0" />
      <p className="text-[11px] leading-4 text-muted-foreground">
        No spatial issues detected — the design looks healthy.
      </p>
    </div>
  );
}

export function IntelligenceSection({
  projectId,
  unit,
}: {
  projectId: string | null;
  unit: string;
}) {
  const [report, setReport]       = useState<IntelligenceReport | null>(null);
  const [busy, setBusy]           = useState(false);
  const [vastuOn, setVastuOn]     = useState(false);
  const [showAll, setShowAll]     = useState(false);
  const abortRef                  = useRef<AbortController | null>(null);

  const load = useCallback(
    (id: string, vastu: boolean) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      setBusy(true);
      getIntelligence(id, vastu, ctrl.signal)
        .then((r) => { setReport(r); setBusy(false); })
        .catch(() => { if (!ctrl.signal.aborted) setBusy(false); });
    },
    [],
  );

  useEffect(() => {
    if (projectId) load(projectId, vastuOn);
    else setReport(null);
  }, [projectId, vastuOn, load]);

  if (!projectId) {
    return (
      <p className="text-[11px] leading-4 text-muted-foreground/70">
        Generate a design to see area analysis, quality checks, and Vastu
        suggestions.
      </p>
    );
  }

  if (busy && !report) return <LoadingState />;

  const checks       = report?.spatial_checks ?? [];
  const vastuList    = report?.vastu_suggestions ?? [];
  const PREVIEW_MAX  = 3;
  const visible      = showAll ? checks : checks.slice(0, PREVIEW_MAX);

  return (
    <div className="flex flex-col gap-3">
      {/* Area summary */}
      {report && (
        <AreaCard summary={report.area_summary} unit={unit} />
      )}

      {/* Spatial checks */}
      <div className="flex flex-col gap-1.5">
        <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
          Design Quality
        </p>
        {checks.length === 0 && !busy ? (
          <EmptyChecks />
        ) : (
          <ul className="flex flex-col gap-1.5">
            {visible.map((c, i) => (
              <CheckItem key={`${c.rule_id}-${i}`} check={c} />
            ))}
          </ul>
        )}
        {checks.length > PREVIEW_MAX && (
          <button
            type="button"
            onClick={() => setShowAll((v) => !v)}
            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
          >
            {showAll ? (
              <><ChevronUp className="size-3" /> Show fewer</>
            ) : (
              <><ChevronDown className="size-3" /> {checks.length - PREVIEW_MAX} more</>
            )}
          </button>
        )}
      </div>

      {/* Vastu toggle + suggestions */}
      <div className="flex flex-col gap-1.5">
        <VastuToggle enabled={vastuOn} onToggle={() => setVastuOn((v) => !v)} />
        {vastuOn && vastuList.length > 0 && (
          <ul className="flex flex-col gap-1.5 mt-0.5">
            {vastuList.map((s, i) => (
              <CheckItem key={`${s.rule_id}-${i}`} check={s} />
            ))}
          </ul>
        )}
        {vastuOn && vastuList.length === 0 && !busy && (
          <p className="text-[11px] text-muted-foreground px-1">
            No Vastu conflicts detected.
          </p>
        )}
      </div>
    </div>
  );
}
