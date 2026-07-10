import { Reveal } from "@/components/marketing/reveal";

const STATS = [
  { value: "Local-first", label: "Your designs stay on your machine",           red: true  },
  { value: "No AI key",   label: "Deterministic generation always works",       red: false },
  { value: "6+ tools",    label: "AutoCAD, SketchUp, Revit, Rhino, Blender, IFC", red: true },
];

export function AboutSection() {
  return (
    <section id="about" className="border-t border-border px-6 py-20 sm:py-28">
      <div className="mx-auto grid max-w-5xl gap-12 md:grid-cols-2 md:items-center">
        <Reveal>
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Built for architects,{" "}
            <span className="brand-text">not just demos</span>
          </h2>
          <div className="mt-5 space-y-4 text-base leading-7 text-muted-foreground">
            <p>
              Scotch started from a simple frustration: the gap between an idea
              and a reviewable design is still measured in hours. The first
              sketch, the 3D study, the area schedule, the export — all done by
              hand, all kept in sync by hand.
            </p>
            <p>
              We treat the architecture model as a single source of truth.
              Generation, editing, 2D, 3D and every export read from and write to
              the same validated model — so describing a change is all it takes
              to update the whole set.
            </p>
          </div>
        </Reveal>

        <Reveal delay={80} className="grid gap-3">
          {STATS.map((stat) => (
            <div
              key={stat.value}
              className="flex items-center gap-4 rounded-xl border border-border bg-card p-5"
            >
              <div
                className={`flex size-10 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${stat.red ? "tint-red" : "tint-ink"}`}
              >
                ✓
              </div>
              <div>
                <div className="text-[15px] font-semibold tracking-tight">{stat.value}</div>
                <div className="mt-0.5 text-sm text-muted-foreground">{stat.label}</div>
              </div>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
