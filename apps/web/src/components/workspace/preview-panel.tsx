"use client";

import { useState } from "react";
import { Box, Compass, Maximize2, Minus, PenLine, Plus } from "lucide-react";

import { Panel, PanelHeader } from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

type ViewMode = "2d" | "3d";

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

export function PreviewPanel() {
  const [view, setView] = useState<ViewMode>("2d");

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
          <span className="text-[11px] text-muted-foreground/70">
            Untitled project
          </span>
        }
      />

      <div className="relative min-h-0 flex-1 bg-muted/20" style={DOT_GRID_STYLE}>
        {view === "2d" ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
            <span className="flex size-12 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
              <Compass className="size-5" />
            </span>
            <div>
              <p className="text-sm font-medium">No design yet</p>
              <p className="mt-1 max-w-60 text-xs leading-5 text-muted-foreground">
                Describe your building in the brief and press Generate. The
                floor plan renders here.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 p-8 text-center">
            <span className="flex size-12 items-center justify-center rounded-xl border border-border bg-card text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
              <Box className="size-5" />
            </span>
            <div>
              <p className="text-sm font-medium">3D massing</p>
              <p className="mt-1 max-w-60 text-xs leading-5 text-muted-foreground">
                Walls and slabs extrude from your plan here in Phase 8.
              </p>
            </div>
          </div>
        )}

        {/* scale chip */}
        <div className="absolute bottom-3 left-3 rounded-md border border-border bg-card px-2 py-1 font-mono text-[10px] text-muted-foreground shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          ft · 1 : 100
        </div>

        {/* zoom cluster */}
        <div className="absolute bottom-3 right-3 flex items-center rounded-lg border border-border bg-card p-0.5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" disabled>
                <Minus />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">Zoom out — wired in Stage 2.5</TooltipContent>
          </Tooltip>
          <span className="min-w-11 text-center font-mono text-[11px] text-muted-foreground">
            100%
          </span>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" disabled>
                <Plus />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">Zoom in — wired in Stage 2.5</TooltipContent>
          </Tooltip>
          <div className="mx-0.5 h-4 w-px bg-border" />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" disabled>
                <Maximize2 />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="top">Fit to view — wired in Stage 2.5</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </Panel>
  );
}
