import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const PIPELINE_STEPS = [
  "Prompt",
  "Architecture model",
  "Editable parameters",
  "2D floor plan",
  "3D massing",
  "Exports",
] as const;

export default function LandingPage() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="flex h-14 items-center justify-between px-6 sm:px-10">
        <div className="flex items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-md bg-foreground text-background text-[13px] font-semibold tracking-tight">
            S
          </span>
          <span className="text-[15px] font-semibold tracking-tight">
            Scotch
          </span>
        </div>
        <Button asChild variant="ghost" size="sm">
          <Link href="/dashboard">Dashboard</Link>
        </Button>
      </header>

      <main className="flex flex-1 flex-col items-center justify-center px-6 py-20 text-center">
        <Badge variant="secondary" className="mb-6 font-normal">
          AI-native architecture design
        </Badge>

        <h1 className="max-w-3xl text-5xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
          Text-to-design
          <br />
          for architecture
        </h1>

        <p className="mt-6 max-w-xl text-base leading-7 text-muted-foreground sm:text-lg sm:leading-8">
          Describe a building in plain language. Scotch turns it into an
          editable floor plan, 3D massing, and exports for the tools
          architects already use.
        </p>

        <div className="mt-10 flex items-center gap-3">
          <Button asChild size="lg" className="px-5">
            <Link href="/dashboard">Start Local Project</Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="px-5">
            <Link href="/workspace">Open Workspace</Link>
          </Button>
        </div>

        <div className="mt-20 flex max-w-3xl flex-wrap items-center justify-center gap-x-2 gap-y-3 text-xs text-muted-foreground">
          {PIPELINE_STEPS.map((step, i) => (
            <span key={step} className="flex items-center gap-2">
              <span className="rounded-md border border-border bg-card px-2.5 py-1.5">
                {step}
              </span>
              {i < PIPELINE_STEPS.length - 1 && (
                <span aria-hidden className="text-border">
                  →
                </span>
              )}
            </span>
          ))}
        </div>
      </main>

      <footer className="flex h-12 items-center justify-center border-t border-border px-6 text-xs text-muted-foreground">
        Scotch · local-first · deterministic generation works without an AI key
      </footer>
    </div>
  );
}
