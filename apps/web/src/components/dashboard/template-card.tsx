import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import type { ProjectTemplate } from "@/features/templates/templates";

function TemplateThumbnail({ template }: { template: ProjectTemplate }) {
  return (
    <svg
      viewBox="0 0 100 70"
      className="h-full w-full"
      role="img"
      aria-label={`${template.name} schematic layout`}
    >
      <rect
        x="1"
        y="1"
        width="98"
        height="68"
        rx="3"
        className="fill-background stroke-border"
        strokeWidth="1"
      />
      {template.thumbnail.map((r, i) => (
        <rect
          key={i}
          x={r.x}
          y={r.y}
          width={r.w}
          height={r.h}
          rx="1.5"
          className="fill-muted stroke-muted-foreground/50 transition-colors group-hover:fill-accent"
          strokeWidth="0.75"
        />
      ))}
    </svg>
  );
}

export function TemplateCard({ template }: { template: ProjectTemplate }) {
  return (
    <Link
      href={`/workspace?template=${template.id}`}
      className="group flex flex-col overflow-hidden rounded-xl border border-border bg-card shadow-[0_1px_2px_rgba(0,0,0,0.04)] transition-all hover:border-muted-foreground/30 hover:shadow-[0_2px_8px_rgba(0,0,0,0.06)]"
    >
      <div className="aspect-[10/6] border-b border-border bg-muted/30 p-3">
        <TemplateThumbnail template={template} />
      </div>
      <div className="flex flex-1 flex-col gap-1 p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-medium tracking-tight">
            {template.name}
          </h3>
          <span className="shrink-0 text-xs text-muted-foreground">
            {template.siteSize}
          </span>
        </div>
        <p className="text-xs leading-5 text-muted-foreground">
          {template.description}
        </p>
        <div className="mt-2 flex gap-1.5">
          {template.tags.map((tag) => (
            <Badge key={tag} variant="secondary" className="font-normal">
              {tag}
            </Badge>
          ))}
        </div>
      </div>
    </Link>
  );
}
