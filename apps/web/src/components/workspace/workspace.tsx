"use client";

import { useState } from "react";

import { DataPanel } from "@/components/workspace/data-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { PromptPanel } from "@/components/workspace/prompt-panel";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";

export function Workspace({ initialTemplateId }: { initialTemplateId?: string }) {
  const initialTemplate = PROJECT_TEMPLATES.find(
    (t) => t.id === initialTemplateId,
  );
  const [templateId, setTemplateId] = useState<string | undefined>(
    initialTemplate?.id,
  );
  const [prompt, setPrompt] = useState(initialTemplate?.prompt ?? "");

  function handleTemplateChange(id: string) {
    setTemplateId(id);
    const template = PROJECT_TEMPLATES.find((t) => t.id === id);
    if (template) {
      setPrompt(template.prompt);
    }
  }

  function handleGenerate() {
    // Wired to POST /generate/from-prompt in Phase 5.
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
      <PreviewPanel />
      <DataPanel />
    </div>
  );
}
