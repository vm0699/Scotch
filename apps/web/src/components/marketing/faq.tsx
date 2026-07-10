import { Plus } from "lucide-react";

import { Reveal } from "@/components/marketing/reveal";

const FAQS = [
  {
    q: "Do I need an AI API key to use Scotch?",
    a: "No. Scotch ships with deterministic, rule-based generation that works with no key at all. Adding an Anthropic or OpenAI-compatible key simply unlocks richer prompt understanding — the deterministic path is always the fallback.",
  },
  {
    q: "Where are my projects stored?",
    a: "Locally, by default — under your Scotch data folder on this machine. Cloud sync is optional and slots in behind the same model when you sign in.",
  },
  {
    q: "How do the desktop integrations work?",
    a: "Each integration targets software you already have installed. SketchUp installs a Scotch extension for one-click import and sync; Revit adds a ribbon add-in; Rhino and Blender run an exported script. Generate a design, then send it across from the workspace.",
  },
  {
    q: "Can I edit what the AI generates?",
    a: "Everything is editable. Adjust rooms, walls, openings and the site on-canvas or in the parameter panel — the model is the single source of truth, so edits flow into the 2D plan, 3D massing and every export.",
  },
  {
    q: "What can I export?",
    a: "AutoCAD DXF, SketchUp, Revit, Rhino, Blender, IFC, PDF drawing sheets, PNG and room/area schedules — all from the same validated model.",
  },
];

export function Faq() {
  return (
    <section id="faq" className="border-t border-border bg-muted/30 px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-3xl">
        <Reveal className="text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Frequently asked
          </h2>
        </Reveal>

        <div className="mt-12 divide-y divide-border overflow-hidden rounded-2xl border border-border bg-card">
          {FAQS.map((faq) => (
            <details key={faq.q} className="group px-6">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 py-5 text-sm font-medium transition-colors [&::-webkit-details-marker]:hidden group-open:text-[var(--brand)]">
                {faq.q}
                <Plus
                  className="size-4 shrink-0 transition-all duration-200 group-open:rotate-45 group-open:text-[var(--brand)] text-muted-foreground"
                />
              </summary>
              <p className="pb-5 text-sm leading-6 text-muted-foreground">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
