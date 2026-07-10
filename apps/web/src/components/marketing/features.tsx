import {
  PencilRuler,
  Ruler,
  ShieldCheck,
  Sparkles,
  Boxes,
  FileDown,
} from "lucide-react";

import { Reveal } from "@/components/marketing/reveal";

const FEATURES = [
  {
    icon: Sparkles,
    title: "Prompt to plan",
    body: "Type a brief and get a coherent, code-aware layout in seconds. Smart defaults fill the gaps and every assumption is surfaced as an editable note.",
    accent: "red",
  },
  {
    icon: PencilRuler,
    title: "Editable parameters",
    body: "Tune rooms, walls, openings and the site on-canvas or in the panel. The model is the single source of truth — edits flow everywhere.",
    accent: "ink",
  },
  {
    icon: Ruler,
    title: "Architectural 2D",
    body: "Double-line walls, door swings, window symbols, dimension lines, room labels with areas and a north arrow — drawing-standard output, not a sketch.",
    accent: "red",
  },
  {
    icon: Boxes,
    title: "Live 3D massing",
    body: "Every plan has a matching 3D massing view with orbit, camera presets and sun-study shadows — no second model to maintain.",
    accent: "ink",
  },
  {
    icon: ShieldCheck,
    title: "Validated by default",
    body: "A shared validator checks every generated and edited model before it renders or exports, so geometry stays sound across the whole pipeline.",
    accent: "red",
  },
  {
    icon: FileDown,
    title: "Professional exports",
    body: "Hand off to AutoCAD (DXF), SketchUp, Revit, Rhino, Blender, IFC and PDF sheets — one model, every format your studio already runs.",
    accent: "ink",
  },
] as const;

export function Features() {
  return (
    <section className="border-t border-border px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-6xl">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            The whole pipeline, in one place
          </h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground">
            From the first sentence to a coordinated drawing set — Scotch keeps
            the design editable at every step.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-px overflow-hidden rounded-2xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((feature, i) => {
            const Icon = feature.icon;
            return (
              <Reveal
                key={feature.title}
                delay={(i % 3) * 70}
                className="group bg-card p-7 transition-shadow duration-200 hover:shadow-md"
              >
                <div
                  className={`flex size-10 items-center justify-center rounded-lg ${feature.accent === "red" ? "tint-red" : "tint-ink"}`}
                >
                  <Icon className="size-5" />
                </div>
                <h3 className="mt-4 text-base font-medium tracking-tight">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">
                  {feature.body}
                </p>
              </Reveal>
            );
          })}
        </div>
      </div>
    </section>
  );
}
