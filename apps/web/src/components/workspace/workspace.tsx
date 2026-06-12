"use client";

import { useState } from "react";

import { DataPanel } from "@/components/workspace/data-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { PromptPanel } from "@/components/workspace/prompt-panel";
import { MOCK_ARCHITECTURE_PROJECT } from "@/features/project/mock-architecture-project";
import type { ArchitectureProject } from "@/features/project/types";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";

export function Workspace({
  initialTemplateId,
  initialProjectId,
}: {
  initialTemplateId?: string;
  initialProjectId?: string;
}) {
  const initialTemplate = PROJECT_TEMPLATES.find(
    (t) => t.id === initialTemplateId,
  );
  const [templateId, setTemplateId] = useState<string | undefined>(
    initialTemplate?.id,
  );
  const [prompt, setPrompt] = useState(initialTemplate?.prompt ?? "");
  // Opening a saved project loads the sample design until storage lands (Phase 4).
  const [project, setProject] = useState<ArchitectureProject | null>(
    initialProjectId ? MOCK_ARCHITECTURE_PROJECT : null,
  );

  function handleTemplateChange(id: string) {
    setTemplateId(id);
    const template = PROJECT_TEMPLATES.find((t) => t.id === id);
    if (template) {
      setPrompt(template.prompt);
    }
  }

  function handleGenerate() {
    // Loads the sample project; replaced by POST /generate/from-prompt in Phase 5.
    setProject(MOCK_ARCHITECTURE_PROJECT);
  }

  return (
    <div className="grid h-full grid-cols-1 gap-3 p-3 lg:grid-cols-[300px_minmax(0,1fr)_340px]">
      <PromptPanel
        prompt={prompt}
        onPromptChange={setPrompt}
        templateId={templateId}
        onTemplateChange={handleTemplateChange}
        onGenerate={handleGenerate}
      />
      <PreviewPanel project={project} />
      <DataPanel project={project} />
    </div>
  );
}
