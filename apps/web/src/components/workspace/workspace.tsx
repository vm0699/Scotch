"use client";

import { useCallback, useEffect, useState } from "react";

import { DataPanel } from "@/components/workspace/data-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { PromptPanel } from "@/components/workspace/prompt-panel";
import {
  ApiError,
  getProject,
  getSampleProject,
  updateProject,
} from "@/features/api/client";
import { MOCK_ARCHITECTURE_PROJECT } from "@/features/project/mock-architecture-project";
import type { ArchitectureProject } from "@/features/project/types";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";

const NOTICE_SAVED =
  "Design generated and saved to your project — prompt parsing arrives in Phase 5.";
const NOTICE_UNSAVED =
  "Design generated (not saved — open a project from the dashboard to persist).";
const NOTICE_OFFLINE =
  "Engine offline — showing the built-in sample. Start it with: npm run dev:api.";
const NOTICE_NOT_FOUND =
  "That project no longer exists — create a new one from the dashboard.";

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
  const [storedId, setStoredId] = useState<string | null>(null);
  const [title, setTitle] = useState("Untitled project");
  const [generating, setGenerating] = useState(false);
  const [notice, setNotice] = useState<string | undefined>(undefined);

  // Stage 4.6 — load the saved project by id.
  useEffect(() => {
    if (!initialProjectId) return;
    let cancelled = false;
    (async () => {
      try {
        const stored = await getProject(initialProjectId);
        if (cancelled) return;
        setStoredId(stored.id);
        setTitle(stored.name);
        setPrompt(stored.prompt ?? "");
        setProject(stored.project ?? null);
      } catch (error) {
        if (cancelled) return;
        setNotice(
          error instanceof ApiError && error.status === 404
            ? NOTICE_NOT_FOUND
            : NOTICE_OFFLINE,
        );
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialProjectId]);

  // Generate: fetch the sample design (real engine in Phase 5) and persist it
  // to the open project (Stage 4.7).
  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    try {
      const design = await getSampleProject();
      setProject(design);
      if (storedId) {
        await updateProject(storedId, { prompt, project: design });
        setNotice(NOTICE_SAVED);
      } else {
        setNotice(NOTICE_UNSAVED);
      }
    } catch {
      setProject(MOCK_ARCHITECTURE_PROJECT);
      setNotice(NOTICE_OFFLINE);
    } finally {
      setGenerating(false);
    }
  }, [storedId, prompt]);

  // Stage 4.7 — rename persists when the project is saved.
  const handleRename = useCallback(
    async (name: string) => {
      const next = name.trim();
      if (!next) return;
      setTitle(next);
      if (storedId) {
        try {
          await updateProject(storedId, { name: next });
        } catch {
          setNotice(NOTICE_OFFLINE);
        }
      }
    },
    [storedId],
  );

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
        onGenerate={() => void handleGenerate()}
        generating={generating}
        notice={notice}
      />
      <PreviewPanel
        project={project}
        title={title}
        onRename={(name) => void handleRename(name)}
      />
      <DataPanel project={project} />
    </div>
  );
}
