"use client";

import { useCallback, useEffect, useState } from "react";

import { DataPanel } from "@/components/workspace/data-panel";
import { OptionsPanel } from "@/components/workspace/options-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { PromptPanel } from "@/components/workspace/prompt-panel";
import {
  ApiError,
  generateFromPrompt,
  generateOptions,
  getGenerationSettings,
  getProject,
  regenerateProject,
  updateProject,
  type ParameterChange,
} from "@/features/api/client";
import { MOCK_ARCHITECTURE_PROJECT } from "@/features/project/mock-architecture-project";
import type { ArchitectureProject, DesignOption } from "@/features/project/types";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";

type GenerationMode = "deterministic" | "ai" | "hybrid";

const NOTICE_UNSAVED =
  "Generated (not saved — open a project from the dashboard to persist designs).";
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
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null);
  const [editBusy, setEditBusy] = useState(false);
  const [historyKey, setHistoryKey] = useState(0);

  // Phase 9 — generation mode + AI availability
  const [generationMode, setGenerationMode] = useState<GenerationMode>("deterministic");
  const [aiAvailable, setAiAvailable] = useState(false);

  // Phase 10 — design options
  const [designOptions, setDesignOptions] = useState<DesignOption[] | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);

  // Phase 9 — fetch generation settings once on mount to unlock AI mode tab
  useEffect(() => {
    getGenerationSettings()
      .then((s) => setAiAvailable(s.anthropic_configured || s.openai_configured))
      .catch(() => {});
  }, []);

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
        if (stored.options && stored.options.length > 0) {
          setDesignOptions(stored.options);
        }
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

  // Stage 5.5 — generation from prompt, persisted to the open project.
  const handleGenerate = useCallback(async () => {
    setGenerating(true);
    try {
      const { project: design, summary } = await generateFromPrompt(
        prompt,
        generationMode,
      );
      setProject(design);
      if (storedId) {
        await updateProject(storedId, { prompt, project: design, change_type: "generate" });
        setHistoryKey((k) => k + 1);
        setNotice(`${summary} Saved to your project.`);
      } else {
        setNotice(`${summary} ${NOTICE_UNSAVED}`);
      }
    } catch {
      setProject(MOCK_ARCHITECTURE_PROJECT);
      setNotice(NOTICE_OFFLINE);
    } finally {
      setGenerating(false);
    }
  }, [storedId, prompt, generationMode]);

  // Phase 10 — generate compact / balanced / spacious options.
  const handleGenerateOptions = useCallback(async () => {
    setShowOptions(true);
    setOptionsLoading(true);
    setDesignOptions(null);
    setSelectedOptionId(null);
    try {
      const { options } = await generateOptions(prompt, generationMode);
      setDesignOptions(options);
      if (storedId) {
        await updateProject(storedId, { options, change_type: "option" });
        setHistoryKey((k) => k + 1);
      }
    } catch {
      setShowOptions(false);
      setNotice("Could not generate options — engine offline.");
    } finally {
      setOptionsLoading(false);
    }
  }, [prompt, generationMode, storedId]);

  // Phase 10 — apply a selected option as the active design.
  const handleApplyOption = useCallback(
    async (option: DesignOption) => {
      setSelectedOptionId(option.option_id);
      setProject(option.preview);
      if (storedId) {
        try {
          await updateProject(storedId, { prompt, project: option.preview, change_type: "option" });
          setHistoryKey((k) => k + 1);
          setNotice(`${option.variant.charAt(0).toUpperCase() + option.variant.slice(1)} option applied and saved.`);
        } catch {
          setNotice("Option applied locally — engine offline, not saved.");
        }
      } else {
        setNotice(`${option.variant.charAt(0).toUpperCase() + option.variant.slice(1)} option applied. ${NOTICE_UNSAVED}`);
      }
    },
    [storedId, prompt],
  );

  // Phase 6 — apply parameter/room edits via the regeneration engine.
  const handleApplyChanges = useCallback(
    async (changes: ParameterChange[]) => {
      if (!project) return;
      setEditBusy(true);
      try {
        const { project: updated, summary } = await regenerateProject(
          project,
          changes,
        );
        setProject(updated);
        if (storedId) {
          await updateProject(storedId, { project: updated, change_type: "regenerate" });
          setHistoryKey((k) => k + 1);
          setNotice(`${summary} Saved.`);
        } else {
          setNotice(summary);
        }
      } catch (error) {
        setNotice(
          error instanceof ApiError && error.status === 422
            ? "Edit rejected — a value was out of range."
            : NOTICE_OFFLINE,
        );
      } finally {
        setEditBusy(false);
      }
    },
    [project, storedId],
  );

  // Phase 19 — restore a version snapshot as the active design.
  const handleRestoreVersion = useCallback(
    (stored: import("@/features/api/client").StoredProject) => {
      if (stored.project) setProject(stored.project);
      setHistoryKey((k) => k + 1);
      setNotice("Restored to a previous version.");
    },
    [],
  );

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
        onGenerateOptions={() => void handleGenerateOptions()}
        generating={generating}
        notice={notice}
        mode={generationMode}
        onModeChange={setGenerationMode}
        aiAvailable={aiAvailable}
      />

      {/* Center column: options panel (when open) + floor plan canvas stacked */}
      <div className="flex min-h-0 flex-col gap-3">
        {showOptions && (
          <OptionsPanel
            options={designOptions}
            loading={optionsLoading}
            selectedOptionId={selectedOptionId}
            onApply={(opt) => void handleApplyOption(opt)}
            onClose={() => setShowOptions(false)}
          />
        )}
        <PreviewPanel
          project={project}
          projectId={storedId ?? undefined}
          title={title}
          onRename={(name) => void handleRename(name)}
          selectedRoomId={selectedRoomId}
          onSelectRoom={setSelectedRoomId}
          editBusy={editBusy}
          onApplyRoomEdit={(changes) => void handleApplyChanges(changes)}
        />
      </div>

      <DataPanel
        project={project}
        storedId={storedId}
        selectedRoomId={selectedRoomId}
        onSelectRoom={setSelectedRoomId}
        editBusy={editBusy}
        onApplyChanges={(changes) => void handleApplyChanges(changes)}
        historyKey={historyKey}
        onRestoreVersion={handleRestoreVersion}
      />
    </div>
  );
}
