"use client";

import { useCallback, useEffect, useState } from "react";

import { DataPanel } from "@/components/workspace/data-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { PromptPanel } from "@/components/workspace/prompt-panel";
import { getSampleProject } from "@/features/api/client";
import { MOCK_ARCHITECTURE_PROJECT } from "@/features/project/mock-architecture-project";
import type { ArchitectureProject } from "@/features/project/types";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";

const NOTICE_BACKEND =
  "Loaded the validated sample from the Scotch engine — prompt parsing arrives in Phase 5.";
const NOTICE_OFFLINE =
  "Engine offline — showing the built-in sample. Start it with: npm run dev:api.";

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
  const [project, setProject] = useState<ArchitectureProject | null>(null);
  const [generating, setGenerating] = useState(false);
  const [notice, setNotice] = useState<string | undefined>(undefined);

  // Fetches the backend sample (real generation replaces this in Phase 5),
  // falling back to the bundled mock when the engine is unreachable.
  const loadSample = useCallback(async () => {
    setGenerating(true);
    try {
      const fromBackend = await getSampleProject();
      setProject(fromBackend);
      setNotice(NOTICE_BACKEND);
    } catch {
      setProject(MOCK_ARCHITECTURE_PROJECT);
      setNotice(NOTICE_OFFLINE);
    } finally {
      setGenerating(false);
    }
  }, []);

  // Opening a saved project loads the sample until storage lands (Phase 4).
  useEffect(() => {
    if (initialProjectId) {
      void loadSample();
    }
  }, [initialProjectId, loadSample]);

  function handleTemplateChange(id: string) {
    setTemplateId(id);
    const template = PROJECT_TEMPLATES.find((t) => t.id === id);
    if (template) {
      setPrompt(template.prompt);
    }
  }

  return (
    <div className="grid h-full grid-cols-1 gap-3 p-3 lg:grid-cols-[300px_minmax(0,1fr)_340px]">
      <PromptPanel
        prompt={prompt}
        onPromptChange={setPrompt}
        templateId={templateId}
        onTemplateChange={handleTemplateChange}
        onGenerate={() => void loadSample()}
        generating={generating}
        notice={notice}
      />
      <PreviewPanel project={project} />
      <DataPanel project={project} />
    </div>
  );
}
