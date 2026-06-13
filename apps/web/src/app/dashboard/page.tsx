import { FolderOpen, LayoutGrid, Settings, Shapes } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Sidebar } from "@/components/layout/sidebar";
import { BackendStatusCard } from "@/components/dashboard/backend-status-card";
import {
  NewProjectButton,
  ProjectsSection,
} from "@/components/dashboard/projects-section";
import { TemplatesSection } from "@/components/dashboard/templates-section";

const SIDEBAR_ITEMS = [
  { label: "Projects", href: "/dashboard", icon: LayoutGrid, active: true },
  { label: "Templates", href: "/dashboard#templates", icon: Shapes },
  { label: "Open workspace", href: "/workspace", icon: FolderOpen },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

export default function DashboardPage() {
  return (
    <AppShell
      active="/dashboard"
      sidebar={<Sidebar items={SIDEBAR_ITEMS} footer="Scotch 0.1.0 · local" />}
    >
      <div className="mx-auto w-full max-w-6xl px-6 py-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Start from a prompt or a template — every design stays editable.
            </p>
          </div>
          <NewProjectButton />
        </div>

        <ProjectsSection />
        <TemplatesSection />

        <section className="mt-10 max-w-md">
          <h2 className="text-sm font-medium text-muted-foreground">System</h2>
          <div className="mt-3">
            <BackendStatusCard />
          </div>
        </section>
      </div>
    </AppShell>
  );
}
