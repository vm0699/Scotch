"use client";

import * as React from "react";
import Link from "next/link";
import { CheckCircle2, Download, ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  API_BASE_URL,
  getSystemIntegrations,
  type IntegrationKey,
  type SystemIntegrations,
} from "@/features/api/client";
import { Reveal } from "@/components/marketing/reveal";

interface PluginMeta {
  key: IntegrationKey;
  name: string;
  blurb: string;
  secondary?: { label: string; href: string; download?: boolean };
  note?: string;
}

const PLUGINS: PluginMeta[] = [
  {
    key: "sketchup",
    name: "SketchUp",
    blurb:
      "Install the Scotch extension for one-click import and two-way sync of rooms and openings.",
    secondary: {
      label: "Download extension (.rbz)",
      href: `${API_BASE_URL}/integrations/sketchup/extension`,
      download: true,
    },
  },
  {
    key: "revit",
    name: "Revit",
    blurb:
      "A C# add-in adds a Scotch ribbon — import the model as levels, walls, rooms and openings, then sync edits back.",
    note: "Generate, then export the Revit package from the workspace.",
  },
  {
    key: "rhino",
    name: "Rhino + Grasshopper",
    blurb:
      "Run an exported Python script in Rhino, or drive a live parametric model from a Grasshopper definition.",
    note: "Export the Rhino script from a project in the workspace.",
  },
  {
    key: "blender",
    name: "Blender",
    blurb:
      "A self-contained Python script rebuilds the scene with materials, cameras and lighting — render-ready.",
    note: "Export the Blender script from a project in the workspace.",
  },
];

/* Alternate red / ink per card */
const CARD_ACCENT = ["tint-red", "tint-ink", "tint-red", "tint-ink"] as const;

type DetectState =
  | { status: "loading" }
  | { status: "unavailable" }
  | { status: "ready"; data: SystemIntegrations };

export function IntegrationsSection() {
  const [state, setState] = React.useState<DetectState>({ status: "loading" });

  React.useEffect(() => {
    const ctrl = new AbortController();
    getSystemIntegrations(ctrl.signal)
      .then((data) => setState({ status: "ready", data }))
      .catch(() => setState({ status: "unavailable" }));
    return () => ctrl.abort();
  }, []);

  return (
    <section
      id="integrations"
      className="brand-section-bg border-t border-border px-6 py-20 sm:py-28"
    >
      <div className="mx-auto max-w-6xl">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Built for the tools you already run
          </h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground">
            Scotch is the front of your workflow, not a replacement for it. Send
            a design straight into your desktop software — Scotch even detects
            what&apos;s installed on this machine.
          </p>
        </Reveal>

        {state.status === "unavailable" && (
          <Reveal>
            <p className="mx-auto mt-6 max-w-xl rounded-lg border border-border bg-card px-4 py-2.5 text-center text-xs text-muted-foreground">
              Local detection is unavailable — start the Scotch backend to see
              what&apos;s installed on this PC.
            </p>
          </Reveal>
        )}

        <div className="mt-12 grid gap-4 sm:grid-cols-2">
          {PLUGINS.map((plugin, i) => {
            return (
              <Reveal key={plugin.key} delay={i * 60}>
                <div className="flex h-full flex-col rounded-2xl border border-border bg-card p-7 transition-shadow duration-200 hover:shadow-lg">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div
                        className={`mb-2 inline-flex size-9 items-center justify-center rounded-lg text-sm font-bold ${CARD_ACCENT[i]}`}
                      >
                        {plugin.name.charAt(0)}
                      </div>
                      <h3 className="text-lg font-medium tracking-tight">{plugin.name}</h3>
                    </div>
                    <DetectionBadge state={state} pluginKey={plugin.key} />
                  </div>

                  <p className="mt-3 text-sm leading-6 text-muted-foreground">{plugin.blurb}</p>

                  <div className="mt-5 flex flex-wrap items-center gap-2">
                    <Button asChild size="sm" className="brand-btn gap-1.5">
                      <Link href="/workspace">
                        Open in workspace
                        <ArrowRight className="size-3.5" />
                      </Link>
                    </Button>
                    {plugin.secondary && (
                      <Button asChild variant="ghost" size="sm">
                        <a href={plugin.secondary.href} download={plugin.secondary.download}>
                          <Download className="size-3.5" />
                          {plugin.secondary.label}
                        </a>
                      </Button>
                    )}
                  </div>

                  {plugin.note && (
                    <p className="mt-3 text-xs text-muted-foreground/70">{plugin.note}</p>
                  )}
                </div>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function DetectionBadge({ state, pluginKey }: { state: DetectState; pluginKey: IntegrationKey }) {
  if (state.status === "loading") {
    return <Pill className="animate-pulse text-muted-foreground">Checking…</Pill>;
  }
  if (state.status === "unavailable") {
    return <Pill className="text-muted-foreground/60">Detection off</Pill>;
  }
  const status = state.data.integrations[pluginKey];
  if (status?.installed) {
    return (
      <Pill className="border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
        <CheckCircle2 className="size-3" />
        Detected{status.version ? ` · ${status.version}` : ""}
      </Pill>
    );
  }
  return <Pill className="text-muted-foreground/60">Not detected</Pill>;
}

function Pill({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border border-border px-2 py-0.5 text-[11px] font-medium",
        className,
      )}
    >
      {children}
    </span>
  );
}
