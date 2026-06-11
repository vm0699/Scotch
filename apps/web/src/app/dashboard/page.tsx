import Link from "next/link";
import { FolderOpen, LayoutGrid, Plus, Settings, Shapes } from "lucide-react";

import { AppShell } from "@/components/layout/app-shell";
import { Sidebar } from "@/components/layout/sidebar";
import { BackendStatusCard } from "@/components/dashboard/backend-status-card";
import { ProjectCard } from "@/components/dashboard/project-card";
import { TemplateCard } from "@/components/dashboard/template-card";
import { Button } from "@/components/ui/button";
import { MOCK_RECENT_PROJECTS } from "@/features/project/mock-projects";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";

const SIDEBAR_ITEMS = [
  { label: "Projects", href: "/dashboard", icon: LayoutGrid, active: true },
  { label: "Templates", href: "/dashboard#templates", icon: Shapes },
  { label: "Open workspace", href: "/workspace", icon: FolderOpen },
  {
    label: "Settings",
    href: "/dashboard",
    icon: Settings,
    disabled: true,
    hint: "Provider and generation settings arrive in Phase 9",
  },
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
          <Button asChild>
            <Link href="/workspace">
              <Plus data-icon="inline-start" />
              New Project
            </Link>
          </Button>
        </div>

        <section className="mt-8">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-muted-foreground">
              Recent projects
            </h2>
            <span className="text-xs text-muted-foreground/70">
              Sample data — local storage lands in Phase 4
            </span>
          </div>
          <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {MOCK_RECENT_PROJECTS.map((project) => (
              <ProjectCard key={project.id} project={project} />
            ))}
          </div>
        </section>

        <section id="templates" className="mt-10 scroll-mt-20">
          <h2 className="text-sm font-medium text-muted-foreground">
            Templates
          </h2>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {PROJECT_TEMPLATES.map((template) => (
              <TemplateCard key={template.id} template={template} />
            ))}
          </div>
        </section>

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
