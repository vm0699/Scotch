"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import {
  ArrowRight,
  Box,
  FileDown,
  LayoutGrid,
  MessageSquareText,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { FloorPlanSvg } from "@/features/plan/floor-plan-svg";
import { MOCK_ARCHITECTURE_PROJECT } from "@/features/project/mock-architecture-project";

const MassingViewer = dynamic(
  () => import("@/features/massing/massing-viewer").then((m) => m.MassingViewer),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full w-full items-center justify-center bg-muted/40 text-xs text-muted-foreground">
        Loading 3D massing…
      </div>
    ),
  },
);

const PROMPT_TEXT =
  "Design a 2BHK home on a 30 × 50 ft east-facing plot with an open kitchen and a master suite.";

const STAGES = [
  { id: "prompt", label: "Prompt", icon: MessageSquareText },
  { id: "plan", label: "Floor plan", icon: LayoutGrid },
  { id: "massing", label: "3D massing", icon: Box },
  { id: "exports", label: "Exports", icon: FileDown },
] as const;

const EXPORT_FORMATS = [
  "DXF", "SketchUp", "Revit", "Rhino",
  "Blender", "IFC", "PDF sheet", "PNG",
];

/* stable colour constant — primary red (single accent hue, no gradient) */
const C_RED      = "oklch(0.55 0.22 25)";
const C_RED_RING = "oklch(0.55 0.22 25 / 18%)";

const ADVANCE_MS = 3400;

export function PipelineAnimation() {
  const [stage, setStage] = React.useState(0);
  const [inView, setInView] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) { setInView(false); return; }
    const obs = new IntersectionObserver(
      ([entry]) => setInView(entry.isIntersecting),
      { threshold: 0.4 },
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  React.useEffect(() => {
    if (!inView) return;
    const t = setInterval(() => setStage((s) => (s + 1) % STAGES.length), ADVANCE_MS);
    return () => clearInterval(t);
  }, [inView]);

  const showMassing = stage === 2 && inView;

  return (
    <div ref={containerRef} className="mx-auto w-full max-w-3xl">
      {/* App frame */}
      <div
        className="overflow-hidden rounded-2xl border border-border bg-card shadow-[0_4px_32px_-8px_oklch(0.55_0.22_25_/_0.12)]"
      >
        {/* Window chrome */}
        <div className="flex h-9 items-center gap-1.5 border-b border-border bg-muted/40 px-3.5">
          <span className="size-2.5 rounded-full bg-border" />
          <span className="size-2.5 rounded-full bg-border" />
          <span className="size-2.5 rounded-full bg-border" />
          <span className="ml-3 text-xs font-medium brand-text">
            {STAGES[stage].label}
          </span>
        </div>

        <div className="relative h-[380px] bg-[#fafafa] dark:bg-background">
          {/* Stage 0 — Prompt */}
          <StagePanel active={stage === 0}>
            <div className="flex h-full flex-col items-center justify-center px-8">
              <div
                className="w-full max-w-md rounded-xl border bg-card p-4 shadow-sm"
                style={{ borderColor: C_RED_RING }}
              >
                <div className="mb-2 flex items-center gap-2 text-xs brand-text">
                  <MessageSquareText className="size-3.5" />
                  Describe your building
                </div>
                <p className="text-[15px] leading-relaxed">
                  {PROMPT_TEXT}
                  <span
                    className="ml-0.5 inline-block h-4 w-px translate-y-0.5 animate-pulse align-middle"
                    style={{ background: C_RED }}
                  />
                </p>
              </div>
              <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                <span className="size-1.5 animate-pulse rounded-full" style={{ background: C_RED }} />
                Generating an editable architecture model…
              </div>
            </div>
          </StagePanel>

          {/* Stage 1 — Floor plan */}
          <StagePanel active={stage === 1}>
            <div className="flex h-full items-center justify-center p-5">
              <FloorPlanSvg project={MOCK_ARCHITECTURE_PROJECT} className="h-full w-auto max-w-full" />
            </div>
          </StagePanel>

          {/* Stage 2 — 3D massing */}
          <StagePanel active={stage === 2}>
            <div className="h-full w-full">
              {showMassing ? (
                <MassingViewer project={MOCK_ARCHITECTURE_PROJECT} />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-muted/40 text-xs text-muted-foreground">
                  3D massing
                </div>
              )}
            </div>
          </StagePanel>

          {/* Stage 3 — Exports */}
          <StagePanel active={stage === 3}>
            <div className="flex h-full flex-col items-center justify-center gap-5 px-8">
              <div className="text-sm text-muted-foreground">
                One model, every professional format
              </div>
              <div className="grid w-full max-w-md grid-cols-4 gap-2.5">
                {EXPORT_FORMATS.map((fmt, i) => (
                  <div
                    key={fmt}
                    style={{ transitionDelay: `${i * 55}ms` }}
                    className={cn(
                      "flex items-center justify-center rounded-lg border border-transparent px-2 py-3 text-center text-xs font-medium transition-all duration-500",
                      i % 2 === 0 ? "tint-red" : "tint-ink",
                      stage === 3 ? "translate-y-0 opacity-100" : "translate-y-2 opacity-0",
                    )}
                  >
                    {fmt}
                  </div>
                ))}
              </div>
            </div>
          </StagePanel>
        </div>
      </div>

      {/* Stage stepper */}
      <div className="mt-5 flex flex-wrap items-center justify-center gap-1.5">
        {STAGES.map((s, i) => {
          const Icon = s.icon;
          const active = i === stage;
          return (
            <React.Fragment key={s.id}>
              <button
                type="button"
                onClick={() => setStage(i)}
                className={cn(
                  "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-all duration-200",
                  active
                    ? "border-transparent text-white"
                    : "border-border text-muted-foreground hover:border-muted-foreground hover:text-foreground",
                )}
                style={active ? { backgroundColor: C_RED } : undefined}
              >
                <Icon className="size-3.5" />
                {s.label}
              </button>
              {i < STAGES.length - 1 && (
                <ArrowRight className="size-3.5 text-border" aria-hidden />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

function StagePanel({ active, children }: { active: boolean; children: React.ReactNode }) {
  return (
    <div
      aria-hidden={!active}
      className={cn(
        "absolute inset-0 transition-opacity duration-500",
        active ? "opacity-100" : "pointer-events-none opacity-0",
      )}
    >
      {children}
    </div>
  );
}
