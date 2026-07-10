import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/marketing/reveal";

export function CtaBand() {
  return (
    <section className="relative overflow-hidden border-t border-border bg-[oklch(0.13_0_0)] px-6 py-24 sm:py-32">
      {/* Subtle dot-grid overlay */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: "radial-gradient(circle, oklch(1 0 0) 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
      />

      <Reveal className="relative mx-auto max-w-2xl text-center">
        <p className="brand-text mb-3 text-sm font-semibold uppercase tracking-widest">
          Ready to design faster?
        </p>
        <h2 className="text-balance text-4xl font-semibold tracking-tight text-white sm:text-5xl">
          Start designing in plain language
        </h2>
        <p className="mt-5 text-base leading-7 text-white/60">
          Open the workspace and turn your first brief into an editable design —
          no setup, no account required.
        </p>
        <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Button asChild size="lg" className="brand-btn gap-2 px-7">
            <Link href="/workspace">
              Open Workspace
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button
            asChild
            variant="outline"
            size="lg"
            className="px-7"
            style={{
              borderColor: "rgba(255,255,255,0.18)",
              color: "rgba(255,255,255,0.80)",
              background: "rgba(255,255,255,0.05)",
            }}
          >
            <Link href="/dashboard">Browse the dashboard</Link>
          </Button>
        </div>
      </Reveal>
    </section>
  );
}
