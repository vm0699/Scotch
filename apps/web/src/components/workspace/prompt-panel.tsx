"use client";

import { useState } from "react";
import { Info, Lock, Sparkles } from "lucide-react";

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

const PROMPT_PLACEHOLDER =
  "Describe your building — e.g. “Design a 2BHK apartment on a 30x50 ft east-facing site with living room, kitchen, 2 bedrooms, 2 bathrooms, balcony, and parking.”";

export function PromptPanel({
  prompt,
  onPromptChange,
  templateId,
  onTemplateChange,
  onGenerate,
}: {
  prompt: string;
  onPromptChange: (value: string) => void;
  templateId?: string;
  onTemplateChange: (id: string) => void;
  onGenerate: () => void;
}) {
  const [notice, setNotice] = useState(false);

  function handleGenerate() {
    setNotice(true);
    onGenerate();
  }

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
            <button
              type="button"
              className="flex-1 rounded-md bg-card px-2 py-1.5 text-xs font-medium shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
            >
              Deterministic
            </button>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="flex flex-1 cursor-default items-center justify-center gap-1.5 rounded-md px-2 py-1.5 text-xs text-muted-foreground/60"
                >
                  <Lock className="size-3" />
                  AI
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom">
                AI providers arrive in Phase 9
              </TooltipContent>
            </Tooltip>
          </div>
          <p className="mt-2 text-[11px] leading-4 text-muted-foreground/70">
            Rule-based layout engine. Runs locally, no API key required.
          </p>
        </PanelSection>

        <PanelSection>
          <Button onClick={handleGenerate} className="w-full justify-between" size="lg">
            <span className="flex items-center gap-2">
              <Sparkles className="size-4" />
              Generate Design
            </span>
            <kbd className="rounded border border-primary-foreground/25 px-1.5 py-0.5 font-sans text-[10px] text-primary-foreground/70">
              Ctrl ↵
            </kbd>
          </Button>
          <div
            className={cn(
              "mt-2.5 flex items-start gap-2 overflow-hidden rounded-md border border-border bg-muted/50 px-2.5 text-[11px] leading-4 text-muted-foreground transition-all",
              notice ? "max-h-16 py-2 opacity-100" : "max-h-0 border-transparent py-0 opacity-0",
            )}
          >
            <Info className="mt-px size-3 shrink-0" />
            The generation engine arrives in Phase 5 — the interface is wired
            and waiting.
          </div>
        </PanelSection>
      </PanelBody>
    </Panel>
  );
}
