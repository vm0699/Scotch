"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Box, Compass, Download, ImageIcon, Loader2, Maximize2, Minus, PenLine, Plus, Ruler, X } from "lucide-react";

import { Panel, PanelHeader } from "@/components/layout/panel";
import { ReferenceOverlay } from "@/components/workspace/reference-overlay";
import { RoomEditor } from "@/components/workspace/room-editor";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ParameterChange, RenderStyleInfo } from "@/features/api/client";
import { createRender, getCameras, getRenderStyles } from "@/features/api/client";
import type { MEPSystem } from "@/features/project/types";
import { FloorPlanSvg, planPixelSize } from "@/features/plan/floor-plan-svg";
import {
  totalBuiltArea,
  unitLabel,
  type ArchitectureProject,
  type CameraSuggestion,
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

type ViewMode = "2d" | "3d" | "render";

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
  projectId,
  title,
  onRename,
  selectedRoomId,
  onSelectRoom,
  editBusy,
  onApplyRoomEdit,
  activeMepLayers,
  selectedMepPointId,
  onSelectMepPoint,
  onToggleMepLayer,
  selectedFurnitureId,
  onSelectFurniture,
  onMoveFurniture,
}: {
  project: ArchitectureProject | null;
  projectId?: string;
  title: string;
  onRename: (name: string) => void;
  selectedRoomId: string | null;
  onSelectRoom: (roomId: string | null) => void;
  editBusy: boolean;
  onApplyRoomEdit: (changes: ParameterChange[]) => void;
  activeMepLayers?: Set<MEPSystem>;
  selectedMepPointId?: string | null;
  onSelectMepPoint?: (id: string) => void;
  onToggleMepLayer?: (system: MEPSystem) => void;
  /** Selected furniture item (Phase 43 — click-to-select interior editing). */
  selectedFurnitureId?: string | null;
  onSelectFurniture?: (id: string | null) => void;
  /** Stage 43.17 — freehand drag-with-snap; supplying this enables dragging. */
  onMoveFurniture?: (id: string, x: number, y: number) => void;
}) {
  const [view, setView] = useState<ViewMode>("2d");
  const [zoom, setZoom] = useState(1);
  const [activeLevel, setActiveLevel] = useState(0);
  const [popoverPos, setPopoverPos] = useState<{ x: number; y: number } | null>(
    null,
  );
  const canvasRef = useRef<HTMLDivElement>(null);

  // ── 2D canvas layer toggles ────────────────────────────────────────────────
  const [showDimensions, setShowDimensions] = useState(true);
  const [showFurniturePlan, setShowFurniturePlan] = useState(true);

  // ── Drag-to-pan (pointer tracking on the scroll container) ────────────────
  const scrollRef = useRef<HTMLDivElement>(null);
  const panRef = useRef<{ x: number; y: number; sl: number; st: number } | null>(null);
  const lastDragRef = useRef(false);

  function handlePanStart(e: React.PointerEvent<HTMLDivElement>) {
    if (e.button !== 0) return;
    const el = e.currentTarget;
    el.setPointerCapture(e.pointerId);
    el.style.cursor = "grabbing";
    lastDragRef.current = false;
    panRef.current = { x: e.clientX, y: e.clientY, sl: el.scrollLeft, st: el.scrollTop };
  }

  function handlePanMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!panRef.current) return;
    const el = e.currentTarget;
    const dx = e.clientX - panRef.current.x;
    const dy = e.clientY - panRef.current.y;
    if (!lastDragRef.current && Math.hypot(dx, dy) > 4) {
      lastDragRef.current = true;
    }
    if (lastDragRef.current) {
      el.scrollLeft = panRef.current.sl - dx;
      el.scrollTop = panRef.current.st - dy;
    }
  }

  function handlePanEnd(e: React.PointerEvent<HTMLDivElement>) {
    e.currentTarget.style.cursor = "grab";
    panRef.current = null;
  }

  // ── Render tab state (Phase 23) ────────────────────────────────────────────
  const captureRef = useRef<(() => string) | null>(null);
  const [renderStyles, setRenderStyles] = useState<RenderStyleInfo[]>([]);
  const [renderCameras, setRenderCameras] = useState<CameraSuggestion[]>([]);
  const [selectedStyle, setSelectedStyle] = useState("photorealistic_exterior");
  const [selectedCamera, setSelectedCamera] = useState("");
  const [renderBusy, setRenderBusy] = useState(false);
  const [renderResult, setRenderResult] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  // CADAM signature interaction: click a room → select + inline edit popover
  // near the click. Clicking empty canvas deselects.
  function handleCanvasClick(event: React.MouseEvent) {
    // If the pointer moved more than the drag threshold, this is a pan-end, not a click.
    if (lastDragRef.current) {
      lastDragRef.current = false;
      return;
    }
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

  // Fit whenever a (new) project arrives; reset per-project state.
  useLayoutEffect(() => {
    fitToView();
    setActiveLevel(0);
    setRenderResult(null);
    setRenderError(null);
  }, [fitToView]);

  // Load render styles once.
  useEffect(() => {
    getRenderStyles().then(setRenderStyles).catch(() => {});
  }, []);

  // Load camera presets when render tab opens (and project/projectId are available).
  useEffect(() => {
    if (view !== "render" || !projectId) return;
    const ctrl = new AbortController();
    getCameras(projectId, ctrl.signal)
      .then((cams) => {
        setRenderCameras(cams);
        if (cams.length > 0 && !selectedCamera) setSelectedCamera(cams[0].name);
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, [view, projectId, selectedCamera]);

  async function handleGenerateRender() {
    if (!projectId) return;
    setRenderBusy(true);
    setRenderError(null);
    setRenderResult(null);
    try {
      const conditioning = captureRef.current?.() ?? null;
      const resp = await createRender(projectId, {
        camera_id: selectedCamera || "exterior_quarter",
        style: selectedStyle,
        conditioning_image_b64: conditioning,
      });
      setRenderResult(resp.render_b64);
    } catch (e) {
      setRenderError(e instanceof Error ? e.message : "Render failed");
    } finally {
      setRenderBusy(false);
    }
  }

  function downloadRender() {
    if (!renderResult) return;
    const a = document.createElement("a");
    a.href = `data:image/png;base64,${renderResult}`;
    a.download = "scotch-render.png";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  const plan = project ? planPixelSize(project) : null;

  return (
    <Panel className="flex-1 min-h-0">
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
            <ViewTab active={view === "render"} onClick={() => setView("render")}>
              <ImageIcon className="size-3.5" />
              Render
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
        {/* ── 2D plan ────────────────────────────────────────────────────────── */}
        {view === "2d" && (
          project && plan ? (
            <div className="absolute inset-0 flex flex-col">
              {/* Level tabs — shown only for multi-floor projects */}
              {project.levels.length > 1 && (
                <div className="flex shrink-0 items-center gap-0.5 border-b border-border/60 bg-card/80 px-3 py-1 backdrop-blur-sm">
                  {project.levels.map((lv) => (
                    <button
                      key={lv.index}
                      type="button"
                      onClick={() => setActiveLevel(lv.index)}
                      className={
                        "rounded px-2.5 py-0.5 text-[11px] font-medium transition-colors " +
                        (activeLevel === lv.index
                          ? "bg-foreground text-background"
                          : "text-muted-foreground hover:text-foreground")
                      }
                    >
                      {lv.name}
                    </button>
                  ))}
                </div>
              )}
              <div
                ref={scrollRef}
                className="relative flex flex-1 overflow-auto"
                style={{ cursor: "grab" }}
                onClick={handleCanvasClick}
                onPointerDown={handlePanStart}
                onPointerMove={handlePanMove}
                onPointerUp={handlePanEnd}
                onPointerLeave={handlePanEnd}
              >
                <FloorPlanSvg
                  project={project}
                  interactive
                  selectedRoomId={selectedRoomId}
                  activeLevel={activeLevel}
                  className="m-auto shrink-0"
                  style={{
                    width: plan.width * zoom,
                    height: plan.height * zoom,
                  }}
                  showDimensions={showDimensions}
                  showFurniturePlan={showFurniturePlan}
                  activeMepLayers={activeMepLayers}
                  selectedMepPointId={selectedMepPointId}
                  onSelectMepPoint={onSelectMepPoint}
                  selectedFurnitureId={selectedFurnitureId}
                  onSelectFurniture={onSelectFurniture}
                  onMoveFurniture={onMoveFurniture}
                />
                {/* Phase 39 — reference image overlay */}
                {projectId && (
                  <ReferenceOverlay
                    projectId={projectId}
                    canvasWidth={plan.width * zoom}
                    canvasHeight={plan.height * zoom}
                  />
                )}
              </div>
            </div>
          ) : (
            <EmptyState
              icon={Compass}
              title="No design yet"
              body="Describe your building in the brief and press Generate. The floor plan renders here."
            />
          )
        )}

        {/* ── 3D viewer — mounted for 3d + render tabs (capture needs it live) ── */}
        {(view === "3d" || view === "render") && (
          project ? (
            <div className={cn("absolute inset-0", view !== "3d" && "invisible pointer-events-none")}>
              <MassingViewer
                project={project}
                projectId={view === "3d" ? projectId : undefined}
                onCaptureReady={(fn) => { captureRef.current = fn; }}
                selectedFurnitureId={selectedFurnitureId}
              />
            </div>
          ) : (
            <EmptyState
              icon={Box}
              title="3D massing"
              body="Generate a floor plan first — walls and slabs will extrude here."
            />
          )
        )}

        {/* ── Render UI — overlays the hidden 3D viewer ────────────────────── */}
        {view === "render" && (
          <div className="absolute inset-0 z-10 overflow-y-auto bg-background/97 backdrop-blur-sm">
            {!project ? (
              <EmptyState
                icon={ImageIcon}
                title="Render"
                body="Generate a floor plan first to enable rendering."
              />
            ) : (
              <div className="flex flex-col gap-4 p-4">
                {/* Style picker */}
                <div>
                  <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
                    Style
                  </div>
                  <div className="grid grid-cols-5 gap-2">
                    {renderStyles.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => setSelectedStyle(s.id)}
                        className={cn(
                          "flex flex-col items-center gap-1.5 rounded-lg border p-2 transition-all",
                          selectedStyle === s.id
                            ? "border-foreground shadow-[0_0_0_1px_var(--foreground)]"
                            : "border-border hover:border-foreground/40",
                        )}
                      >
                        <div
                          className="h-7 w-full rounded-md"
                          style={{ background: s.swatch_color }}
                        />
                        <span className="line-clamp-1 text-[10px] font-medium leading-tight">
                          {s.name}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Camera selector */}
                {renderCameras.length > 0 && (
                  <div>
                    <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
                      Camera
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {renderCameras.map((cam) => (
                        <button
                          key={cam.name}
                          type="button"
                          onClick={() => setSelectedCamera(cam.name)}
                          className={cn(
                            "rounded-md border px-2.5 py-1 text-[11px] capitalize transition-colors",
                            selectedCamera === cam.name
                              ? "border-foreground bg-foreground/5 font-medium"
                              : "border-border text-muted-foreground hover:border-foreground/40 hover:text-foreground",
                          )}
                        >
                          {cam.name.replace(/_/g, " ")}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Generate button */}
                <Button
                  onClick={handleGenerateRender}
                  disabled={renderBusy || !projectId}
                  className="w-full"
                >
                  {renderBusy ? (
                    <>
                      <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                      Rendering…
                    </>
                  ) : (
                    "Generate Render"
                  )}
                </Button>

                <p className="text-[10px] text-muted-foreground/50">
                  Tip: orient the camera in 3D Massing view first, then generate a render here.
                </p>

                {/* Loading skeleton */}
                {renderBusy && (
                  <div className="aspect-video w-full animate-pulse rounded-xl bg-muted" />
                )}

                {/* Error */}
                {renderError && (
                  <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive">
                    {renderError}
                  </div>
                )}

                {/* Result image */}
                {renderResult && !renderBusy && (
                  <div className="overflow-hidden rounded-xl border border-border shadow-[0_2px_8px_rgba(0,0,0,0.06)]">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`data:image/png;base64,${renderResult}`}
                      alt="Architectural render"
                      className="w-full"
                    />
                    <div className="flex items-center justify-between border-t border-border/60 px-3 py-2">
                      <span className="text-[10px] text-muted-foreground/70 capitalize">
                        {renderStyles.find((s) => s.id === selectedStyle)?.name ?? selectedStyle}
                        {selectedCamera && ` · ${selectedCamera.replace(/_/g, " ")}`}
                      </span>
                      <Button variant="ghost" size="sm" onClick={downloadRender}>
                        <Download className="mr-1.5 size-3.5" />
                        Download PNG
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* 2D layer toggle toolbar — top-left, always above scroll content */}
        {view === "2d" && project && (
          <div className="absolute top-3 left-3 z-10 flex items-center gap-0.5 rounded-lg border border-border/70 bg-card/90 px-1 py-0.5 shadow-[0_1px_3px_rgba(0,0,0,0.06)] backdrop-blur-sm">
            {/* Dimensions */}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Toggle dimensions"
                  aria-pressed={showDimensions}
                  onClick={() => setShowDimensions((v) => !v)}
                  className={showDimensions ? "bg-muted text-foreground" : "text-muted-foreground/50"}
                >
                  <Ruler className="size-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent side="bottom">Dimensions</TooltipContent>
            </Tooltip>

            {/* Furniture */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label="Toggle furniture"
                  aria-pressed={showFurniturePlan}
                  onClick={() => setShowFurniturePlan((v) => !v)}
                  className={cn(
                    "flex h-6 items-center rounded px-1.5 text-[10px] font-semibold transition-colors",
                    showFurniturePlan
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground/50 hover:text-muted-foreground",
                  )}
                >
                  Furn
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom">Furniture layer</TooltipContent>
            </Tooltip>

            {/* MEP layer chips — only when MEP has been generated */}
            {project.mep_plan?.generated && onToggleMepLayer && (
              <>
                <div className="mx-0.5 h-4 w-px bg-border/60" />
                {(["plumbing", "electrical", "lighting", "ac"] as const).map((sys) => {
                  const active = activeMepLayers?.has(sys) ?? false;
                  const label = sys === "plumbing" ? "P" : sys === "electrical" ? "E" : sys === "lighting" ? "L" : "AC";
                  const color = sys === "plumbing" ? "#1a6eb5" : sys === "electrical" ? "#d97706" : sys === "lighting" ? "#ca8a04" : "#0891b2";
                  return (
                    <Tooltip key={sys}>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          aria-label={`Toggle ${sys} layer`}
                          aria-pressed={active}
                          onClick={() => onToggleMepLayer(sys)}
                          style={{ color }}
                          className={cn(
                            "flex h-6 min-w-[20px] items-center justify-center rounded px-1 text-[10px] font-bold transition-opacity",
                            active ? "opacity-100" : "opacity-25 hover:opacity-60",
                          )}
                        >
                          {label}
                        </button>
                      </TooltipTrigger>
                      <TooltipContent side="bottom" className="capitalize">{sys}</TooltipContent>
                    </Tooltip>
                  );
                })}
              </>
            )}
          </div>
        )}

        {/* on-canvas room edit popover (CADAM-style) — 2D only */}
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

        {/* scale chip — 2D only; centered so it doesn't overlap reference overlay (left) or zoom cluster (right) */}
        {view === "2d" && (
          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-md border border-border bg-card px-2 py-1 font-mono text-[10px] text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)] pointer-events-none">
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
