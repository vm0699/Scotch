"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, ChevronDown, ChevronUp, Loader2, Send, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { sendChatMessage, type ChatMessage } from "@/features/api/client";
import type { ArchitectureProject } from "@/features/project/types";
import { cn } from "@/lib/utils";

interface ChatPanelProps {
  projectId: string | null;
  project: ArchitectureProject | null;
  onProjectUpdate: (project: ArchitectureProject) => void;
}

interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: string[];
  pending?: boolean;
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

const STARTERS_INITIAL = [
  "Generate a 2BHK house for a family of 4",
  "Add a powder room near the entry",
  "Check Tamil Nadu compliance",
  "Calculate BOQ and cost estimate",
];

const STARTERS_WITH_PROJECT = [
  "Make the kitchen 10×12 ft",
  "Add MEP layers",
  "Generate toilet detail",
  "Generate render prompt",
  "Client asked to add attached toilet",
  "Export as DXF",
];

let _msgId = 0;
function nextId() {
  return `m${++_msgId}`;
}

export function ChatPanel({ projectId, project, onProjectUpdate }: ChatPanelProps) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const historyRef = useRef<ChatMessage[]>([]);

  // Scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-focus input when panel opens
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 120);
  }, [open]);

  async function handleSend(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    if (!projectId) return;

    setInput("");

    const userMsg: DisplayMessage = { id: nextId(), role: "user", content: msg };
    const pendingMsg: DisplayMessage = {
      id: nextId(),
      role: "assistant",
      content: "",
      pending: true,
    };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setBusy(true);

    try {
      const resp = await sendChatMessage(projectId, msg, historyRef.current);
      historyRef.current = [
        ...historyRef.current,
        { role: "user" as const, content: msg },
        { role: "assistant" as const, content: resp.reply },
      ].slice(-20); // keep last 20 turns

      setMessages((prev) =>
        prev.map((m) =>
          m.pending
            ? { ...m, content: resp.reply, toolCalls: resp.tool_calls, pending: false }
            : m,
        ),
      );

      if (resp.project) {
        onProjectUpdate(resp.project as ArchitectureProject);
      }
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) =>
          m.pending
            ? {
                ...m,
                content: "Something went wrong — is the backend running?",
                pending: false,
              }
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

  const hasProject = !!project;

  return (
    <div className="flex flex-col border-t border-border/60 bg-card">
      {/* ── Toggle bar ──────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex h-9 shrink-0 items-center gap-2 px-4 text-left text-[11px] font-medium text-muted-foreground transition-colors hover:bg-muted/40 hover:text-foreground"
      >
        <Sparkles className="size-3.5 text-violet-500" />
        <span className="flex-1">AI Design Assistant</span>
        {busy && <Loader2 className="size-3 animate-spin" />}
        {open ? (
          <ChevronDown className="size-3.5" />
        ) : (
          <ChevronUp className="size-3.5" />
        )}
      </button>

      {/* ── Panel body ──────────────────────────────────────────────── */}
      {open && (
        <div className="flex flex-col" style={{ height: 340 }}>
          {/* Message thread */}
          <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
            {messages.length === 0 && (
              <div className="py-4 text-center">
                <Bot className="mx-auto mb-2 size-8 text-muted-foreground/30" />
                <p className="text-[11px] text-muted-foreground/60">
                  {hasProject
                    ? "Ask me to refine rooms, generate MEP, run compliance, or create a render prompt."
                    : "Describe your building to generate a floor plan."}
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

            {messages.map((m) => (
              <div
                key={m.id}
                className={cn(
                  "flex",
                  m.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                <div
                  className={cn(
                    "max-w-[85%] rounded-xl px-3 py-2 text-[11px] leading-relaxed",
                    m.role === "user"
                      ? "bg-foreground text-background"
                      : "bg-muted/60 text-foreground",
                    m.pending && "animate-pulse",
                  )}
                >
                  {m.pending ? (
                    <span className="text-muted-foreground">Thinking…</span>
                  ) : (
                    <>
                      <span className="whitespace-pre-wrap">{m.content}</span>
                      {m.toolCalls && m.toolCalls.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {[...new Set(m.toolCalls)].map((tc) => {
                            const label = TOOL_LABELS[tc] ?? tc.replace(/_/g, " ");
                            const isMutating = [
                              "generate_design","add_room","remove_room","set_parameter",
                              "generate_mep","edit_mep_point","generate_detail","delete_detail",
                              "calculate_boq","edit_rate","edit_tile_spec","update_client_brief",
                              "create_client_change","approve_change","reject_change","revert_change",
                              "generate_render_prompt","export_drawing","export_project","restore_version",
                            ].includes(tc);
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
            ))}
            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <div className="shrink-0 border-t border-border/60 px-3 py-2">
            <div className="flex items-end gap-2">
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
                disabled={busy || !hasProject}
                rows={1}
                className="flex-1 resize-none rounded-lg border border-border bg-muted/30 px-3 py-2 text-[11px] placeholder:text-muted-foreground/50 focus:border-foreground/30 focus:outline-none disabled:opacity-40"
                style={{ maxHeight: 80, overflowY: "auto" }}
              />
              <Button
                size="icon-sm"
                disabled={!input.trim() || busy || !hasProject}
                onClick={() => void handleSend()}
                aria-label="Send"
              >
                <Send className="size-3.5" />
              </Button>
            </div>
            <p className="mt-1 text-[9px] text-muted-foreground/40">
              Enter to send · Shift+Enter for new line
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
