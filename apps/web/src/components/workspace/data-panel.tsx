"use client";

import {
  Braces,
  FileBox,
  FileCode2,
  FileImage,
  ShieldCheck,
} from "lucide-react";

import {
  Panel,
  PanelBody,
  PanelHeader,
  PanelSection,
} from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

function GhostRow({ label, width }: { label: string; width: string }) {
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-xs text-muted-foreground/60">{label}</span>
      <span
        className="h-5 rounded-md bg-muted"
        style={{ width }}
        aria-hidden
      />
    </div>
  );
}

const EXPORT_FORMATS = [
  { label: "JSON", icon: Braces },
  { label: "SVG", icon: FileCode2 },
  { label: "PNG", icon: FileImage },
  { label: "DXF", icon: FileBox },
] as const;

export function DataPanel() {
  return (
    <Panel>
      <PanelHeader title="Design Data" />
      <PanelBody>
        <PanelSection title="Parameters">
          <div className="divide-y divide-border/60">
            <GhostRow label="Site width" width="72px" />
            <GhostRow label="Site depth" width="72px" />
            <GhostRow label="Orientation" width="88px" />
            <GhostRow label="Floors" width="56px" />
          </div>
          <p className="mt-2.5 text-[11px] leading-4 text-muted-foreground/70">
            Generate a design to edit its parameters — here and directly on
            the plan.
          </p>
        </PanelSection>

        <PanelSection title="Room Schedule">
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
        </PanelSection>

        <PanelSection title="Exports">
          <div className="grid grid-cols-2 gap-2">
            {EXPORT_FORMATS.map((format) => (
              <Tooltip key={format.label}>
                <TooltipTrigger asChild>
                  <span>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled
                      className="w-full justify-start gap-2"
                    >
                      <format.icon className="size-3.5 text-muted-foreground" />
                      {format.label}
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent side="top">Exports arrive in Phase 7</TooltipContent>
              </Tooltip>
            ))}
          </div>
        </PanelSection>

        <PanelSection title="Warnings">
          <div className="flex items-center gap-2.5 rounded-lg border border-border bg-muted/40 px-3 py-2.5">
            <ShieldCheck className="size-4 text-muted-foreground" />
            <p className="text-xs leading-5 text-muted-foreground">
              Design checks run after generation.
            </p>
          </div>
        </PanelSection>
      </PanelBody>
    </Panel>
  );
}
