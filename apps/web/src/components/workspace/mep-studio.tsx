"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Droplets,
  Flame,
  Lightbulb,
  Wind,
  Zap,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { ArchitectureProject, MEPSystem, ServicePoint } from "@/features/project/types";

// ── Layer toggle ──────────────────────────────────────────────────────────────

const SYSTEM_META: Record<MEPSystem, { label: string; color: string; icon: React.ReactNode }> = {
  plumbing:   { label: "Plumbing",   color: "#1a6eb5", icon: <Droplets className="h-3.5 w-3.5" /> },
  electrical: { label: "Electrical", color: "#d97706", icon: <Zap className="h-3.5 w-3.5" /> },
  lighting:   { label: "Lighting",   color: "#ca8a04", icon: <Lightbulb className="h-3.5 w-3.5" /> },
  ac:         { label: "AC",         color: "#0891b2", icon: <Wind className="h-3.5 w-3.5" /> },
};

function LayerToggle({
  system,
  active,
  count,
  onToggle,
}: {
  system: MEPSystem;
  active: boolean;
  count: number;
  onToggle: () => void;
}) {
  const meta = SYSTEM_META[system];
  return (
    <button
      onClick={onToggle}
      className={cn(
        "flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-all",
        active
          ? "border-transparent text-white"
          : "border-border bg-card text-muted-foreground hover:bg-muted/60",
      )}
      style={active ? { backgroundColor: meta.color } : undefined}
    >
      {meta.icon}
      {meta.label}
      <span
        className={cn(
          "ml-0.5 rounded-full px-1 text-[10px] font-semibold",
          active ? "bg-white/25 text-white" : "bg-muted text-muted-foreground",
        )}
      >
        {count}
      </span>
    </button>
  );
}

// ── Point row ─────────────────────────────────────────────────────────────────

function PointRow({
  pt,
  roomName,
  selected,
  onSelect,
}: {
  pt: ServicePoint;
  roomName: string;
  selected: boolean;
  onSelect: () => void;
}) {
  const meta = SYSTEM_META[pt.system];
  return (
    <button
      onClick={onSelect}
      className={cn(
        "group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors",
        selected ? "bg-sky-50 ring-1 ring-sky-200" : "hover:bg-muted/60",
      )}
    >
      <span
        className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-white"
        style={{ backgroundColor: meta.color }}
      >
        {meta.icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium text-foreground">{pt.label || pt.kind}</span>
        <span className="block truncate text-[10px] text-muted-foreground">{roomName}</span>
      </span>
      {pt.user_override && (
        <Badge variant="outline" className="shrink-0 border-amber-300 bg-amber-50 text-amber-700 text-[9px] px-1 py-0">
          edited
        </Badge>
      )}
      {pt.needs_review ? (
        <AlertTriangle className="h-3 w-3 shrink-0 text-amber-500" />
      ) : (
        <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-500 opacity-0 group-hover:opacity-100" />
      )}
    </button>
  );
}

// ── Section accordion ─────────────────────────────────────────────────────────

function SystemSection({
  system,
  points,
  roomsById,
  selectedPointId,
  onSelectPoint,
}: {
  system: MEPSystem;
  points: ServicePoint[];
  roomsById: Map<string, string>;
  selectedPointId?: string | null;
  onSelectPoint: (id: string) => void;
}) {
  const [open, setOpen] = useState(true);
  const meta = SYSTEM_META[system];
  if (points.length === 0) return null;

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-1.5 py-1 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
      >
        {open ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span style={{ color: meta.color }}>{meta.label}</span>
        <span className="ml-auto text-[10px] font-normal">{points.length} pts</span>
      </button>
      {open && (
        <div className="mt-0.5 flex flex-col gap-0.5 pl-1">
          {points.map((pt) => (
            <PointRow
              key={pt.id}
              pt={pt}
              roomName={roomsById.get(pt.room_id) ?? pt.room_id}
              selected={pt.id === selectedPointId}
              onSelect={() => onSelectPoint(pt.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Confidence badge ──────────────────────────────────────────────────────────

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 85 ? "#10b981" : pct >= 70 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-1.5">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="w-7 text-right text-[10px] text-muted-foreground">{pct}%</span>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function MepStudio({
  project,
  activeLayers,
  onToggleLayer,
  selectedPointId,
  onSelectPoint,
  onGenerateMep,
  generating,
}: {
  project: ArchitectureProject;
  activeLayers: Set<MEPSystem>;
  onToggleLayer: (s: MEPSystem) => void;
  selectedPointId?: string | null;
  onSelectPoint?: (id: string) => void;
  onGenerateMep?: (systems: MEPSystem[]) => void;
  generating?: boolean;
}) {
  const mep = project.mep_plan;
  const roomsById = new Map(project.rooms.map((r) => [r.id, r.name]));

  const counts: Record<MEPSystem, number> = {
    plumbing:   mep.plumbing.points.length,
    electrical: mep.electrical.points.length,
    lighting:   mep.lighting.points.length,
    ac:         mep.ac.points.length,
  };

  const allWarnings = [
    ...mep.plumbing.warnings,
    ...mep.electrical.warnings,
    ...mep.lighting.warnings,
    ...mep.ac.warnings,
  ];

  const systemPts: Partial<Record<MEPSystem, ServicePoint[]>> = {
    plumbing:   mep.plumbing.points,
    electrical: mep.electrical.points,
    lighting:   mep.lighting.points,
    ac:         mep.ac.points,
  };

  if (!mep.generated) {
    return (
      <div className="flex flex-col items-center gap-3 py-8 text-center">
        <p className="text-sm text-muted-foreground">
          No MEP layers generated yet.
        </p>
        <Button
          size="sm"
          onClick={() => onGenerateMep?.(["plumbing", "electrical", "lighting", "ac"])}
          disabled={generating}
        >
          {generating ? "Generating…" : "Generate MEP Layers"}
        </Button>
        <p className="max-w-[220px] text-[11px] text-muted-foreground/70">
          Or type in chat: <em>"add plumbing, electrical, lighting, AC layers"</em>
        </p>
      </div>
    );
  }

  const avgConf =
    (mep.plumbing.confidence + mep.electrical.confidence + mep.lighting.confidence + mep.ac.confidence) / 4;

  return (
    <div className="flex flex-col gap-3 pb-2">
      {/* Stale warning */}
      {mep.stale && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
          <span>
            Rooms changed since MEP was generated — layers may be stale.{" "}
            <button
              className="font-semibold underline underline-offset-2"
              onClick={() => onGenerateMep?.(["plumbing", "electrical", "lighting", "ac"])}
            >
              Regenerate
            </button>
          </span>
        </div>
      )}

      {/* Advisory notice */}
      <div className="rounded-md border border-border/50 bg-muted/30 px-3 py-2 text-[11px] text-muted-foreground">
        Advisory placement only — not engineering-certified. Requires professional review.
      </div>

      {/* Confidence */}
      <div>
        <p className="mb-1 text-[11px] font-medium text-muted-foreground">Overall confidence</p>
        <ConfidenceBar value={avgConf} />
      </div>

      {/* Layer toggles */}
      <div>
        <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">Visible layers</p>
        <div className="flex flex-wrap gap-1.5">
          {(["plumbing", "electrical", "lighting", "ac"] as MEPSystem[]).map((s) => (
            <LayerToggle
              key={s}
              system={s}
              active={activeLayers.has(s)}
              count={counts[s]}
              onToggle={() => onToggleLayer(s)}
            />
          ))}
        </div>
      </div>

      {/* Points by system */}
      <div className="flex flex-col gap-1 divide-y divide-border/50">
        {(["plumbing", "electrical", "lighting", "ac"] as MEPSystem[]).map((s) => {
          const pts = (systemPts[s] ?? []).filter(() => activeLayers.has(s));
          if (pts.length === 0) return null;
          return (
            <div key={s} className="pt-1.5 first:pt-0">
              <SystemSection
                system={s}
                points={pts}
                roomsById={roomsById}
                selectedPointId={selectedPointId}
                onSelectPoint={(id) => onSelectPoint?.(id)}
              />
            </div>
          );
        })}
      </div>

      {/* Warnings */}
      {allWarnings.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-[11px] font-medium text-muted-foreground">Warnings</p>
          {allWarnings.map((w, i) => (
            <div
              key={i}
              className="flex items-start gap-1.5 text-[11px] text-amber-800"
            >
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-amber-500" />
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Regenerate */}
      <Button
        variant="outline"
        size="sm"
        className="w-full text-xs"
        onClick={() => onGenerateMep?.(["plumbing", "electrical", "lighting", "ac"])}
        disabled={generating}
      >
        {generating ? "Regenerating…" : "Regenerate All MEP Layers"}
      </Button>
    </div>
  );
}
