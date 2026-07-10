import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PipelineAnimation } from "@/components/marketing/pipeline-animation";

export function Hero() {
  return (
    <section id="product" className="relative overflow-hidden px-6 pt-20 pb-20 sm:pt-28 sm:pb-24">
      {/* single clean red wash from top */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-80"
        style={{
          background: "radial-gradient(ellipse 80% 100% at 50% 0%, oklch(0.55 0.22 25 / 0.06), transparent)",
        }}
      />

      <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
        {/* badge */}
        <span
          className="animate-fade-up brand-badge mb-6 inline-flex items-center gap-2 rounded-full px-3.5 py-1 text-xs font-medium"
        >
          <Sparkles className="size-3" />
          AI-native architecture design
        </span>

        {/* headline — first line in brand red, second in foreground */}
        <h1
          className="animate-fade-up max-w-3xl text-balance text-5xl font-semibold leading-[1.07] tracking-tight sm:text-6xl"
          style={{ animationDelay: "60ms" }}
        >
          <span className="brand-text">Text-to-design</span>
          <br />
          for architecture
        </h1>

        <p
          className="animate-fade-up mt-6 max-w-xl text-pretty text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8"
          style={{ animationDelay: "120ms" }}
        >
          Describe a building in plain language. Scotch turns it into an
          editable floor plan, 3D massing, and exports for the tools architects
          already use — AutoCAD, SketchUp, Revit, Rhino and Blender.
        </p>

        <div
          className="animate-fade-up mt-9 flex flex-col items-center gap-3 sm:flex-row"
          style={{ animationDelay: "180ms" }}
        >
          <Button asChild size="lg" className="brand-btn gap-2 px-6">
            <Link href="/workspace">
              Open Workspace
              <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="px-6">
            <Link href="/dashboard">Start a local project</Link>
          </Button>
        </div>

        <p
          className="animate-fade-up mt-4 text-xs text-muted-foreground"
          style={{ animationDelay: "240ms" }}
        >
          No account needed · Works offline · Deterministic generation without an AI key
        </p>
      </div>

      <div className="mt-16 animate-float">
        <PipelineAnimation />
      </div>
    </section>
  );
}
