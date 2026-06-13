"use client";

import { Info, Loader2, Sparkles } from "lucide-react";

import {
  Panel,
  PanelBody,
  PanelHeader,
  PanelSection,
} from "@/components/layout/panel";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";
import { cn } from "@/lib/utils";

type GenerationMode = "deterministic" | "ai" | "hybrid";

const PROMPT_PLACEHOLDER =
  "Describe your building — e.g. Design a 2BHK apartment on a 30x50 ft east-facing site with living room, kitchen, 2 bedrooms, 2 bathrooms, balcony, and parking.";

function ModeTab({
  active,
  onClick,
  disabled,
  children,
}: {
  active: boolean;
  onClick?: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      className={cn(
        "flex flex-1 items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
        active
          ? "bg-card text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
          : disabled
            ? "cursor-default text-muted-foreground/40"
            : "text-muted-foreground hover:text-foreground",
      )}
    >
      {children}
    </button>
  );
}

export function PromptPanel({
  prompt,
  onPromptChange,
  templateId,
  onTemplateChange,
  onGenerate,
  onGenerateOptions,
  generating = false,
  notice,
  mode = "deterministic",
  onModeChange,
  aiAvailable = false,
}: {
  prompt: string;
  onPromptChange: (value: string) => void;
  templateId?: string;
  onTemplateChange: (id: string) => void;
  onGenerate: () => void;
  onGenerateOptions?: () => void;
  generating?: boolean;
  notice?: string;
  mode?: GenerationMode;
  onModeChange?: (mode: GenerationMode) => void;
  aiAvailable?: boolean;
}) {
  function handleGenerate() {
    if (!generating) {
      onGenerate();
    }
  }

  const modeDescription =
    mode === "ai"
      ? "Claude analyses the brief and generates a layout. Requires an API key."
      : mode === "hybrid"
        ? "AI generation with automatic deterministic fallback on failure."
        : "Rule-based layout engine. Runs locally, no API key required.";

  return (
    <Panel>
      <PanelHeader title="Design Brief" />
      <PanelBody className="flex flex-col">
        <PanelSection title="Prompt" className="flex-1">
          <Textarea
            value={prompt}
            onChange={(e) => onPromptChange(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                handleGenerate();
              }
            }}
            placeholder={PROMPT_PLACEHOLDER}
            className="min-h-44 resize-none border-border bg-background text-[13px] leading-6 shadow-none"
          />
          <div className="mt-1.5 flex justify-end text-[11px] text-muted-foreground/70">
            {prompt.length > 0 ? `${prompt.length} characters` : "Plain language works best"}
          </div>
        </PanelSection>

        <PanelSection title="Template">
          <Select value={templateId} onValueChange={onTemplateChange}>
            <SelectTrigger className="w-full" size="sm">
              <SelectValue placeholder="Start from a template…" />
            </SelectTrigger>
            <SelectContent>
              {PROJECT_TEMPLATES.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  <span className="flex w-full items-center justify-between gap-3">
                    {t.name}
                    <span className="text-xs text-muted-foreground">
                      {t.siteSize}
                    </span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </PanelSection>

        <PanelSection title="Generation Mode">
          <div className="flex rounded-lg bg-muted p-0.5">
            <ModeTab
              active={mode === "deterministic"}
              onClick={() => onModeChange?.("deterministic")}
            >
              Deterministic
            </ModeTab>

            {aiAvailable ? (
              <>
                <ModeTab
                  active={mode === "ai"}
                  onClick={() => onModeChange?.("ai")}
                >
                  <Sparkles className="size-3" />
                  AI
                </ModeTab>
                <ModeTab
                  active={mode === "hybrid"}
                  onClick={() => onModeChange?.("hybrid")}
                >
                  Hybrid
                </ModeTab>
              </>
            ) : (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="flex flex-1 cursor-default items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted-foreground/40">
                    <Sparkles className="size-3" />
                    AI
                  </span>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="max-w-52 text-center">
                  Add an API key in Settings to unlock AI generation mode.
                </TooltipContent>
              </Tooltip>
            )}
          </div>
          <p className="mt-2 text-[11px] leading-4 text-muted-foreground/70">
            {modeDescription}
          </p>
        </PanelSection>

        <PanelSection>
          <Button
            onClick={handleGenerate}
            disabled={generating}
            className="w-full justify-between"
            size="lg"
          >
            <span className="flex items-center gap-2">
              {generating ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Sparkles className="size-4" />
              )}
              {generating ? "Generating…" : "Generate Design"}
            </span>
            <kbd className="rounded border border-primary-foreground/25 px-1.5 py-0.5 font-sans text-[10px] text-primary-foreground/70">
              Ctrl ↵
            </kbd>
          </Button>

          {onGenerateOptions && (
            <button
              type="button"
              onClick={generating ? undefined : onGenerateOptions}
              disabled={generating}
              className="mt-2 w-full text-center text-[11px] text-muted-foreground/70 transition-colors hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
            >
              or compare compact · balanced · spacious options
            </button>
          )}

          <div
            className={cn(
              "mt-2.5 flex items-start gap-2 overflow-hidden rounded-md border border-border bg-muted/50 px-2.5 text-[11px] leading-4 text-muted-foreground transition-all",
              notice ? "max-h-20 py-2 opacity-100" : "max-h-0 border-transparent py-0 opacity-0",
            )}
          >
            <Info className="mt-px size-3 shrink-0" />
            {notice}
          </div>
        </PanelSection>
      </PanelBody>
    </Panel>
  );
}
