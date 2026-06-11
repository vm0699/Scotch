import Link from "next/link";
import { Building2 } from "lucide-react";

import type { MockProjectSummary } from "@/features/project/mock-projects";

export function ProjectCard({ project }: { project: MockProjectSummary }) {
  return (
    <Link
      href={`/workspace?project=${project.id}`}
      className="group flex items-start gap-3.5 rounded-xl border border-border bg-card p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:border-muted-foreground/30 hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/50 text-muted-foreground transition-colors group-hover:text-foreground">
        <Building2 className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate text-sm font-medium tracking-tight">
          {project.name}
        </span>
        <span className="mt-0.5 block truncate text-xs text-muted-foreground">
          {project.promptSummary}
        </span>
        <span className="mt-2 block text-xs text-muted-foreground/80">
          {project.siteSize} · {project.roomCount} rooms · {project.updatedLabel}
        </span>
      </span>
    </Link>
  );
}
