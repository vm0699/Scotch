"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Box, Compass, Maximize2, Minus, PenLine, Plus, X } from "lucide-react";

import { Panel, PanelHeader } from "@/components/layout/panel";
import { RoomEditor } from "@/components/workspace/room-editor";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ParameterChange } from "@/features/api/client";
import { FloorPlanSvg, planPixelSize } from "@/features/plan/floor-plan-svg";
import {
  totalBuiltArea,
  unitLabel,
  type ArchitectureProject,
} from "@/features/project/types";
import { cn } from "@/lib/utils";

// Dynamically imported: R3F uses browser-only WebGL APIs (ssr:false required)
const MassingViewer = dynamic(
  () =>
    import("@/features/massing/massing-viewer").then((m) => ({
      default: m.MassingViewer,
    })),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
        Loading 3D…
      </div>
    ),
  },
);

const POPOVER_W = 232;
const POPOVER_H = 200;

type ViewMode = "2d" | "3d";

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 3;
const ZOOM_STEP = 1.25;

const DOT_GRID_STYLE: React.CSSProperties = {
  backgroundImage:
    "radial-gradient(circle, color-mix(in oklch, var(--border) 80%, transparent) 1px, transparent 1px)",
  backgroundSize: "22px 22px",
};

function ViewTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-colors",
        active
          ? "bg-card text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
          : "text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

function InlineTitle({
  value,
  onRename,
}: {
  value: string;
  onRename: (name: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  if (!editing) {
    return (
      <button
        type="button"
        title="Rename project"
        onClick={() => {
          setDraft(value);
          setEditing(true);
        }}
        className="max-w-44 truncate rounded px-1 py-0.5 text-[11px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        {value}
      </button>
    );
  }

  function commit() {
    setEditing(false);
    if (draft.trim() && draft.trim() !== value) {
      onRename(draft);
    }
  }

  return (
    <input
      autoFocus
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") setEditing(false);
      }}
      className="w-44 rounded border border-ring bg-background px-1 py-0.5 text-[11px] outline-none"
    />
  );
}

function EmptyState({
  icon: Icon,
  title,
  body,
}: {
  icon: typeof Compass;
  title: string;
  body: string;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
        <Icon className="size-5" />
      </span>
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="mt-1 max-w-60 text-xs leading-5 text-muted-foreground">
          {body}
        </p>
      </div>
    </div>
  );
}

export function PreviewPanel({
  project,
  title,
  onRename,
  selectedRoomId,
  onSelectRoom,
  editBusy,
  onApplyRoomEdit,
}: {
  project: ArchitectureProject | null;
  title: string;
  onRename: (name: string) => void;
  selectedRoomId: string | null;
  onSelectRoom: (roomId: string | null) => void;
  editBusy: boolean;
  onApplyRoomEdit: (changes: ParameterChange[]) => void;
}) {
  const [view, setView] = useState<ViewMode>("2d");
  const [zoom, setZoom] = useState(1);
  const [popoverPos, setPopoverPos] = useState<{ x: number; y: number } | null>(
    null,
  );
  const canvasRef = useRef<HTMLDivElement>(null);

  // CADAM signature interaction: click a room → select + inline edit popover
  // near the click. Clicking empty canvas deselects.
  function handleCanvasClick(event: React.MouseEvent) {
    const roomEl = (event.target as Element).closest("[data-room-id]");
    if (roomEl && canvasRef.current) {
      const roomId = roomEl.getAttribute("data-room-id");
      const box = canvasRef.current.getBoundingClientRect();
      setPopoverPos({
        x: Math.min(Math.max(event.clientX - box.left + 12, 8), box.width - POPOVER_W - 8),
        y: Math.min(Math.max(event.clientY - box.top + 12, 8), box.height - POPOVER_H - 8),
      });
      onSelectRoom(roomId);
    } else {
      onSelectRoom(null);
      setPopoverPos(null);
    }
  }

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onSelectRoom(null);
        setPopoverPos(null);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onSelectRoom]);

  const selectedRoom =
    project?.rooms.find((r) => r.id === selectedRoomId) ?? null;

  const fitToView = useCallback(() => {
    if (!project || !canvasRef.current) return;
    const { width, height } = planPixelSize(project);
    const box = canvasRef.current.getBoundingClientRect();
    const fit = Math.min((box.width - 24) / width, (box.height - 24) / height);
    setZoom(Math.min(Math.max(fit, MIN_ZOOM), MAX_ZOOM));
  }, [project]);

  // Fit whenever a (new) project arrives.
  useLayoutEffect(() => {
    fitToView();
  }, [fitToView]);

  const plan = project ? planPixelSize(project) : null;

  return (
    <Panel>
      <PanelHeader
        title={
          <div className="flex rounded-lg bg-muted p-0.5">
            <ViewTab active={view === "2d"} onClick={() => setView("2d")}>
              <PenLine className="size-3.5" />
              2D Plan
            </ViewTab>
            <ViewTab active={view === "3d"} onClick={() => setView("3d")}>
              <Box className="size-3.5" />
              3D Massing
            </ViewTab>
          </div>
        }
        actions={
          <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground/70">
            <InlineTitle value={title} onRename={onRename} />
            {project && (
              <span className="whitespace-nowrap">
                · {project.rooms.length} rooms · {totalBuiltArea(project)}{" "}
                {unitLabel(project.units)}²
              </span>
            )}
          </span>
        }
      />

      <div
        ref={canvasRef}
        className="relative min-h-[480px] flex-1 bg-muted/20 lg:min-h-0"
        style={DOT_GRID_STYLE}
      >
        {view === "2d" ? (
          project && plan ? (
            <div
              className="absolute inset-0 flex overflow-auto"
              onClick={handleCanvasClick}
            >
              <FloorPlanSvg
                project={project}
                interactive
                selectedRoomId={selectedRoomId}
                className="m-auto shrink-0"
                style={{
                  width: plan.width * zoom,
                  height: plan.height * zoom,
                }}
              />
            </div>
          ) : (
            <EmptyState
              icon={Compass}
              title="No design yet"
              body="Describe your building in the brief and press Generate. The floor plan renders here."
            />
          )
        ) : project ? (
          <div className="absolute inset-0">
            <MassingViewer project={project} />
          </div>
        ) : (
          <EmptyState
            icon={Box}
            title="3D massing"
            body="Generate a floor plan first — walls and slabs will extrude here."
          />
        )}

        {/* on-canvas room edit popover (CADAM-style) */}
        {view === "2d" && selectedRoom && popoverPos && (
          <div
            className="absolute z-20 w-56 rounded-xl border border-border bg-card p-3 shadow-[0_8px_24px_rgba(0,0,0,0.12)]"
            style={{ left: popoverPos.x, top: popoverPos.y }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Edit room
              </span>
              <Button
                variant="ghost"
                size="icon-xs"
                aria-label="Close room editor"
                onClick={() => {
                  onSelectRoom(null);
                }}
              >
                <X />
              </Button>
            </div>
            <RoomEditor
              room={selectedRoom}
              units={project!.units}
              busy={editBusy}
              compact
              onApply={onApplyRoomEdit}
            />
          </div>
        )}

        {/* scale chip — 2D only */}
        {view === "2d" && (
          <div className="absolute bottom-3 left-3 rounded-md border border-border bg-card px-2 py-1 font-mono text-[10px] text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            {project ? unitLabel(project.units) : "ft"} · plan
          </div>
        )}

        {/* zoom cluster — 2D only (3D viewer has its own overlay controls) */}
        {view === "2d" && <div className="absolute bottom-3 right-3 flex items-center rounded-lg border border-border bg-card p-0.5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                disabled={!project || view !== "2d"}
                onClick={() =>
                  setZoom((z) => Math.max(z / ZOOM_STEP, MIN_ZOOM))
                }
              >
                <Minus />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">Zoom out</TooltipContent>
          </Tooltip>
          <span className="min-w-11 text-center font-mono text-[11px] text-muted-foreground">
            {Math.round(zoom * 100)}%
          </span>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                disabled={!project || view !== "2d"}
                onClick={() =>
                  setZoom((z) => Math.min(z * ZOOM_STEP, MAX_ZOOM))
                }
              >
                <Plus />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">Zoom in</TooltipContent>
          </Tooltip>
          <div className="mx-0.5 h-4 w-px bg-border" />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                disabled={!project || view !== "2d"}
                onClick={fitToView}
              >
                <Maximize2 />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">Fit to view</TooltipContent>
          </Tooltip>
        </div>}
      </div>
    </Panel>
  );
}
