"use client";

import {
  Braces,
  Box,
  ExternalLink,
  Eye,
  EyeOff,
  FileBox,
  FileCode2,
  FileImage,
  FileSpreadsheet,
  FileText,
  Info,
  Loader2,
  ShieldCheck,
  Sofa,
  TriangleAlert,
  Wrench,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  Panel,
  PanelBody,
  PanelHeader,
  PanelSection,
} from "@/components/layout/panel";
import { BOQStudio } from "@/components/workspace/boq-studio";
import { AccountPanel } from "@/components/workspace/account-panel";
import { ChangeInbox } from "@/components/workspace/change-inbox";
import { FeasibilitySection } from "@/components/workspace/feasibility-section";
import { ReviewSection } from "@/components/workspace/review-section";
import { DetailStudio } from "@/components/workspace/detail-studio";
import { HistorySection } from "@/components/workspace/history-section";
import { IntelligenceSection } from "@/components/workspace/intelligence-section";
import { InteriorStudio } from "@/components/workspace/interior-studio";
import { MepStudio } from "@/components/workspace/mep-studio";
import { ProgramGrid, ProgramGridSkeleton } from "@/components/workspace/program-grid";
import { RoomEditor } from "@/components/workspace/room-editor";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type {
  ClientBrief,
  ComplianceReport,
  DetailType,
  InteriorEditAction,
  MEPSystem,
  ParameterChange,
  RuleResult,
  StoredProject,
  TNAdvisoryReport,
  TNRuleResult,
  TNStatus,
} from "@/features/api/client";
import {
  fetchExportBlob,
  getClientBrief,
  getCompliance,
  getTNAdvisory,
  triggerExport,
  updateClientBrief,
  type ExportFormat,
} from "@/features/api/client";
import {
  type ArchitectureProject,
  type InteriorGenerationMode,
  type ProjectWarning,
} from "@/features/project/types";
import { cn } from "@/lib/utils";


type ExportGroup = {
  heading?: string;
  formats: {
    label: string;
    fmt: ExportFormat;
    icon: React.ComponentType<{ className?: string }>;
    ext?: string;
    tooltip?: string;
  }[];
};

const EXPORT_GROUPS: ExportGroup[] = [
  {
    heading: "Drawing Files",
    formats: [
      { label: "JSON", fmt: "json", icon: Braces },
      { label: "SVG", fmt: "svg", icon: FileCode2 },
      { label: "PNG", fmt: "png", icon: FileImage },
      { label: "DXF", fmt: "dxf", icon: FileBox },
    ],
  },
  {
    heading: "3D Software",
    formats: [
      {
        label: "SketchUp",
        fmt: "sketchup",
        icon: Box,
        ext: ".rb",
        tooltip: "Ruby script — run in SketchUp Extensions › Ruby Console",
      },
      {
        label: "Blender",
        fmt: "blender",
        icon: Box,
        ext: ".py",
        tooltip: "Python script — run in Blender Scripting workspace",
      },
      {
        label: "Rhino",
        fmt: "rhino",
        icon: Box,
        ext: ".py",
        tooltip: "RhinoPython script — run via Tools › PythonScript in Rhino 7+",
      },
    ],
  },
  {
    heading: "Presentation Sheets",
    formats: [
      {
        label: "Sheet SVG",
        fmt: "sheet_svg",
        icon: FileCode2,
        ext: ".svg",
        tooltip: "A3 board — open in Illustrator; layers preserved",
      },
      {
        label: "Sheet PDF",
        fmt: "sheet_pdf",
        icon: FileText,
        ext: ".pdf",
        tooltip: "A3 print-ready board — place in InDesign or share directly",
      },
    ],
  },
  {
    heading: "BIM",
    formats: [
      {
        label: "IFC",
        fmt: "ifc",
        icon: Box,
        ext: ".ifc",
        tooltip: "Industry Foundation Classes (IFC4) — open in BIM viewers, Revit, ArchiCAD, FreeCAD",
      },
    ],
  },
  {
    heading: "Room Schedule",
    formats: [
      {
        label: "Schedule JSON",
        fmt: "schedule_json",
        icon: Braces,
        ext: ".json",
        tooltip: "Full room schedule with gross and carpet areas as JSON",
      },
      {
        label: "Schedule CSV",
        fmt: "schedule_csv",
        icon: FileSpreadsheet,
        ext: ".csv",
        tooltip: "Room schedule as CSV — open in Excel or Google Sheets",
      },
    ],
  },
];

// ── Compliance section (Phase 27.4) ──────────────────────────────────────────

const RULE_STATUS_STYLES: Record<
  RuleResult["status"],
  { icon: React.ComponentType<{ className?: string }>; className: string; badge: string }
> = {
  pass: { icon: ShieldCheck,    className: "text-emerald-600", badge: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  fail: { icon: TriangleAlert,  className: "text-red-600",     badge: "bg-red-50 text-red-700 border-red-200" },
  warn: { icon: TriangleAlert,  className: "text-amber-600",   badge: "bg-amber-50 text-amber-700 border-amber-200" },
  skip: { icon: Info,           className: "text-muted-foreground", badge: "bg-muted text-muted-foreground border-border" },
};

function ComplianceSection({ projectId }: { projectId: string | null }) {
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    const ctrl = new AbortController();
    setLoading(true);
    getCompliance(projectId, ctrl.signal)
      .then(setReport)
      .catch(() => {/* backend offline or no project yet */})
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [projectId]);

  if (!projectId) return (
    <p className="text-[11px] text-muted-foreground/70">Generate a plan to run compliance checks.</p>
  );

  if (loading) return (
    <div className="flex items-center gap-2 text-[11px] text-muted-foreground/60">
      <Loader2 className="size-3 animate-spin" /> Running NBC checks…
    </div>
  );

  if (!report) return (
    <p className="text-[11px] text-muted-foreground/70">Compliance data unavailable — backend may be offline.</p>
  );

  const fails = report.rules.filter((r) => r.status === "fail");
  const warns = report.rules.filter((r) => r.status === "warn");
  const passes = report.rules.filter((r) => r.status === "pass");

  return (
    <div className="flex flex-col gap-2.5">
      {/* Overall badge */}
      <div className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2.5",
        report.passes_review
          ? "border-emerald-200 bg-emerald-50"
          : "border-red-200 bg-red-50",
      )}>
        {report.passes_review
          ? <ShieldCheck className="size-3.5 shrink-0 text-emerald-600" />
          : <TriangleAlert className="size-3.5 shrink-0 text-red-600" />}
        <div>
          <p className={cn("text-[11px] font-semibold",
            report.passes_review ? "text-emerald-700" : "text-red-700")}>
            {report.passes_review ? "Passes NBC Review" : "Needs Attention"}
          </p>
          <p className="mt-0.5 text-[10px] leading-4 text-foreground/60">{report.summary}</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-1.5">
        {[
          { label: "Pass", count: passes.length, color: "text-emerald-600" },
          { label: "Fail", count: fails.length,  color: "text-red-600" },
          { label: "Warn", count: warns.length,  color: "text-amber-600" },
        ].map(({ label, count, color }) => (
          <div key={label} className="rounded border border-border bg-muted/30 px-2 py-1.5 text-center">
            <p className={cn("text-base font-semibold leading-none", color)}>{count}</p>
            <p className="mt-0.5 text-[9px] text-muted-foreground/60">{label}</p>
          </div>
        ))}
      </div>

      {/* Rule list */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground/70 hover:text-foreground/80"
      >
        <Info className="size-3" />
        {expanded ? "Hide" : "Show"} all {report.rules.length} checks
      </button>

      {expanded && (
        <ul className="flex flex-col gap-1.5">
          {report.rules.map((rule) => {
            const s = RULE_STATUS_STYLES[rule.status];
            return (
              <li key={rule.rule_id} className="rounded-lg border border-border bg-muted/20 px-2.5 py-2">
                <div className="flex items-start gap-2">
                  <s.icon className={cn("mt-0.5 size-3 shrink-0", s.className)} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className={cn(
                        "inline-flex shrink-0 items-center rounded border px-1 py-px text-[9px] font-semibold uppercase tracking-wide",
                        s.badge,
                      )}>
                        {rule.status}
                      </span>
                      <span className="truncate text-[10px] font-medium text-foreground/80">
                        {rule.description}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[10px] leading-4 text-muted-foreground/70">{rule.message}</p>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Context note */}
      <p className="text-[10px] leading-4 text-muted-foreground/50">
        NBC 2016 urban residential — FSI {report.max_fsi}, setbacks {report.front_setback_ft.toFixed(1)} ft front /
        {" "}{report.side_setback_ft.toFixed(1)} ft sides / {report.rear_setback_ft.toFixed(1)} ft rear.
      </p>
    </div>
  );
}

// ── Tamil Nadu Advisory section (Phase 32) ───────────────────────────────────

const TN_STATUS_STYLES: Record<
  TNStatus,
  { icon: React.ComponentType<{ className?: string }>; className: string; badge: string }
> = {
  pass:          { icon: ShieldCheck,   className: "text-emerald-600", badge: "bg-emerald-50 text-emerald-700 border-emerald-200" },
  fail:          { icon: TriangleAlert, className: "text-red-600",     badge: "bg-red-50 text-red-700 border-red-200" },
  warn:          { icon: TriangleAlert, className: "text-amber-600",   badge: "bg-amber-50 text-amber-700 border-amber-200" },
  skip:          { icon: Info,          className: "text-muted-foreground", badge: "bg-muted text-muted-foreground border-border" },
  advisory:      { icon: Info,          className: "text-blue-600",    badge: "bg-blue-50 text-blue-700 border-blue-200" },
  missing_input: { icon: Info,          className: "text-amber-500",   badge: "bg-amber-50 text-amber-600 border-amber-200" },
};

function TNAdvisorySection({ projectId }: { projectId: string | null }) {
  const [report, setReport] = useState<TNAdvisoryReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    const ctrl = new AbortController();
    setLoading(true);
    getTNAdvisory(projectId, 0, ctrl.signal)
      .then(setReport)
      .catch(() => {/* backend offline or no project yet */})
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [projectId]);

  if (!projectId) return (
    <p className="text-[11px] text-muted-foreground/70">Generate a plan to run TN advisory checks.</p>
  );

  if (loading) return (
    <div className="flex items-center gap-2 text-[11px] text-muted-foreground/60">
      <Loader2 className="size-3 animate-spin" /> Running TN advisory…
    </div>
  );

  if (!report) return (
    <p className="text-[11px] text-muted-foreground/70">TN advisory unavailable — generate a plan first.</p>
  );

  const warns = report.results.filter((r) => r.status === "warn" || r.status === "fail");
  const missing = report.missing_inputs;

  return (
    <div className="flex flex-col gap-2.5">
      {/* Advisory badge */}
      <div className={cn(
        "flex items-start gap-2 rounded-lg border px-3 py-2.5",
        warns.length === 0
          ? "border-blue-200 bg-blue-50"
          : "border-amber-200 bg-amber-50",
      )}>
        <Info className={cn("mt-0.5 size-3.5 shrink-0", warns.length === 0 ? "text-blue-600" : "text-amber-600")} />
        <div className="min-w-0">
          <p className={cn("text-[11px] font-semibold", warns.length === 0 ? "text-blue-700" : "text-amber-700")}>
            Tamil Nadu Advisory
          </p>
          <p className="mt-0.5 text-[10px] leading-4 text-foreground/60">{report.summary}</p>
        </div>
      </div>

      {/* Missing inputs */}
      {missing.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-2">
          <p className="text-[10px] font-medium text-amber-700 mb-1">Missing inputs for full analysis:</p>
          <ul className="list-disc list-inside space-y-0.5">
            {missing.map((m) => (
              <li key={m} className="text-[10px] text-amber-700">{m}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Toggle results */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground/70 hover:text-foreground/80"
      >
        <Info className="size-3" />
        {expanded ? "Hide" : "Show"} all {report.results.length} advisory checks
      </button>

      {expanded && (
        <ul className="flex flex-col gap-1.5">
          {report.results.map((result) => {
            const s = TN_STATUS_STYLES[result.status];
            return (
              <li key={result.rule_id} className="rounded-lg border border-border bg-muted/20 px-2.5 py-2">
                <div className="flex items-start gap-2">
                  <s.icon className={cn("mt-0.5 size-3 shrink-0", s.className)} />
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className={cn(
                        "inline-flex shrink-0 items-center rounded border px-1 py-px text-[9px] font-semibold uppercase tracking-wide",
                        s.badge,
                      )}>
                        {result.status.replace("_", " ")}
                      </span>
                      <span className="truncate text-[10px] font-medium text-foreground/80">
                        {result.title}
                      </span>
                    </div>
                    <p className="mt-0.5 text-[10px] leading-4 text-muted-foreground/70">{result.message}</p>
                    {result.advisory_items.length > 0 && (
                      <ul className="mt-1 list-disc list-inside space-y-0.5">
                        {result.advisory_items.map((item, i) => (
                          <li key={i} className="text-[10px] text-muted-foreground/60">{item}</li>
                        ))}
                      </ul>
                    )}
                    <div className="mt-1 flex flex-wrap items-center gap-2">
                      <span className="text-[9px] text-muted-foreground/50">
                        Source: {result.source_name}
                        {result.source_section ? ` · ${result.source_section}` : ""}
                      </span>
                      <span className="text-[9px] text-muted-foreground/40">
                        {Math.round(result.confidence * 100)}% confidence
                        {result.is_placeholder ? " · placeholder values" : ""}
                      </span>
                    </div>
                    {result.needs_professional_verification && (
                      <p className="mt-0.5 text-[9px] font-medium text-amber-600">
                        Verify with licensed architect / CMDA-registered engineer
                      </p>
                    )}
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* Disclaimer */}
      <p className="text-[9px] leading-4 text-muted-foreground/50 italic">
        {report.disclaimer}
      </p>
    </div>
  );
}

const WARNING_STYLES = {
  info: { icon: Info, className: "text-muted-foreground" },
  warning: { icon: TriangleAlert, className: "text-amber-600" },
  error: { icon: TriangleAlert, className: "text-red-600" },
} as const;

function WarningRow({ warning }: { warning: ProjectWarning }) {
  const style = WARNING_STYLES[warning.severity];
  return (
    <li className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/30 px-3 py-2.5">
      <style.icon className={cn("mt-0.5 size-3.5 shrink-0", style.className)} />
      <p className="text-xs leading-5 text-foreground/80">{warning.message}</p>
    </li>
  );
}


function ExportSection({
  project,
  storedId,
}: {
  project: ArchitectureProject | null;
  storedId: string | null;
}) {
  const [busyFmt, setBusyFmt] = useState<ExportFormat | null>(null);
  const canExport = Boolean(storedId && project);

  async function handleExport(fmt: ExportFormat) {
    if (!storedId || !project || busyFmt) return;
    setBusyFmt(fmt);
    try {
      const manifest = await triggerExport(storedId, fmt);
      const blob = await fetchExportBlob(storedId, manifest.filename);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = manifest.filename;
      document.body.appendChild(anchor);
      anchor.click();
      document.body.removeChild(anchor);
      URL.revokeObjectURL(url);
      toast.success(`${manifest.filename} downloaded.`);
    } catch {
      toast.error(`Export failed — engine may be offline. Try again.`, { duration: 5000 });
    } finally {
      setBusyFmt(null);
    }
  }

  const disabledTip = !canExport
    ? storedId
      ? "Generate a floor plan to enable exports"
      : "Save the project first to enable exports"
    : null;

  return (
    <div className="flex flex-col gap-3">
      {EXPORT_GROUPS.map((group) => (
        <div key={group.heading} className="flex flex-col gap-1.5">
          {group.heading && (
            <p className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
              {group.heading}
            </p>
          )}
          <div className="grid grid-cols-2 gap-2">
            {group.formats.map(({ label, fmt, icon: Icon, ext, tooltip }) => {
              const busy = busyFmt === fmt;
              return (
                <Tooltip key={fmt}>
                  <TooltipTrigger asChild>
                    <span>
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={!canExport || busyFmt !== null}
                        onClick={() => void handleExport(fmt)}
                        className="w-full justify-start gap-2"
                      >
                        {busy ? (
                          <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                        ) : (
                          <Icon className="size-3.5 text-muted-foreground" />
                        )}
                        <span className="truncate">
                          {label}
                          {ext && (
                            <span className="ml-1 text-[10px] text-muted-foreground/60">
                              {ext}
                            </span>
                          )}
                        </span>
                      </Button>
                    </span>
                  </TooltipTrigger>
                  {(disabledTip ?? tooltip) && (
                    <TooltipContent side="top">
                      {disabledTip ?? tooltip}
                    </TooltipContent>
                  )}
                </Tooltip>
              );
            })}
          </div>
        </div>
      ))}
      {/* SketchUp extension help affordance */}
      <div className="rounded-lg border border-border bg-muted/30 px-3 py-2.5">
        <p className="text-[11px] font-medium text-foreground/80">
          SketchUp Extension
        </p>
        <p className="mt-1 text-[11px] leading-4 text-muted-foreground/70">
          Install the Scotch extension for one-click JSON import with full tags
          and materials.{" "}
          <a
            href="/docs/integrations/sketchup-workflow"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-0.5 text-foreground/60 underline underline-offset-2 hover:text-foreground/90"
          >
            Workflow guide
            <ExternalLink className="size-2.5" />
          </a>
        </p>
      </div>
    </div>
  );
}

// ── Phase 33 — Client Brief Editor ───────────────────────────────────────────

const BUDGET_LABELS: Record<string, string> = {
  economy: "Economy",
  standard: "Standard",
  premium: "Premium",
};

function ClientBriefSection({ projectId }: { projectId: string | null }) {
  const [brief, setBrief] = useState<ClientBrief | null>(null);
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    if (!projectId) return;
    getClientBrief(projectId).then(setBrief).catch(() => setBrief(null));
  }, [projectId]);

  async function handleBudget(level: string) {
    if (!projectId || saving) return;
    setSaving(true);
    try {
      const updated = await updateClientBrief(projectId, { budget_level: level as ClientBrief["budget_level"] });
      setBrief(updated);
      toast.success(`Budget set to ${BUDGET_LABELS[level] ?? level}.`);
    } catch {
      toast.error("Couldn't update client brief.");
    } finally {
      setSaving(false);
    }
  }

  async function handleFamilySize(size: number) {
    if (!projectId || saving || isNaN(size)) return;
    setSaving(true);
    try {
      const updated = await updateClientBrief(projectId, { family_size: size });
      setBrief(updated);
    } catch {
      toast.error("Couldn't update client brief.");
    } finally {
      setSaving(false);
    }
  }

  async function handleVastu(val: boolean) {
    if (!projectId || saving) return;
    setSaving(true);
    try {
      const updated = await updateClientBrief(projectId, { vastu_preference: val });
      setBrief(updated);
    } catch {
      toast.error("Couldn't update client brief.");
    } finally {
      setSaving(false);
    }
  }

  if (!projectId) {
    return (
      <p className="text-[11px] text-muted-foreground/70">
        Save the project to enable client brief.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Budget selector */}
      <div>
        <p className="mb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
          Budget Level
        </p>
        <div className="grid grid-cols-3 gap-1.5">
          {(["economy", "standard", "premium"] as const).map((lvl) => (
            <button
              key={lvl}
              type="button"
              disabled={saving}
              onClick={() => void handleBudget(lvl)}
              className={cn(
                "rounded-md border px-2 py-1.5 text-[11px] font-medium transition-colors",
                brief?.budget_level === lvl
                  ? "border-foreground/40 bg-foreground/10 text-foreground"
                  : "border-border bg-muted/20 text-muted-foreground hover:border-foreground/20 hover:bg-muted/40",
              )}
            >
              {BUDGET_LABELS[lvl]}
            </button>
          ))}
        </div>
      </div>

      {/* Expand for more fields */}
      <button
        type="button"
        onClick={() => setExpanded((e) => !e)}
        className="flex items-center gap-1.5 text-[10px] font-medium text-muted-foreground/70 hover:text-foreground/80"
      >
        <Info className="size-3" />
        {expanded ? "Fewer" : "More"} client details
      </button>

      {expanded && (
        <div className="flex flex-col gap-3">
          {/* Family size */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
              Family Size
            </label>
            <input
              type="number"
              min={1}
              max={20}
              defaultValue={brief?.family_size ?? 0}
              onBlur={(e) => void handleFamilySize(parseInt(e.target.value, 10))}
              className="w-full rounded-md border border-border bg-muted/20 px-2.5 py-1.5 text-[12px] text-foreground outline-none focus:border-foreground/30"
            />
          </div>

          {/* Vastu */}
          <div className="flex items-center justify-between">
            <span className="text-[11px] text-foreground/80">Vastu Preference</span>
            <button
              type="button"
              disabled={saving}
              onClick={() => void handleVastu(!(brief?.vastu_preference ?? false))}
              className={cn(
                "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors",
                brief?.vastu_preference ? "bg-foreground/80" : "bg-muted-foreground/30",
              )}
            >
              <span
                className={cn(
                  "pointer-events-none inline-block size-4 rounded-full bg-white shadow transition-transform",
                  brief?.vastu_preference ? "translate-x-4" : "translate-x-0",
                )}
              />
            </button>
          </div>

          {/* Style preference */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
              Style Preference
            </label>
            <input
              type="text"
              defaultValue={brief?.style_preference ?? ""}
              placeholder="contemporary, traditional, minimal…"
              onBlur={async (e) => {
                if (!projectId || saving) return;
                setSaving(true);
                try {
                  const updated = await updateClientBrief(projectId, { style_preference: e.target.value.trim() });
                  setBrief(updated);
                } catch { /* ignore */ } finally { setSaving(false); }
              }}
              className="w-full rounded-md border border-border bg-muted/20 px-2.5 py-1.5 text-[12px] text-foreground outline-none focus:border-foreground/30"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="mb-1 block text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
              Notes
            </label>
            <textarea
              rows={2}
              defaultValue={brief?.notes ?? ""}
              placeholder="Any special requirements…"
              onBlur={async (e) => {
                if (!projectId || saving) return;
                setSaving(true);
                try {
                  const updated = await updateClientBrief(projectId, { notes: e.target.value.trim() });
                  setBrief(updated);
                } catch { /* ignore */ } finally { setSaving(false); }
              }}
              className="w-full resize-none rounded-md border border-border bg-muted/20 px-2.5 py-1.5 text-[12px] leading-4 text-foreground outline-none focus:border-foreground/30"
            />
          </div>
        </div>
      )}

      <p className="text-[10px] leading-4 text-muted-foreground/50">
        Budget influences room sizes on next generation. Vastu → east-facing orientation.
      </p>
    </div>
  );
}

export function DataPanel({
  project,
  storedId,
  selectedRoomId,
  onSelectRoom,
  editBusy,
  onApplyChanges,
  historyKey,
  onRestoreVersion,
  activeMepLayers,
  onToggleMepLayer,
  selectedMepPointId,
  onSelectMepPoint,
  onGenerateMep,
  mepGenerating,
  onGenerateDetail,
  onDeleteDetail,
  detailGenerating,
  onCalculateBOQ,
  onEditRate,
  onEditTileSpec,
  boqCalculating,
  selectedFurnitureId,
  onSelectFurniture,
  onGenerateInterior,
  onEditInterior,
  onGenerateAllInteriors,
  interiorBusy,
}: {
  project: ArchitectureProject | null;
  storedId: string | null;
  selectedRoomId: string | null;
  onSelectRoom: (roomId: string | null) => void;
  editBusy: boolean;
  onApplyChanges: (changes: ParameterChange[]) => void;
  historyKey: number;
  onRestoreVersion: (stored: StoredProject) => void;
  activeMepLayers?: Set<MEPSystem>;
  onToggleMepLayer?: (s: MEPSystem) => void;
  selectedMepPointId?: string | null;
  onSelectMepPoint?: (id: string) => void;
  onGenerateMep?: (systems?: MEPSystem[]) => void;
  mepGenerating?: boolean;
  onGenerateDetail?: (type: DetailType, sourceId: string) => void;
  onDeleteDetail?: (id: string) => void;
  detailGenerating?: boolean;
  onCalculateBOQ?: () => Promise<void>;
  onEditRate?: (category: string, item: string, rate: number) => Promise<void>;
  onEditTileSpec?: (id: string, field: string, value: number) => Promise<void>;
  boqCalculating?: boolean;
  selectedFurnitureId?: string | null;
  onSelectFurniture?: (id: string | null) => void;
  onGenerateInterior?: (roomId: string, opts: { mode: InteriorGenerationMode; style: string }) => void;
  onEditInterior?: (roomId: string, edit: InteriorEditAction) => void;
  onGenerateAllInteriors?: (opts: { mode: InteriorGenerationMode; style: string; overwrite: boolean }) => void;
  interiorBusy?: boolean;
}) {
  const selectedRoom = useMemo(
    () => project?.rooms.find((r) => r.id === selectedRoomId) ?? null,
    [project, selectedRoomId],
  );
  const unitLabel = project?.units === "meters" ? "m" : "ft";

  return (
    <Panel>
      <PanelHeader title="Design Data" />
      <PanelBody>
        {project && (
          <PanelSection title="Selection">
            {selectedRoom ? (
              <RoomEditor
                room={selectedRoom}
                units={project.units}
                busy={editBusy}
                onApply={onApplyChanges}
              />
            ) : (
              <p className="text-[11px] leading-4 text-muted-foreground/70">
                Click a room on the plan to edit its name and dimensions —
                here or right on the drawing.
              </p>
            )}
          </PanelSection>
        )}

        <PanelSection title="Program">
          {project ? (
            <ProgramGrid
              project={project}
              selectedRoomId={selectedRoomId}
              onSelectRoom={onSelectRoom}
              busy={editBusy}
              onApplyChanges={onApplyChanges}
            />
          ) : (
            <ProgramGridSkeleton />
          )}
        </PanelSection>

        <PanelSection title="Intelligence">
          <IntelligenceSection projectId={storedId} unit={unitLabel} />
        </PanelSection>

        <PanelSection title="Compliance">
          <ComplianceSection projectId={storedId} />
        </PanelSection>

        <PanelSection title="TN Advisory">
          <TNAdvisorySection projectId={storedId} />
        </PanelSection>

        <PanelSection title="Client Brief">
          <ClientBriefSection projectId={storedId} />
        </PanelSection>

        <PanelSection title="Client Changes">
          <ChangeInbox projectId={storedId} />
        </PanelSection>

        <PanelSection title="History">
          <HistorySection
            projectId={storedId}
            historyKey={historyKey}
            onRestored={onRestoreVersion}
          />
        </PanelSection>

        {project && (
          <PanelSection title="Furniture">
            <div className="flex items-start gap-3">
              <Sofa className="mt-0.5 size-3.5 shrink-0 text-muted-foreground/60" />
              <div className="flex flex-1 flex-col gap-1.5">
                <p className="text-[11px] leading-4 text-muted-foreground/80">
                  {project.furniture.length} item{project.furniture.length !== 1 ? "s" : ""} placed across {new Set(project.furniture.map((f) => f.room_id)).size} room{new Set(project.furniture.map((f) => f.room_id)).size !== 1 ? "s" : ""}.
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full justify-start gap-2"
                  onClick={() =>
                    onApplyChanges([
                      { key: "show_furniture", value: !project.show_furniture },
                    ])
                  }
                  disabled={editBusy}
                >
                  {project.show_furniture ? (
                    <Eye className="size-3.5 text-muted-foreground" />
                  ) : (
                    <EyeOff className="size-3.5 text-muted-foreground" />
                  )}
                  {project.show_furniture ? "Hide furniture layer" : "Show furniture layer"}
                </Button>
              </div>
            </div>
          </PanelSection>
        )}

        {project && (
          <PanelSection title="Interior Design">
            <InteriorStudio
              project={project}
              selectedRoomId={selectedRoomId}
              selectedFurnitureId={selectedFurnitureId ?? null}
              onSelectFurniture={onSelectFurniture ?? (() => {})}
              onGenerate={(roomId, opts) => onGenerateInterior?.(roomId, opts)}
              onEdit={(roomId, edit) => onEditInterior?.(roomId, edit)}
              onGenerateAll={(opts) => onGenerateAllInteriors?.(opts)}
              busy={!!interiorBusy}
            />
          </PanelSection>
        )}

        {project && (
          <PanelSection title="MEP Studio">
            <MepStudio
              project={project}
              activeLayers={activeMepLayers ?? new Set<MEPSystem>(["plumbing", "electrical", "lighting", "ac"])}
              onToggleLayer={(s) => onToggleMepLayer?.(s)}
              selectedPointId={selectedMepPointId}
              onSelectPoint={onSelectMepPoint}
              onGenerateMep={onGenerateMep}
              generating={mepGenerating}
            />
          </PanelSection>
        )}

        {project && (
          <PanelSection title="Detail Drawings">
            <DetailStudio
              project={project}
              projectId={storedId ?? undefined}
              onGenerateDetail={(type, src) => onGenerateDetail?.(type, src)}
              onDeleteDetail={(id) => onDeleteDetail?.(id)}
              generating={detailGenerating ?? false}
            />
          </PanelSection>
        )}

        {project && (
          <PanelSection title="BOQ &amp; Cost">
            <BOQStudio
              project={project}
              onCalculate={onCalculateBOQ ?? (async () => {})}
              onEditRate={onEditRate ?? (async () => {})}
              onEditTileSpec={onEditTileSpec ? async (id, field, value) => onEditTileSpec(id, field as never, value) : async () => {}}
              calculating={boqCalculating ?? false}
            />
          </PanelSection>
        )}

        <PanelSection title="Feasibility">
          <FeasibilitySection projectId={storedId} />
        </PanelSection>

        <PanelSection title="Review &amp; QA">
          <ReviewSection projectId={storedId} />
        </PanelSection>

        <PanelSection title="Exports">
          <ExportSection project={project} storedId={storedId} />
        </PanelSection>

        <PanelSection title="Warnings">
          {project ? (
            <>
              <ul className="flex flex-col gap-2">
                {project.warnings.map((warning) => (
                  <WarningRow key={warning.id} warning={warning} />
                ))}
              </ul>
              {project.notes.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
                    Assumptions
                  </h4>
                  <ul className="mt-1.5 flex flex-col gap-1">
                    {project.notes.map((note) => (
                      <li
                        key={note}
                        className="flex items-start gap-2 text-[11px] leading-4 text-muted-foreground"
                      >
                        <span className="mt-1.5 size-1 shrink-0 rounded-full bg-muted-foreground/40" />
                        {note}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          ) : (
            <div className="flex items-center gap-2.5 rounded-lg border border-border bg-muted/40 px-3 py-2.5">
              <ShieldCheck className="size-4 text-muted-foreground" />
              <p className="text-xs leading-5 text-muted-foreground">
                Design checks run after generation.
              </p>
            </div>
          )}
        </PanelSection>

        <AccountPanel />
      </PanelBody>
    </Panel>
  );
}
