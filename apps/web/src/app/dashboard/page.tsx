import Link from "next/link";

import { TopBar } from "@/components/layout/top-bar";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  return (
    <div className="flex flex-1 flex-col bg-muted/40">
      <TopBar active="/dashboard" />

      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Create a project and design from a prompt.
            </p>
          </div>
          <Button asChild>
            <Link href="/workspace">New Project</Link>
          </Button>
        </div>

        <section className="mt-8">
          <h2 className="text-sm font-medium text-muted-foreground">
            Recent projects
          </h2>
          <div className="mt-3 flex h-40 items-center justify-center rounded-xl border border-dashed border-border bg-card text-sm text-muted-foreground">
            Saved projects will appear here once local storage lands (Phase 4).
          </div>
        </section>

        <section className="mt-10">
          <h2 className="text-sm font-medium text-muted-foreground">
            Templates
          </h2>
          <div className="mt-3 flex h-40 items-center justify-center rounded-xl border border-dashed border-border bg-card text-sm text-muted-foreground">
            Starter templates — 2BHK Apartment, 3BHK Villa, Studio, Small Cafe
            — arrive with the dashboard UI (Phase 2).
          </div>
        </section>
      </main>
    </div>
  );
}
