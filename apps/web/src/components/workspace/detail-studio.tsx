"use client";

import { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  AlertTriangle,
  RefreshCw,
  Trash2,
} from "lucide-react";

import type { ArchitectureProject, DetailDrawing, DetailType } from "@/features/project/types";
import { API_BASE_URL } from "@/features/api/client";

// ── Sub-components ────────────────────────────────────────────────────────────

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 85 ? "text-emerald-600" : pct >= 70 ? "text-amber-600" : "text-red-500";
  return <span className={`text-[10px] font-medium tabular-nums ${color}`}>{pct}%</span>;
}

function StaleBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-sm bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200">
      <AlertTriangle size={8} />
      Stale
    </span>
  );
}

function ReviewBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-sm bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700 border border-blue-200">
      Review required
    </span>
  );
}

const DETAIL_TYPE_LABELS: Record<DetailType | string, string> = {
  toilet: "WC / Toilet",
  kitchen: "Kitchen Layout",
  door_window: "Door / Window",
  wall_section: "Wall Section",
  tile_layout: "Tile Layout",
  stair: "Stair Section",
  custom: "Custom",
};

const DETAIL_VIEW_LABELS: Record<string, string> = {
  plan: "Plan",
  section: "Section",
  elevation: "Elevation",
};

// ── Generate prompt panel ─────────────────────────────────────────────────────

function GenerateForm({
  project,
  onGenerate,
  generating,
}: {
  project: ArchitectureProject;
  onGenerate: (type: DetailType, sourceId: string) => void;
  generating: boolean;
}) {
  const [detailType, setDetailType] = useState<DetailType>("toilet");
  const [sourceId, setSourceId] = useState("");

  // Auto-populate source ID based on type
  const handleTypeChange = (type: DetailType) => {
    setDetailType(type);
    const typeToRoomType: Record<string, string[]> = {
      toilet: ["bathroom", "master_bathroom", "toilet"],
      kitchen: ["kitchen"],
      wall_section: [],
      tile_layout: [],
    };
    const eligible = typeToRoomType[type] ?? [];
    let room = null;
    if (type === "door_window") {
      setSourceId(project.doors[0]?.id ?? project.windows[0]?.id ?? "");
      return;
    }
    if (type === "stair") {
      setSourceId(project.stairs[0]?.id ?? "");
      return;
    }
    if (eligible.length > 0) {
      room = project.rooms.find((r) => eligible.includes(r.type));
    } else {
      room = project.rooms.find((r) => r.type !== "stair" && r.type !== "parking");
    }
    setSourceId(room?.id ?? "");
  };

  const sourceOptions: Array<{ id: string; label: string }> = [];
  if (detailType === "door_window") {
    project.doors.forEach((d) => sourceOptions.push({ id: d.id, label: `Door — ${d.id}` }));
    project.windows.forEach((w) => sourceOptions.push({ id: w.id, label: `Window — ${w.id}` }));
  } else if (detailType === "stair") {
    project.stairs.forEach((s) => sourceOptions.push({ id: s.id, label: `Stair — ${s.id}` }));
  } else {
    const eligible: Record<string, string[]> = {
      toilet: ["bathroom", "master_bathroom", "toilet"],
      kitchen: ["kitchen"],
      wall_section: [],
      tile_layout: [],
    };
    const types = eligible[detailType] ?? [];
    project.rooms
      .filter((r) => types.length === 0 || types.includes(r.type))
      .forEach((r) => sourceOptions.push({ id: r.id, label: `${r.name} (${r.type})` }));
  }

  return (
    <div className="rounded-lg border border-border/60 bg-muted/30 p-3 space-y-3">
      <div className="text-xs font-medium text-foreground/70 uppercase tracking-wide">Generate New Detail</div>
      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">Detail type</label>
        <select
          className="w-full rounded-md border border-border/60 bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary/40"
          value={detailType}
          onChange={(e) => handleTypeChange(e.target.value as DetailType)}
        >
          {Object.entries(DETAIL_TYPE_LABELS).filter(([k]) => k !== "custom").map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
      </div>
      <div className="space-y-2">
        <label className="text-xs text-muted-foreground">Source object</label>
        {sourceOptions.length > 0 ? (
          <select
            className="w-full rounded-md border border-border/60 bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary/40"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
          >
            {sourceOptions.map((o) => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
        ) : (
          <input
            className="w-full rounded-md border border-border/60 bg-background px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary/40"
            placeholder="Room / object ID"
            value={sourceId}
            onChange={(e) => setSourceId(e.target.value)}
          />
        )}
      </div>
      <button
        className="w-full rounded-md bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        disabled={generating || !sourceId}
        onClick={() => onGenerate(detailType, sourceId)}
      >
        {generating ? "Generating…" : "Generate Detail"}
      </button>
    </div>
  );
}

// ── Detail card ───────────────────────────────────────────────────────────────

function DetailCard({
  drawing,
  projectId,
  onDelete,
  onRegenerate,
}: {
  drawing: DetailDrawing;
  projectId: string;
  onDelete: (id: string) => void;
  onRegenerate: (type: DetailType, sourceId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const svgUrl = `${API_BASE_URL}/projects/${projectId}/details/${drawing.id}/svg`;

  return (
    <div className={`rounded-lg border bg-card transition-colors ${drawing.stale ? "border-amber-300" : "border-border/60"}`}>
      {/* Header */}
      <button
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
        onClick={() => setExpanded((v) => !v)}
      >
        <FileText size={13} className="shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-medium truncate">{drawing.name}</span>
            {drawing.stale && <StaleBadge />}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-muted-foreground">
              {DETAIL_TYPE_LABELS[drawing.detail_type] ?? drawing.detail_type} · {DETAIL_VIEW_LABELS[drawing.view] ?? drawing.view} · {drawing.scale}
            </span>
            <ConfidenceBadge value={drawing.confidence} />
            {drawing.needs_review && <ReviewBadge />}
          </div>
        </div>
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      {/* Expanded body */}
      {expanded && (
        <div className="border-t border-border/40 px-3 pb-3 pt-2.5 space-y-3">
          {drawing.stale && (
            <div className="flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 p-2 text-[11px] text-amber-700">
              <AlertTriangle size={11} className="mt-0.5 shrink-0" />
              <span>Source object was modified — regenerate to update this detail.</span>
              <button
                className="ml-auto shrink-0 text-amber-700 hover:text-amber-900"
                onClick={() => onRegenerate(drawing.detail_type, drawing.source_object_ids[0] ?? "")}
              >
                <RefreshCw size={11} />
              </button>
            </div>
          )}

          {/* SVG preview placeholder — actual rendering via img src */}
          <div className="rounded-md border border-border/40 bg-muted/20 overflow-hidden">
            <img
              src={svgUrl}
              alt={drawing.name}
              className="w-full h-auto"
              style={{ maxHeight: 200, objectFit: "contain" }}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          </div>

          {/* Annotations */}
          {drawing.annotations.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-medium uppercase tracking-wide text-muted-foreground">Notes</div>
              <ul className="space-y-0.5">
                {drawing.annotations.map((note, i) => (
                  <li key={i} className="text-[10px] text-muted-foreground flex gap-1.5">
                    <span className="shrink-0 mt-0.5 text-amber-500">⚠</span>
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2">
            <a
              href={svgUrl}
              download={`${drawing.id}.svg`}
              className="flex items-center gap-1.5 rounded-md border border-border/60 px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              <Download size={10} />
              Export SVG
            </a>
            <button
              className="ml-auto flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-red-500 hover:text-red-700 hover:bg-red-50 transition-colors"
              onClick={() => onDelete(drawing.id)}
            >
              <Trash2 size={10} />
              Remove
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export interface DetailStudioProps {
  project: ArchitectureProject;
  projectId?: string;
  onGenerateDetail: (type: DetailType, sourceId: string) => void;
  onDeleteDetail: (id: string) => void;
  generating: boolean;
}

export function DetailStudio({
  project,
  projectId,
  onGenerateDetail,
  onDeleteDetail,
  generating,
}: DetailStudioProps) {
  const drawings = project.detail_drawings ?? [];
  const staleCount = drawings.filter((d) => d.stale).length;

  return (
    <div className="space-y-3">
      <GenerateForm project={project} onGenerate={onGenerateDetail} generating={generating} />

      {staleCount > 0 && (
        <div className="flex items-center gap-1.5 rounded-md bg-amber-50 border border-amber-200 px-2.5 py-2 text-[11px] text-amber-700">
          <AlertTriangle size={11} />
          {staleCount} detail{staleCount > 1 ? "s" : ""} stale — plan changed after generation
        </div>
      )}

      {drawings.length === 0 ? (
        <div className="rounded-lg border border-border/40 border-dashed px-4 py-6 text-center text-xs text-muted-foreground">
          <FileText size={20} className="mx-auto mb-2 opacity-30" />
          <p className="font-medium text-foreground/60">No detail drawings yet</p>
          <p className="mt-1">Generate a toilet, kitchen, wall section, or tile layout above.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {drawings.map((d) => (
            <DetailCard
              key={d.id}
              drawing={d}
              projectId={projectId ?? ""}
              onDelete={onDeleteDetail}
              onRegenerate={onGenerateDetail}
            />
          ))}
        </div>
      )}

      {drawings.length > 0 && (
        <p className="text-[10px] text-muted-foreground text-center">
          Advisory only — not construction drawings. Verify all details on site.
        </p>
      )}
    </div>
  );
}
