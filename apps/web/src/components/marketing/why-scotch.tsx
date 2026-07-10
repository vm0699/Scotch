import { Check, X } from "lucide-react";

import { Reveal } from "@/components/marketing/reveal";

const TRADITIONAL = [
  "Start from a blank canvas every time",
  "Redraw 2D and 3D separately, keep them in sync by hand",
  "Manual area take-offs and code checks",
  "Hours before the first reviewable option",
];

const SCOTCH = [
  "Describe the brief and get a first layout in seconds",
  "One model drives 2D, 3D and every export at once",
  "Areas, validation and compliance computed automatically",
  "Iterate on options in minutes, fully editable",
];

export function WhyScotch() {
  return (
    <section className="border-t border-border px-6 py-20 sm:py-28">
      <div className="mx-auto max-w-5xl">
        <Reveal className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">Why Scotch</h2>
          <p className="mt-4 text-base leading-7 text-muted-foreground">
            The early-stage design loop, compressed — without giving up the
            precision your downstream tools expect.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-6 md:grid-cols-2">
          {/* Traditional CAD — neutral */}
          <Reveal className="rounded-2xl border border-border bg-muted/20 p-8">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
              Traditional CAD
            </h3>
            <ul className="mt-5 space-y-4">
              {TRADITIONAL.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-6 text-muted-foreground">
                  <X className="mt-0.5 size-4 shrink-0 text-muted-foreground/40" />
                  {item}
                </li>
              ))}
            </ul>
          </Reveal>

          {/* With Scotch — red accented */}
          <Reveal delay={80}>
            <div
              className="rounded-2xl border bg-card p-8 shadow-sm"
              style={{ borderColor: "oklch(0.55 0.22 25 / 28%)" }}
            >
            <h3 className="brand-text text-xs font-semibold uppercase tracking-widest">
              With Scotch
            </h3>
            <ul className="mt-5 space-y-4">
              {SCOTCH.map((item) => (
                <li key={item} className="flex gap-3 text-sm leading-6">
                  <Check className="brand-text mt-0.5 size-4 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
