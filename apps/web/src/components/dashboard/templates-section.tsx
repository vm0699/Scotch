"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { TemplateCard } from "@/components/dashboard/template-card";
import { createProject } from "@/features/api/client";
import {
  PROJECT_TEMPLATES,
  type ProjectTemplate,
} from "@/features/templates/templates";

export function TemplatesSection() {
  const router = useRouter();
  const [busyId, setBusyId] = useState<string | null>(null);

  async function handleSelect(template: ProjectTemplate) {
    if (busyId) return;
    setBusyId(template.id);
    try {
      const stored = await createProject({
        name: template.name,
        prompt: template.prompt,
      });
      router.push(`/workspace?project=${stored.id}`);
    } catch {
      // Engine offline: open the workspace in template mode without persistence.
      router.push(`/workspace?template=${template.id}`);
    }
  }

  return (
    <section id="templates" className="mt-10 scroll-mt-20">
      <h2 className="text-sm font-medium text-muted-foreground">Templates</h2>
      <div
        className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3"
        data-busy={busyId ?? undefined}
      >
        {PROJECT_TEMPLATES.map((template) => (
          <TemplateCard
            key={template.id}
            template={template}
            onSelect={(t) => void handleSelect(t)}
          />
        ))}
      </div>
    </section>
  );
}
