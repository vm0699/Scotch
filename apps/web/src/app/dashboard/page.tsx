import Link from "next/link";
import { FolderOpen, LayoutGrid, Settings, Shapes } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Sidebar } from "@/components/layout/sidebar";
import { Button } from "@/components/ui/button";

const SIDEBAR_ITEMS = [
  { label: "Projects", href: "/dashboard", icon: LayoutGrid, active: true },
  {
    label: "Templates",
    href: "/dashboard",
    icon: Shapes,
    disabled: true,
    hint: "Arrives in Stage 2.2",
  },
  {
    label: "Open project",
    href: "/workspace",
    icon: FolderOpen,
  },
  {
    label: "Settings",
    href: "/dashboard",
    icon: Settings,
    disabled: true,
    hint: "Arrives in Phase 9",
  },
];

export default function DashboardPage() {
  return (
    <AppShell
      active="/dashboard"
      sidebar={<Sidebar items={SIDEBAR_ITEMS} footer="Scotch 0.1.0 · local" />}
    >
      <div className="mx-auto w-full max-w-6xl px-6 py-10">
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
            — arrive with the dashboard UI (Stage 2.2).
          </div>
        </section>
      </div>
    </AppShell>
  );
}
