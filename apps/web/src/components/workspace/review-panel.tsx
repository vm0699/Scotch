"use client";

import { useState, useEffect, useCallback } from "react";
import type { ReviewIssue, QAChecklist } from "@/features/project/types";
import {
  listReviewIssues,
  createReviewIssue,
  updateReviewIssue,
  deleteReviewIssue,
  runQAChecklist,
  exportReviewReport,
} from "@/features/api/client";

interface Props {
  projectId: string;
}

const STATUS_COLORS: Record<string, string> = {
  open: "bg-red-100 text-red-700",
  in_progress: "bg-amber-100 text-amber-700",
  resolved: "bg-green-100 text-green-700",
};

const PRIORITY_COLORS: Record<string, string> = {
  low: "text-stone-400",
  medium: "text-amber-600",
  high: "text-red-600",
};

const QA_ICONS: Record<string, string> = {
  pass: "✓",
  fail: "✗",
  warning: "⚠",
  not_checked: "–",
};

const QA_COLORS: Record<string, string> = {
  pass: "text-green-600",
  fail: "text-red-600",
  warning: "text-amber-600",
  not_checked: "text-stone-400",
};

function IssueRow({
  issue,
  onStatusChange,
  onDelete,
}: {
  issue: ReviewIssue;
  onStatusChange: (id: string, status: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="border border-stone-200 rounded p-2 space-y-1 text-xs">
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium text-stone-800 leading-snug">{issue.title}</span>
        <button
          onClick={() => onDelete(issue.id)}
          className="shrink-0 text-stone-300 hover:text-red-500 transition-colors"
          title="Delete issue"
        >
          ×
        </button>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[issue.status] ?? ""}`}>
          {issue.status.replace("_", " ")}
        </span>
        <span className={`font-medium ${PRIORITY_COLORS[issue.priority] ?? ""}`}>
          {issue.priority}
        </span>
        <span className="text-stone-400">{issue.category}</span>
      </div>
      {issue.description && (
        <p className="text-stone-400 leading-relaxed">{issue.description}</p>
      )}
      {issue.status !== "resolved" && (
        <div className="flex gap-1 pt-0.5">
          {issue.status === "open" && (
            <button
              onClick={() => onStatusChange(issue.id, "in_progress")}
              className="text-xs px-2 py-0.5 border border-stone-200 rounded hover:bg-stone-50 text-stone-600 transition-colors"
            >
              Start
            </button>
          )}
          <button
            onClick={() => onStatusChange(issue.id, "resolved")}
            className="text-xs px-2 py-0.5 border border-green-200 rounded hover:bg-green-50 text-green-700 transition-colors"
          >
            Resolve
          </button>
        </div>
      )}
    </div>
  );
}

export function ReviewPanel({ projectId }: Props) {
  const [tab, setTab] = useState<"issues" | "qa">("issues");
  const [issues, setIssues] = useState<ReviewIssue[]>([]);
  const [qa, setQA] = useState<QAChecklist | null>(null);
  const [loading, setLoading] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [newPriority, setNewPriority] = useState("medium");
  const [addOpen, setAddOpen] = useState(false);

  const loadIssues = useCallback(async () => {
    try {
      const data = await listReviewIssues(projectId);
      // backend returns array directly
      setIssues(Array.isArray(data) ? data : (data as { issues?: ReviewIssue[] }).issues ?? []);
    } catch {
      // ignore errors
    }
  }, [projectId]);

  useEffect(() => {
    loadIssues();
  }, [loadIssues]);

  async function loadQA() {
    setLoading(true);
    try {
      const data = await runQAChecklist(projectId);
      setQA(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }

  async function handleAdd() {
    if (!newTitle.trim()) return;
    try {
      await createReviewIssue(projectId, {
        title: newTitle.trim(),
        category: newCategory as ReviewIssue["category"],
        priority: newPriority as ReviewIssue["priority"],
      });
      setNewTitle("");
      setAddOpen(false);
      loadIssues();
    } catch {
      // ignore
    }
  }

  async function handleStatusChange(id: string, status: string) {
    try {
      await updateReviewIssue(projectId, id, {
        status: status as ReviewIssue["status"],
      });
      loadIssues();
    } catch {
      // ignore
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteReviewIssue(projectId, id);
      loadIssues();
    } catch {
      // ignore
    }
  }

  async function handleExport(fmt: "json" | "text") {
    try {
      const blob = await exportReviewReport(projectId, fmt);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `review-${projectId}.${fmt === "json" ? "json" : "txt"}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
  }

  const openCount = issues.filter((i) => i.status === "open").length;
  const inProgressCount = issues.filter((i) => i.status === "in_progress").length;

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-widest">
          Review &amp; QA
        </h3>
        <p className="text-xs text-stone-400">
          Track issues · QA checklist · export report
        </p>
      </div>

      <div className="flex border-b border-stone-200 text-xs">
        <button
          onClick={() => setTab("issues")}
          className={`px-3 py-1.5 border-b-2 transition-colors ${
            tab === "issues"
              ? "border-stone-800 text-stone-800 font-medium"
              : "border-transparent text-stone-400 hover:text-stone-600"
          }`}
        >
          Issues
          {openCount > 0 && (
            <span className="ml-1 px-1 py-0.5 text-xs bg-red-100 text-red-700 rounded-full">
              {openCount}
            </span>
          )}
        </button>
        <button
          onClick={() => { setTab("qa"); if (!qa) loadQA(); }}
          className={`px-3 py-1.5 border-b-2 transition-colors ${
            tab === "qa"
              ? "border-stone-800 text-stone-800 font-medium"
              : "border-transparent text-stone-400 hover:text-stone-600"
          }`}
        >
          QA Checklist
        </button>
      </div>

      {tab === "issues" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs text-stone-400 space-x-2">
              <span>{openCount} open</span>
              {inProgressCount > 0 && <span>{inProgressCount} in progress</span>}
            </div>
            <div className="flex gap-1">
              <button
                onClick={() => setAddOpen(!addOpen)}
                className="text-xs px-2 py-1 bg-stone-800 text-white rounded hover:bg-stone-700 transition-colors"
              >
                + Add
              </button>
              <button
                onClick={() => handleExport("json")}
                className="text-xs px-2 py-1 border border-stone-200 rounded hover:bg-stone-50 text-stone-600 transition-colors"
              >
                JSON
              </button>
              <button
                onClick={() => handleExport("text")}
                className="text-xs px-2 py-1 border border-stone-200 rounded hover:bg-stone-50 text-stone-600 transition-colors"
              >
                TXT
              </button>
            </div>
          </div>

          {addOpen && (
            <div className="border border-stone-200 rounded p-2 space-y-2 bg-stone-50">
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                placeholder="Issue title…"
                className="w-full text-xs border border-stone-200 rounded px-2 py-1.5 bg-white text-stone-800 placeholder-stone-300 focus:outline-none focus:border-stone-400"
                onKeyDown={(e) => e.key === "Enter" && handleAdd()}
              />
              <div className="flex gap-2">
                <select
                  value={newCategory}
                  onChange={(e) => setNewCategory(e.target.value)}
                  className="flex-1 text-xs border border-stone-200 rounded px-2 py-1 bg-white text-stone-700"
                >
                  {["spatial", "mep", "compliance", "boq", "detail", "export", "general"].map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="flex-1 text-xs border border-stone-200 rounded px-2 py-1 bg-white text-stone-700"
                >
                  {["low", "medium", "high"].map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-1 justify-end">
                <button
                  onClick={() => setAddOpen(false)}
                  className="text-xs px-2 py-1 text-stone-400 hover:text-stone-600"
                >
                  Cancel
                </button>
                <button
                  onClick={handleAdd}
                  disabled={!newTitle.trim()}
                  className="text-xs px-3 py-1 bg-stone-800 text-white rounded hover:bg-stone-700 disabled:opacity-50 transition-colors"
                >
                  Add
                </button>
              </div>
            </div>
          )}

          {issues.length === 0 ? (
            <p className="text-xs text-stone-400 text-center py-4">No issues logged.</p>
          ) : (
            <div className="space-y-2">
              {issues.map((issue) => (
                <IssueRow
                  key={issue.id}
                  issue={issue}
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {tab === "qa" && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <button
              onClick={loadQA}
              disabled={loading}
              className="text-xs px-3 py-1 bg-stone-800 text-white rounded hover:bg-stone-700 disabled:opacity-50 transition-colors"
            >
              {loading ? "Running…" : "Run QA"}
            </button>
            {qa && (
              <span className="text-xs text-stone-400">
                {qa.passed}/{qa.items.length} passed · {Math.round(qa.completion_pct)}% complete
              </span>
            )}
          </div>

          {qa && (
            <>
              <div className="grid grid-cols-4 gap-1 text-xs text-center">
                <div className="bg-green-50 rounded p-1.5">
                  <p className="font-semibold text-green-700">{qa.passed}</p>
                  <p className="text-green-600">Pass</p>
                </div>
                <div className="bg-red-50 rounded p-1.5">
                  <p className="font-semibold text-red-700">{qa.failed}</p>
                  <p className="text-red-600">Fail</p>
                </div>
                <div className="bg-amber-50 rounded p-1.5">
                  <p className="font-semibold text-amber-700">{qa.warnings}</p>
                  <p className="text-amber-600">Warn</p>
                </div>
                <div className="bg-stone-50 rounded p-1.5">
                  <p className="font-semibold text-stone-500">{qa.not_checked}</p>
                  <p className="text-stone-400">Skip</p>
                </div>
              </div>

              <div className="space-y-1">
                {qa.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-2 text-xs py-1 border-b border-stone-100 last:border-0"
                  >
                    <span className={`shrink-0 font-mono font-bold ${QA_COLORS[item.status] ?? ""}`}>
                      {QA_ICONS[item.status] ?? "–"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-stone-700 font-medium">{item.title}</p>
                      {item.detail && (
                        <p className="text-stone-400 leading-relaxed">{item.detail}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {qa.advisory && (
                <p className="text-xs text-stone-500 bg-stone-50 rounded p-2 leading-relaxed">
                  {qa.advisory}
                </p>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
