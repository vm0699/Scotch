"use client";

import { useState } from "react";
import { MessageSquarePlus, Send, X } from "lucide-react";
import { Button } from "@/components/ui/button";

type FeedbackType = "bug" | "feature" | "general";

interface LocalFeedback {
  type: FeedbackType;
  message: string;
  timestamp: string;
  url: string;
}

function saveFeedbackLocally(fb: LocalFeedback) {
  if (typeof window === "undefined") return;
  const key = "scotch_feedback";
  const existing: LocalFeedback[] = JSON.parse(localStorage.getItem(key) ?? "[]");
  existing.push(fb);
  localStorage.setItem(key, JSON.stringify(existing.slice(-50)));
}

export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [type, setType] = useState<FeedbackType>("general");
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState(false);

  function submit() {
    if (!message.trim()) return;
    saveFeedbackLocally({
      type,
      message: message.trim(),
      timestamp: new Date().toISOString(),
      url: window.location.href,
    });
    setSent(true);
    setTimeout(() => {
      setOpen(false);
      setSent(false);
      setMessage("");
      setType("general");
    }, 1800);
  }

  const TYPE_LABELS: Record<FeedbackType, string> = {
    bug: "Bug report",
    feature: "Feature request",
    general: "General feedback",
  };

  return (
    <>
      <button
        title="Send feedback"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
      >
        <MessageSquarePlus className="h-3.5 w-3.5" />
        Feedback
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-end p-4 pointer-events-none">
          <div
            className="pointer-events-auto w-80 rounded-xl border border-border bg-card shadow-[0_8px_32px_rgba(0,0,0,0.12)] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-border px-4 py-3">
              <span className="text-sm font-medium">Send feedback</span>
              <Button variant="ghost" size="icon-xs" onClick={() => setOpen(false)}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>

            {sent ? (
              <div className="flex flex-col items-center gap-2 p-6 text-center">
                <span className="text-2xl">✓</span>
                <p className="text-sm font-medium">Thanks! Feedback saved.</p>
                <p className="text-[11px] text-muted-foreground">
                  Stored locally — the team reviews pilot feedback periodically.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-3 p-4">
                {/* Type picker */}
                <div className="flex gap-1">
                  {(["bug", "feature", "general"] as FeedbackType[]).map((t) => (
                    <button
                      key={t}
                      onClick={() => setType(t)}
                      className={`flex-1 rounded-md border px-2 py-1 text-[10px] font-medium transition-colors ${
                        type === t
                          ? "border-foreground bg-foreground/5 text-foreground"
                          : "border-border text-muted-foreground hover:border-foreground/30"
                      }`}
                    >
                      {TYPE_LABELS[t]}
                    </button>
                  ))}
                </div>

                {/* Message */}
                <textarea
                  autoFocus
                  placeholder={
                    type === "bug" ? "What happened? What did you expect?" :
                    type === "feature" ? "What would you like Scotch to do?" :
                    "What's on your mind?"
                  }
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={4}
                  className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-[11px] outline-none ring-ring placeholder:text-muted-foreground/50 focus:ring-1"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
                  }}
                />

                <div className="flex items-center justify-between">
                  <span className="text-[9px] text-muted-foreground/50">
                    Saved locally · ⌘↵ to submit
                  </span>
                  <Button
                    size="sm"
                    className="gap-1.5 text-xs"
                    onClick={submit}
                    disabled={!message.trim()}
                  >
                    <Send className="h-3 w-3" />
                    Submit
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
