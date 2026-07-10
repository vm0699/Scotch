"use client";

import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle,
  Circle,
  ClipboardCheck,
  Download,
  Loader2,
  PlusCircle,
  RefreshCw,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  createReviewIssue,
  deleteReviewIssue,
  exportReviewReport,
  runQAChecklist,
  listReviewIssues,
  updateReviewIssue,
  type QAChecklist,
  type ReviewIssue,
} from "@/features/api/client";

// ── QA status icon ────────────────────────────────────────────────────────────

function QAIcon({ status }: { status: string }) {
  if (status === "pass") return <CheckCircle className="h-3.5 w-3.5 text-emerald-600" />;
  if (status === "fail") return <XCircle className="h-3.5 w-3.5 text-destructive" />;
  if (status === "warning") return <TriangleAlert className="h-3.5 w-3.5 text-amber-500" />;
  return <Circle className="h-3.5 w-3.5 text-muted-foreground/40" />;
}

// ── QA Checklist sub-panel ────────────────────────────────────────────────────

function QAPanel({ projectId }: { projectId: string }) {
  const [qa, setQA] = useState<QAChecklist | null>(null);
  const [loading, setLoading] = useState(false);

  const run = useCallback(async () => {
    setLoading(true);
    try {
      const result = await runQAChecklist(projectId);
      setQA(result);
    } catch {
      // fail silently; user can retry
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { run(); }, [run]);

  if (!qa && !loading) {
    return (
      <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs" onClick={run}>
        <ClipboardCheck className="h-3 w-3" /> Run QA checklist
      </Button>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" /> Running checks…
      </div>
    );
  }

  if (!qa) return null;

  const scoreColor =
    qa.completion_pct >= 80 ? "text-emerald-700" :
    qa.completion_pct >= 50 ? "text-amber-600" : "text-destructive";

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className={`text-[13px] font-semibold tabular-nums ${scoreColor}`}>
          {qa.completion_pct.toFixed(0)}%
        </span>
        <span className="text-[10px] text-muted-foreground">
          {qa.passed} pass · {qa.warnings} warn · {qa.failed} fail
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-all ${
            qa.completion_pct >= 80 ? "bg-emerald-500" :
            qa.completion_pct >= 50 ? "bg-amber-400" : "bg-destructive"
          }`}
          style={{ width: `${qa.completion_pct}%` }}
        />
      </div>
      <div className="flex flex-col gap-1">
        {qa.items.map((item) => (
          <div key={item.id} className="flex items-start gap-2 rounded-md px-1.5 py-1 hover:bg-muted/40">
            <QAIcon status={item.status} />
            <div className="flex flex-col">
              <span className="text-[11px] font-medium leading-tight">{item.title}</span>
              {item.detail && (
                <span className="text-[10px] leading-tight text-muted-foreground">{item.detail}</span>
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5">
        <Button variant="outline" size="sm" className="flex-1 gap-1 text-xs" onClick={run} disabled={loading}>
          <RefreshCw className="h-3 w-3" /> Refresh
        </Button>
        <Button
          variant="outline"
          size="sm"
          className="gap-1 text-xs"
          onClick={() =>
            exportReviewReport(projectId, "text").then((blob) => {
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url; a.download = `review_${projectId}.txt`;
              a.click(); URL.revokeObjectURL(url);
            }).catch(() => {})
          }
        >
          <Download className="h-3 w-3" />
        </Button>
      </div>
      <p className="text-[9px] text-muted-foreground/50">{qa.advisory}</p>
    </div>
  );
}

// ── Issue list sub-panel ──────────────────────────────────────────────────────

function IssueRow({
  issue,
  onResolve,
  onDelete,
}: {
  issue: ReviewIssue;
  onResolve: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="flex items-start gap-2 rounded-md border border-border bg-card px-2.5 py-1.5 text-[11px]">
      <button
        title={issue.status === "resolved" ? "Resolved" : "Mark resolved"}
        onClick={() => issue.status !== "resolved" && onResolve(issue.id)}
        className="mt-0.5 shrink-0"
      >
        {issue.status === "resolved"
          ? <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
          : <Circle className="h-3.5 w-3.5 text-muted-foreground/40 hover:text-emerald-400 transition-colors" />
        }
      </button>
      <div className="flex min-w-0 flex-1 flex-col">
        <span className={`font-medium leading-tight ${issue.status === "resolved" ? "line-through text-muted-foreground" : ""}`}>
          {issue.title}
        </span>
        <span className="text-[10px] text-muted-foreground capitalize">{issue.category}</span>
      </div>
      <button
        onClick={() => onDelete(issue.id)}
        className="ml-1 shrink-0 text-muted-foreground/40 hover:text-destructive transition-colors"
        title="Remove issue"
      >
        <XCircle className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

// ── Main ReviewSection ────────────────────────────────────────────────────────

export function ReviewSection({ projectId }: { projectId: string | null }) {
  const [tab, setTab] = useState<"qa" | "issues">("qa");
  const [issues, setIssues] = useState<ReviewIssue[]>([]);
  const [newTitle, setNewTitle] = useState("");
  const [adding, setAdding] = useState(false);
  const [showAdd, setShowAdd] = useState(false);

  const loadIssues = useCallback(async () => {
    if (!projectId) return;
    try {
      const data = await listReviewIssues(projectId);
      setIssues(Array.isArray(data) ? data : []);
    } catch {
      // fail silently
    }
  }, [projectId]);

  useEffect(() => {
    if (tab === "issues") loadIssues();
  }, [tab, loadIssues]);

  if (!projectId) {
    return (
      <p className="text-[11px] text-muted-foreground/70">
        Generate a design to run QA checks.
      </p>
    );
  }

  async function handleAdd() {
    if (!newTitle.trim() || !projectId) return;
    setAdding(true);
    try {
      await createReviewIssue(projectId, { title: newTitle.trim() });
      setNewTitle("");
      setShowAdd(false);
      await loadIssues();
    } catch {
      // fail silently
    } finally {
      setAdding(false);
    }
  }

  async function handleResolve(id: string) {
    if (!projectId) return;
    await updateReviewIssue(projectId, id, { status: "resolved" }).catch(() => {});
    await loadIssues();
  }

  async function handleDelete(id: string) {
    if (!projectId) return;
    await deleteReviewIssue(projectId, id).catch(() => {});
    await loadIssues();
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex rounded-md bg-muted p-0.5 text-xs">
        {(["qa", "issues"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded py-0.5 text-center font-medium transition-colors ${
              tab === t
                ? "bg-card text-foreground shadow-[0_1px_2px_rgba(0,0,0,0.06)]"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t === "qa" ? "QA Checklist" : `Issues${issues.length > 0 ? ` (${issues.length})` : ""}`}
          </button>
        ))}
      </div>

      {tab === "qa" && <QAPanel projectId={projectId} />}

      {tab === "issues" && (
        <div className="flex flex-col gap-2">
          {issues.length > 0 ? (
            <div className="flex flex-col gap-1">
              {issues.map((issue) => (
                <IssueRow
                  key={issue.id}
                  issue={issue}
                  onResolve={handleResolve}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-muted-foreground/70">
              No issues yet. Add one to track a review comment.
            </p>
          )}

          {showAdd ? (
            <div className="flex gap-1.5">
              <input
                autoFocus
                type="text"
                placeholder="Issue title…"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAdd();
                  if (e.key === "Escape") { setShowAdd(false); setNewTitle(""); }
                }}
                className="flex-1 rounded-md border border-border bg-background px-2 py-1 text-[11px] outline-none ring-ring focus:ring-1"
              />
              <Button size="sm" className="h-6 px-2 text-xs" onClick={handleAdd} disabled={adding || !newTitle.trim()}>
                Add
              </Button>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="w-full gap-1.5 text-xs"
              onClick={() => setShowAdd(true)}
            >
              <PlusCircle className="h-3 w-3" />
              Add review issue
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
