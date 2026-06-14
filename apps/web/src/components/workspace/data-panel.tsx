"use client";

import {
  Braces,
  Box,
  FileBox,
  FileCode2,
  FileImage,
  FileText,
  Info,
  Loader2,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { useState } from "react";

import {
  Panel,
  PanelBody,
  PanelHeader,
  PanelSection,
} from "@/components/layout/panel";
import { ParameterEditor } from "@/components/workspace/parameter-editor";
import { RoomEditor } from "@/components/workspace/room-editor";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ParameterChange } from "@/features/api/client";
import {
  fetchExportBlob,
  triggerExport,
  type ExportFormat,
} from "@/features/api/client";
import {
  formatRoomSize,
  roomArea,
  totalBuiltArea,
  unitLabel,
  type ArchitectureProject,
  type ProjectWarning,
} from "@/features/project/types";
import { cn } from "@/lib/utils";

function GhostRow({ label, width }: { label: string; width: string }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-xs text-muted-foreground/60">{label}</span>
      <span className="h-5 rounded-md bg-muted" style={{ width }} aria-hidden />
    </div>
  );
}

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
];

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

function RoomSchedule({
  project,
  selectedRoomId,
  onSelectRoom,
}: {
  project: ArchitectureProject;
  selectedRoomId: string | null;
  onSelectRoom: (roomId: string | null) => void;
}) {
  const unit = unitLabel(project.units);
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="grid grid-cols-[1fr_auto_auto] gap-3 border-b border-border bg-muted/50 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
        <span>Room</span>
        <span className="w-14 text-right">Size</span>
        <span className="w-14 text-right">Area</span>
      </div>
      {project.rooms.map((room) => (
        <button
          key={room.id}
          type="button"
          onClick={() =>
            onSelectRoom(room.id === selectedRoomId ? null : room.id)
          }
          className={cn(
            "grid w-full grid-cols-[1fr_auto_auto] gap-3 border-b border-border/60 px-3 py-1.5 text-left text-xs transition-colors last:border-b-0",
            room.id === selectedRoomId
              ? "bg-sky-50 text-foreground"
              : "hover:bg-muted/50",
          )}
        >
          <span className="truncate">{room.name}</span>
          <span className="w-14 text-right tabular-nums text-muted-foreground">
            {formatRoomSize(room)}
          </span>
          <span className="w-14 text-right tabular-nums text-muted-foreground">
            {roomArea(room)} {unit}²
          </span>
        </button>
      ))}
      <div className="grid grid-cols-[1fr_auto] gap-3 border-t border-border bg-muted/30 px-3 py-1.5 text-xs font-medium">
        <span>Built-up area</span>
        <span className="tabular-nums">
          {totalBuiltArea(project)} {unit}²
        </span>
      </div>
    </div>
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
  const [lastExport, setLastExport] = useState<string | null>(null);
  const canExport = Boolean(storedId && project);

  async function handleExport(fmt: ExportFormat) {
    if (!storedId || !project || busyFmt) return;
    setBusyFmt(fmt);
    setLastExport(null);
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
      setLastExport(fmt.toUpperCase());
    } catch {
      setLastExport(null);
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
      {lastExport && (
        <p className="text-[11px] text-muted-foreground">
          {lastExport} downloaded.
        </p>
      )}
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
}: {
  project: ArchitectureProject | null;
  storedId: string | null;
  selectedRoomId: string | null;
  onSelectRoom: (roomId: string | null) => void;
  editBusy: boolean;
  onApplyChanges: (changes: ParameterChange[]) => void;
}) {
  const selectedRoom =
    project?.rooms.find((r) => r.id === selectedRoomId) ?? null;

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

        <PanelSection title="Parameters">
          {project ? (
            <ParameterEditor
              project={project}
              busy={editBusy}
              onApply={onApplyChanges}
            />
          ) : (
            <>
              <div className="divide-y divide-border/60">
                <GhostRow label="Site width" width="72px" />
                <GhostRow label="Site depth" width="72px" />
                <GhostRow label="Orientation" width="88px" />
                <GhostRow label="Floors" width="56px" />
              </div>
              <p className="mt-2.5 text-[11px] leading-4 text-muted-foreground/70">
                Generate a design to edit its parameters — here and directly
                on the plan.
              </p>
            </>
          )}
        </PanelSection>

        <PanelSection title="Room Schedule">
          {project ? (
            <RoomSchedule
              project={project}
              selectedRoomId={selectedRoomId}
              onSelectRoom={onSelectRoom}
            />
          ) : (
            <div className="overflow-hidden rounded-lg border border-border">
              <div className="grid grid-cols-[1fr_auto_auto] gap-3 border-b border-border bg-muted/50 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                <span>Room</span>
                <span>Size</span>
                <span>Area</span>
              </div>
              {[0, 1, 2].map((i) => (
                <div
                  key={i}
                  className="grid grid-cols-[1fr_auto_auto] gap-3 border-b border-border/60 px-3 py-2 last:border-b-0"
                  aria-hidden
                >
                  <span className="h-3.5 w-20 rounded bg-muted" />
                  <span className="h-3.5 w-12 rounded bg-muted" />
                  <span className="h-3.5 w-10 rounded bg-muted" />
                </div>
              ))}
            </div>
          )}
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
      </PanelBody>
    </Panel>
  );
}
