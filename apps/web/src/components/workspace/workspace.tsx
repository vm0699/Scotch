"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { ChatPanel } from "@/components/workspace/chat-panel";
import { DataPanel } from "@/components/workspace/data-panel";
import { OptionsPanel } from "@/components/workspace/options-panel";
import { PreviewPanel } from "@/components/workspace/preview-panel";
import { PromptPanel } from "@/components/workspace/prompt-panel";
import {
  API_BASE_URL,
  ApiError,
  deleteDetail,
  editRate,
  generateDetail,
  generateFromPrompt,
  generateMep,
  generateOptions,
  getGenerationSettings,
  getProject,
  regenerateProject,
  updateProject,
  type DetailType,
  type MEPSystem,
  type ParameterChange,
  type StoredProject,
} from "@/features/api/client";
import { MOCK_ARCHITECTURE_PROJECT } from "@/features/project/mock-architecture-project";
import type { ArchitectureProject, DesignOption } from "@/features/project/types";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";

type GenerationMode = "deterministic" | "ai" | "hybrid";

const MSG_UNSAVED =
  "Generated (not saved — open a project from the dashboard to persist designs).";
const MSG_OFFLINE =
  "Engine offline — showing the built-in sample. Start the API with: npm run dev:api";
const MSG_NOT_FOUND =
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

  const [generationMode, setGenerationMode] = useState<GenerationMode>("deterministic");
  const [aiAvailable, setAiAvailable] = useState(false);

  const [designOptions, setDesignOptions] = useState<DesignOption[] | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);

  // Phase 29: MEP state
  const [activeMepLayers, setActiveMepLayers] = useState<Set<MEPSystem>>(
    new Set<MEPSystem>(["plumbing", "electrical", "lighting", "ac"]),
  );
  const [selectedMepPointId, setSelectedMepPointId] = useState<string | null>(null);
  const [mepGenerating, setMepGenerating] = useState(false);

  // Phase 30: Detail Drawing state
  const [detailGenerating, setDetailGenerating] = useState(false);

  // Phase 31: BOQ state
  const [boqCalculating, setBoqCalculating] = useState(false);

  useEffect(() => {
    getGenerationSettings()
      .then((s) => setAiAvailable(s.anthropic_configured || s.openai_configured))
      .catch(() => {});
  }, []);

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
        const msg =
          error instanceof ApiError && error.status === 404
            ? MSG_NOT_FOUND
            : MSG_OFFLINE;
        toast.error(msg, { duration: 6000 });
        setNotice(msg);
      }
    })();
    return () => { cancelled = true; };
  }, [initialProjectId]);

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
        setNotice(`${summary} Saved.`);
      } else {
        setNotice(`${summary} ${MSG_UNSAVED}`);
      }
    } catch {
      setProject(MOCK_ARCHITECTURE_PROJECT);
      setNotice(MSG_OFFLINE);
      toast.error(MSG_OFFLINE, { duration: 6000 });
    } finally {
      setGenerating(false);
    }
  }, [storedId, prompt, generationMode]);

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
      toast.error("Could not generate options — engine offline.", { duration: 5000 });
    } finally {
      setOptionsLoading(false);
    }
  }, [prompt, generationMode, storedId]);

  const handleApplyOption = useCallback(
    async (option: DesignOption) => {
      setSelectedOptionId(option.option_id);
      setProject(option.preview);
      const label = option.variant.charAt(0).toUpperCase() + option.variant.slice(1);
      if (storedId) {
        try {
          await updateProject(storedId, { prompt, project: option.preview, change_type: "option" });
          setHistoryKey((k) => k + 1);
          toast.success(`${label} option applied and saved.`);
        } catch {
          toast.error("Option applied locally — engine offline, not saved.", { duration: 5000 });
        }
      } else {
        toast.info(`${label} option applied. ${MSG_UNSAVED}`, { duration: 5000 });
      }
    },
    [storedId, prompt],
  );

  const handleApplyChanges = useCallback(
    async (changes: ParameterChange[]) => {
      if (!project) return;
      setEditBusy(true);
      try {
        const { project: updated, summary } = await regenerateProject(project, changes);
        setProject(updated);
        if (storedId) {
          await updateProject(storedId, { project: updated, change_type: "regenerate" });
          setHistoryKey((k) => k + 1);
          toast.success(summary ?? "Edit applied and saved.");
        } else {
          toast.success(summary ?? "Edit applied.");
        }
      } catch (error) {
        const msg =
          error instanceof ApiError && error.status === 422
            ? "Edit rejected — a value was out of range."
            : MSG_OFFLINE;
        toast.error(msg, { duration: 5000 });
      } finally {
        setEditBusy(false);
      }
    },
    [project, storedId],
  );

  const handleRestoreVersion = useCallback((stored: StoredProject) => {
    if (stored.project) setProject(stored.project);
    setHistoryKey((k) => k + 1);
    toast.success("Restored to a previous version.");
  }, []);

  // Phase 29: generate MEP layers
  const handleGenerateMep = useCallback(
    async (systems?: MEPSystem[]) => {
      if (!storedId) {
        toast.error("Save the project first before generating MEP layers.");
        return;
      }
      setMepGenerating(true);
      try {
        const updated = await generateMep(storedId, systems);
        if (updated && typeof updated === "object" && "rooms" in updated) {
          setProject(updated as unknown as ArchitectureProject);
          await updateProject(storedId, {
            project: updated as unknown as ArchitectureProject,
            change_type: "regenerate",
          });
          setHistoryKey((k) => k + 1);
          toast.success("MEP layers generated. Advisory — review with a licensed engineer.");
        }
      } catch {
        toast.error("MEP generation failed — ensure a project is generated first.");
      } finally {
        setMepGenerating(false);
      }
    },
    [storedId],
  );

  const handleToggleMepLayer = useCallback((system: MEPSystem) => {
    setActiveMepLayers((prev) => {
      const next = new Set(prev);
      if (next.has(system)) next.delete(system);
      else next.add(system);
      return next;
    });
  }, []);

  // Phase 30: generate detail drawing
  const handleGenerateDetail = useCallback(
    async (detailType: DetailType, sourceId: string) => {
      if (!storedId) {
        toast.error("Save the project first before generating detail drawings.");
        return;
      }
      setDetailGenerating(true);
      try {
        const drawing = await generateDetail(storedId, detailType, sourceId);
        setProject((prev) => {
          if (!prev) return prev;
          const existing = prev.detail_drawings ?? [];
          const filtered = existing.filter((d) => d.id !== drawing.id);
          return { ...prev, detail_drawings: [...filtered, drawing] };
        });
        await updateProject(storedId, {
          change_type: "regenerate",
        });
        setHistoryKey((k) => k + 1);
        toast.success(`${drawing.name} generated. Advisory — verify on site.`);
      } catch {
        toast.error("Detail generation failed — ensure a project is generated first.");
      } finally {
        setDetailGenerating(false);
      }
    },
    [storedId],
  );

  const handleDeleteDetail = useCallback(
    async (detailId: string) => {
      if (!storedId) return;
      try {
        await deleteDetail(storedId, detailId);
        setProject((prev) => {
          if (!prev) return prev;
          return { ...prev, detail_drawings: (prev.detail_drawings ?? []).filter((d) => d.id !== detailId) };
        });
        toast.success("Detail drawing removed.");
      } catch {
        toast.error("Could not remove detail — engine offline.");
      }
    },
    [storedId],
  );

  // Phase 31: BOQ actions
  const handleCalculateBOQ = useCallback(async () => {
    if (!storedId) {
      toast.error("Save the project first before calculating BOQ.");
      return;
    }
    setBoqCalculating(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/projects/${storedId}/chat`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: "calculate BOQ" }),
        },
      );
      if (response.ok) {
        const data = (await response.json()) as { project?: ArchitectureProject };
        if (data.project) {
          setProject(data.project);
          await updateProject(storedId, { project: data.project, change_type: "regenerate" });
          setHistoryKey((k) => k + 1);
          toast.success("BOQ calculated. Review rates and adjust as needed.");
        }
      }
    } catch {
      toast.error("BOQ calculation failed — engine offline.");
    } finally {
      setBoqCalculating(false);
    }
  }, [storedId]);

  const handleEditRate = useCallback(
    async (category: string, item: string, rate: number) => {
      if (!storedId) return;
      try {
        const updated = await editRate(storedId, category, item, rate);
        if (updated) {
          setProject(updated);
          setHistoryKey((k) => k + 1);
          toast.success("Rate updated and BOQ recalculated.");
        }
      } catch {
        toast.error("Rate update failed — engine offline.");
      }
    },
    [storedId],
  );

  const handleEditTileSpec = useCallback(
    async (id: string, field: string, value: number) => {
      if (!storedId || !project) return;
      try {
        const response = await fetch(
          `${API_BASE_URL}/projects/${storedId}/chat`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              message: `update tile spec ${id} ${field} to ${value}`,
            }),
          },
        );
        if (response.ok) {
          const data = (await response.json()) as { project?: ArchitectureProject };
          if (data.project) {
            setProject(data.project);
            setHistoryKey((k) => k + 1);
          }
        }
      } catch {
        // silently ignore tile spec update in offline mode
      }
    },
    [storedId, project],
  );

  // Stage 24.6 — chat tool call mutated the project; sync workspace state
  const handleChatProjectUpdate = useCallback(
    (updated: ArchitectureProject) => {
      setProject(updated);
      setHistoryKey((k) => k + 1);
    },
    [],
  );

  const handleRename = useCallback(
    async (name: string) => {
      const next = name.trim();
      if (!next) return;
      setTitle(next);
      if (storedId) {
        try {
          await updateProject(storedId, { name: next });
        } catch {
          toast.error("Rename failed — engine offline.", { duration: 4000 });
        }
      }
    },
    [storedId],
  );

  function handleTemplateChange(id: string) {
    setTemplateId(id);
    const template = PROJECT_TEMPLATES.find((t) => t.id === id);
    if (template) setPrompt(template.prompt);
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
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-border/60 bg-card shadow-[0_1px_4px_rgba(0,0,0,0.04)]">
          <PreviewPanel
            project={project}
            projectId={storedId ?? undefined}
            title={title}
            onRename={(name) => void handleRename(name)}
            selectedRoomId={selectedRoomId}
            onSelectRoom={setSelectedRoomId}
            editBusy={editBusy}
            onApplyRoomEdit={(changes) => void handleApplyChanges(changes)}
            activeMepLayers={activeMepLayers}
            selectedMepPointId={selectedMepPointId}
            onSelectMepPoint={setSelectedMepPointId}
            onToggleMepLayer={handleToggleMepLayer}
          />
          <ChatPanel
            projectId={storedId}
            project={project}
            onProjectUpdate={handleChatProjectUpdate}
          />
        </div>
      </div>

      <DataPanel
        project={project}
        storedId={storedId}
        selectedRoomId={selectedRoomId}
        onSelectRoom={setSelectedRoomId}
        editBusy={editBusy}
        onApplyChanges={(changes) => void handleApplyChanges(changes)}
        historyKey={historyKey}
        activeMepLayers={activeMepLayers}
        onToggleMepLayer={handleToggleMepLayer}
        selectedMepPointId={selectedMepPointId}
        onSelectMepPoint={setSelectedMepPointId}
        onGenerateMep={(sys) => void handleGenerateMep(sys)}
        mepGenerating={mepGenerating}
        onGenerateDetail={(type, src) => void handleGenerateDetail(type, src)}
        onDeleteDetail={(id) => void handleDeleteDetail(id)}
        detailGenerating={detailGenerating}
        onRestoreVersion={handleRestoreVersion}
        onCalculateBOQ={handleCalculateBOQ}
        onEditRate={handleEditRate}
        onEditTileSpec={handleEditTileSpec}
        boqCalculating={boqCalculating}
      />
    </div>
  );
}
