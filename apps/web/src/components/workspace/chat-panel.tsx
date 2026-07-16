"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
  Layers,
  Loader2,
  Paperclip,
  RotateCcw,
  Send,
  Sparkles,
  X,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { PROJECT_TEMPLATES } from "@/features/templates/templates";
import type { ArchitectureProject } from "@/features/project/types";
import { cn } from "@/lib/utils";

export type GenerationMode = "deterministic" | "ai" | "hybrid";

interface ChatPanelProps {
  storedId: string | null;
  project: ArchitectureProject | null;
  generating: boolean;
  generationMode: GenerationMode;
  onModeChange: (mode: GenerationMode) => void;
  aiAvailable: boolean;
  templateId?: string;
  onTemplateChange: (id: string) => void;
  onSend: (
    text: string,
    files: File[],
  ) => Promise<{ reply: string; toolCalls?: string[] }>;
}

interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: string[];
  pending?: boolean;
  imageNames?: string[];
  /** Live blob: preview URLs for this session only — never persisted to storage. */
  previews?: string[];
}

// Tool badge label overrides — human-readable names for action chips
const TOOL_LABELS: Record<string, string> = {
  generate_design:         "✦ Generated",
  add_room:                "+ Room added",
  remove_room:             "− Room removed",
  set_parameter:           "✎ Edited",
  generate_mep:            "⚡ MEP generated",
  edit_mep_point:          "✎ MEP point moved",
  get_mep_plan:            "⚡ MEP plan",
  generate_detail:         "⊕ Detail drawn",
  list_details:            "Details listed",
  delete_detail:           "Detail removed",
  run_intelligence:        "⬡ Analysis",
  calculate_boq:           "₹ BOQ calculated",
  get_boq:                 "₹ BOQ summary",
  edit_rate:               "₹ Rate updated",
  edit_tile_spec:          "⬡ Tile spec updated",
  check_tn_rules:          "⚖ TN Advisory",
  get_user_profile:        "👤 Profile",
  update_user_profile:     "✎ Profile updated",
  get_client_brief:        "📋 Brief",
  update_client_brief:     "✎ Brief updated",
  create_client_change:    "↺ Change request",
  show_affected_items:     "⬡ Impact report",
  list_client_changes:     "↺ Changes",
  approve_change:          "✓ Approved",
  reject_change:           "✗ Rejected",
  revert_change:           "↺ Reverted",
  generate_render_prompt:  "🎨 Render prompt",
  export_drawing:          "⬇ Exported",
  export_project:          "⬇ Exported",
  restore_version:         "↩ Restored",
  get_program:             "◻ Program",
};

const MUTATING_TOOLS = new Set([
  "generate_design", "add_room", "remove_room", "set_parameter",
  "generate_mep", "edit_mep_point", "generate_detail", "delete_detail",
  "calculate_boq", "edit_rate", "edit_tile_spec", "update_client_brief",
  "create_client_change", "approve_change", "reject_change", "revert_change",
  "generate_render_prompt", "export_drawing", "export_project", "restore_version",
]);

const STARTERS_INITIAL = [
  "Generate a 2BHK house for a family of 4",
  "Design a compact 1BHK apartment, 25x40 ft site",
  "Build a 3-bedroom villa with a home office",
];

const STARTERS_WITH_PROJECT = [
  "Make the kitchen 10×12 ft",
  "Add MEP layers",
  "Generate toilet detail",
  "Check Tamil Nadu compliance",
  "Calculate BOQ and cost estimate",
  "Export as DXF",
];

const MAX_ATTACHMENTS = 4;
const MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024; // 8 MB

let _msgId = 0;
function nextId() {
  // Timestamp + counter, not just a counter — a plain per-session counter
  // restarts at 0 on every reload and collides with ids already sitting in
  // the persisted (cross-reload) history.
  return `m${Date.now().toString(36)}${(++_msgId).toString(36)}`;
}

interface Attachment {
  id: string;
  file: File;
  previewUrl: string;
}

function storageKey(storedId: string) {
  return `scotch:chat:${storedId}`;
}

function loadHistory(storedId: string | null): DisplayMessage[] {
  if (!storedId || typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(storageKey(storedId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as DisplayMessage[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(storedId: string | null, messages: DisplayMessage[]) {
  if (!storedId || typeof window === "undefined") return;
  try {
    // Persist without pending placeholders or live object-URL previews —
    // blob: URLs die with the tab, so only the filenames survive as a record.
    const persisted = messages
      .filter((m) => !m.pending)
      .map(({ id, role, content, toolCalls, imageNames }) => ({ id, role, content, toolCalls, imageNames }));
    window.localStorage.setItem(storageKey(storedId), JSON.stringify(persisted));
  } catch {
    // storage full or unavailable — conversation just won't survive reload
  }
}

export function ChatPanel({
  storedId,
  project,
  generating,
  generationMode,
  onModeChange,
  aiAvailable,
  templateId,
  onTemplateChange,
  onSend,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const loadedForRef = useRef<string | null>(null);
  const objectUrlsRef = useRef<string[]>([]);

  // Load persisted history whenever we get (or switch to) a real project id.
  // Skip if the conversation already has messages in memory — that means the
  // id just got created lazily mid-conversation (first send auto-creates the
  // project), and there's nothing on disk yet to clobber the live thread with.
  useEffect(() => {
    if (!storedId || loadedForRef.current === storedId) return;
    loadedForRef.current = storedId;
    setMessages((prev) => (prev.length > 0 ? prev : loadHistory(storedId)));
  }, [storedId]);

  // Persist on every change (once we have a project id)
  useEffect(() => {
    saveHistory(storedId, messages);
  }, [storedId, messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    return () => {
      objectUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    };
  }, []);

  const hasProject = !!project;
  const disabled = busy || generating;

  const selectedTemplate = useMemo(
    () => PROJECT_TEMPLATES.find((t) => t.id === templateId),
    [templateId],
  );

  function addFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList).filter((f) => f.type.startsWith("image/"));
    const room = MAX_ATTACHMENTS - attachments.length;
    if (room <= 0) {
      toast.error(`You can attach up to ${MAX_ATTACHMENTS} images per message.`);
      return;
    }
    const accepted: Attachment[] = [];
    for (const file of files.slice(0, room)) {
      if (file.size > MAX_ATTACHMENT_BYTES) {
        toast.error(`${file.name} is too large — max ${MAX_ATTACHMENT_BYTES / 1024 / 1024} MB.`);
        continue;
      }
      const previewUrl = URL.createObjectURL(file);
      objectUrlsRef.current.push(previewUrl);
      accepted.push({ id: nextId(), file, previewUrl });
    }
    if (accepted.length > 0) setAttachments((prev) => [...prev, ...accepted]);
  }

  function removeAttachment(id: string) {
    setAttachments((prev) => {
      const target = prev.find((a) => a.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((a) => a.id !== id);
    });
  }

  async function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if ((!msg && attachments.length === 0) || disabled) return;

    const outgoingFiles = attachments.map((a) => a.file);
    const imagePreviews = attachments.map((a) => a.previewUrl);
    const imageNames = attachments.map((a) => a.file.name);

    setInput("");
    setAttachments([]);

    const userMsg: DisplayMessage = {
      id: nextId(),
      role: "user",
      content: msg || "(image only)",
      imageNames: imageNames.length > 0 ? imageNames : undefined,
      previews: imagePreviews.length > 0 ? imagePreviews : undefined,
    };
    const pendingMsg: DisplayMessage = {
      id: nextId(),
      role: "assistant",
      content: "",
      pending: true,
    };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setBusy(true);

    try {
      const result = await onSend(msg, outgoingFiles);
      setMessages((prev) =>
        prev.map((m) =>
          m.pending
            ? { ...m, content: result.reply, toolCalls: result.toolCalls, pending: false }
            : m,
        ),
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.pending
            ? { ...m, content: "Something went wrong — is the backend running?", pending: false }
            : m,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }

  function handleClear() {
    setMessages([]);
    if (storedId) {
      try {
        window.localStorage.removeItem(storageKey(storedId));
      } catch {
        // ignore
      }
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      {/* Header */}
      <div className="flex h-11 shrink-0 items-center justify-between gap-2 border-b border-border px-3">
        <div className="flex items-center gap-1.5 text-[13px] font-medium tracking-tight">
          <Sparkles className="size-3.5 text-violet-500" />
          Design Assistant
          {(busy || generating) && <Loader2 className="size-3 animate-spin text-muted-foreground" />}
        </div>
        <div className="flex items-center gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <Layers className="size-3" />
                Template
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              <DropdownMenuLabel>Insert a starter prompt</DropdownMenuLabel>
              {PROJECT_TEMPLATES.map((t) => (
                <DropdownMenuItem
                  key={t.id}
                  onSelect={() => {
                    onTemplateChange(t.id);
                    setInput(t.prompt);
                    setTimeout(() => inputRef.current?.focus(), 50);
                  }}
                >
                  <span className="flex w-full flex-col">
                    <span className="flex items-center justify-between gap-2">
                      <span>{t.name}</span>
                      <span className="text-[10px] text-muted-foreground">{t.siteSize}</span>
                    </span>
                  </span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={handleClear}
                disabled={messages.length === 0}
                className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-30"
                aria-label="Clear conversation"
              >
                <RotateCcw className="size-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom">Clear conversation</TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Generation mode — only meaningfully affects the first design generation */}
      {!hasProject && (
        <div className="shrink-0 border-b border-border/70 px-3 py-2">
          <div className="flex items-center gap-1 rounded-lg bg-muted p-0.5">
            {(["deterministic", "ai", "hybrid"] as GenerationMode[]).map((m) => {
              const isAiMode = m !== "deterministic";
              const lockedOut = isAiMode && !aiAvailable;
              return (
                <button
                  key={m}
                  type="button"
                  disabled={lockedOut}
                  onClick={() => onModeChange(m)}
                  className={cn(
                    "flex flex-1 items-center justify-center gap-1 rounded-md px-2 py-1 text-[11px] font-medium capitalize transition-colors",
                    generationMode === m
                      ? "bg-card text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                      : lockedOut
                        ? "cursor-default text-muted-foreground/40"
                        : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {isAiMode && <Sparkles className="size-2.5" />}
                  {m}
                </button>
              );
            })}
          </div>
          <p className="mt-1.5 text-[10px] leading-4 text-muted-foreground/70">
            Applies to the first design generation only — edits after that happen through chat.
            {selectedTemplate && ` Template loaded: ${selectedTemplate.name}.`}
          </p>
        </div>
      )}

      {/* Thread */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {messages.length === 0 && (
          <div className="py-6 text-center">
            <Bot className="mx-auto mb-2 size-8 text-muted-foreground/30" />
            <p className="text-[11px] text-muted-foreground/60">
              {hasProject
                ? "Ask me to refine rooms, generate MEP, run compliance, or create a render prompt."
                : "Describe your building, or attach a reference photo or sketch, to generate a floor plan."}
            </p>
            <div className="mt-3 flex flex-wrap justify-center gap-1.5">
              {(hasProject ? STARTERS_WITH_PROJECT : STARTERS_INITIAL).map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => void handleSend(s)}
                  className="rounded-full border border-border/70 bg-muted/40 px-2.5 py-1 text-[10px] text-muted-foreground transition-colors hover:border-foreground/30 hover:text-foreground"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => {
          const previews = m.previews;
          return (
            <div
              key={m.id}
              className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}
            >
              <div
                className={cn(
                  "max-w-[88%] rounded-xl px-3 py-2 text-[11px] leading-relaxed",
                  m.role === "user" ? "bg-foreground text-background" : "bg-muted/60 text-foreground",
                  m.pending && "animate-pulse",
                )}
              >
                {(previews && previews.length > 0) || (m.imageNames && m.imageNames.length > 0) ? (
                  <div className="mb-1.5 flex flex-wrap gap-1.5">
                    {previews
                      ? previews.map((src, i) => (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            key={i}
                            src={src}
                            alt="attachment"
                            className="size-14 rounded-md border border-background/30 object-cover"
                          />
                        ))
                      : m.imageNames?.map((name, i) => (
                          <span
                            key={i}
                            className="rounded border border-background/30 bg-background/10 px-1.5 py-0.5 text-[9px]"
                          >
                            📎 {name}
                          </span>
                        ))}
                  </div>
                ) : null}

                {m.pending ? (
                  <span className="text-muted-foreground">Thinking…</span>
                ) : (
                  <>
                    <span className="whitespace-pre-wrap">{m.content}</span>
                    {m.toolCalls && m.toolCalls.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {[...new Set(m.toolCalls)].map((tc) => {
                          const label = TOOL_LABELS[tc] ?? tc.replace(/_/g, " ");
                          const isMutating = MUTATING_TOOLS.has(tc);
                          return (
                            <span
                              key={tc}
                              title={tc}
                              className={cn(
                                "rounded px-1.5 py-0.5 text-[9px] font-medium",
                                isMutating
                                  ? "bg-violet-500/15 text-violet-700"
                                  : "bg-muted/60 text-muted-foreground",
                              )}
                            >
                              {label}
                            </span>
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-border px-3 py-2.5">
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {attachments.map((a) => (
              <div key={a.id} className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={a.previewUrl}
                  alt={a.file.name}
                  className="size-12 rounded-md border border-border object-cover"
                />
                <button
                  type="button"
                  onClick={() => removeAttachment(a.id)}
                  className="absolute -right-1.5 -top-1.5 flex size-4 items-center justify-center rounded-full bg-foreground text-background"
                  aria-label={`Remove ${a.file.name}`}
                >
                  <X className="size-2.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => {
              addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled || attachments.length >= MAX_ATTACHMENTS}
                className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
                aria-label="Attach image"
              >
                <Paperclip className="size-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent side="top">Attach a reference image or sketch</TooltipContent>
          </Tooltip>

          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={
              hasProject
                ? "Add a bedroom, check TN rules, generate render prompt…"
                : "Describe your building — 2BHK house on 30×50 ft east-facing site…"
            }
            disabled={disabled}
            rows={1}
            className="flex-1 resize-none rounded-lg border border-border bg-muted/30 px-3 py-2 text-[11px] placeholder:text-muted-foreground/50 focus:border-foreground/30 focus:outline-none disabled:opacity-40"
            style={{ maxHeight: 96, overflowY: "auto" }}
          />
          <Button
            size="icon-sm"
            disabled={(!input.trim() && attachments.length === 0) || disabled}
            onClick={() => void handleSend()}
            aria-label="Send"
          >
            {disabled ? <Loader2 className="size-3.5 animate-spin" /> : <Send className="size-3.5" />}
          </Button>
        </div>
        <p className="mt-1 text-[9px] text-muted-foreground/40">
          Enter to send · Shift+Enter for new line · attach up to {MAX_ATTACHMENTS} images
        </p>
      </div>
    </div>
  );
}
