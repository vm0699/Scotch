"use client";

import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  DollarSign,
  Info,
  Loader2,
  Plus,
  RotateCcw,
  ThumbsDown,
  ThumbsUp,
  XCircle,
  Zap,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  createClientChange,
  deleteClientChange,
  listClientChanges,
  updateClientChange,
  type CreateChangeBody,
} from "@/features/api/client";
import type {
  AffectedItem,
  AffectedItems,
  ChangeStatus,
  ClientChangeRequest,
} from "@/features/project/types";

// ── Status display helpers ────────────────────────────────────────────────────

const STATUS_CONFIG: Record<ChangeStatus, { label: string; className: string; icon: React.ComponentType<{ className?: string }> }> = {
  pending:  { label: "Pending",  className: "bg-amber-50 text-amber-700 border-amber-200",   icon: Clock },
  approved: { label: "Approved", className: "bg-blue-50 text-blue-700 border-blue-200",      icon: CheckCircle2 },
  applied:  { label: "Applied",  className: "bg-emerald-50 text-emerald-700 border-emerald-200", icon: CheckCircle2 },
  rejected: { label: "Rejected", className: "bg-red-50 text-red-700 border-red-200",         icon: XCircle },
  reverted: { label: "Reverted", className: "bg-gray-50 text-gray-600 border-gray-200",      icon: RotateCcw },
};

const SEVERITY_ICON: Record<AffectedItem["severity"], React.ComponentType<{ className?: string }>> = {
  info:          Info,
  warning:       AlertTriangle,
  action_needed: Zap,
};

const SEVERITY_COLOR: Record<AffectedItem["severity"], string> = {
  info:          "text-muted-foreground",
  warning:       "text-amber-600",
  action_needed: "text-red-600",
};

const MODULE_LABEL: Record<string, string> = {
  rooms:      "Floor Plan",
  mep:        "MEP",
  boq:        "BOQ / Cost",
  compliance: "Compliance",
  details:    "Details",
  exports:    "Exports",
  plugins:    "Plugins",
};

// ── Affected items display ────────────────────────────────────────────────────

function AffectedSection({ title, items }: { title: string; items: AffectedItem[] }) {
  const [open, setOpen] = useState(false);
  if (items.length === 0) return null;
  const Icon = open ? ChevronDown : ChevronRight;
  const actionCount = items.filter((i) => i.severity === "action_needed").length;

  return (
    <div className="rounded-md border border-border/60 bg-muted/30">
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
        onClick={() => setOpen(!open)}
      >
        <Icon className="size-3 shrink-0 text-muted-foreground" />
        <span className="flex-1 text-[11px] font-medium">{title}</span>
        <span className="text-[10px] text-muted-foreground">
          {items.length} item{items.length !== 1 ? "s" : ""}
          {actionCount > 0 && (
            <span className="ml-1 font-medium text-red-600">· {actionCount} action{actionCount !== 1 ? "s" : ""}</span>
          )}
        </span>
      </button>
      {open && (
        <ul className="border-t border-border/40 divide-y divide-border/30">
          {items.map((item, i) => {
            const SIcon = SEVERITY_ICON[item.severity];
            return (
              <li key={i} className="flex items-start gap-2 px-3 py-2">
                <SIcon className={`mt-0.5 size-3 shrink-0 ${SEVERITY_COLOR[item.severity]}`} />
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] leading-4">{item.description}</p>
                  {item.action && (
                    <p className="mt-0.5 text-[10px] text-muted-foreground">{item.action}</p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ── Single change card ────────────────────────────────────────────────────────

function ChangeCard({
  change,
  projectId,
  onRefresh,
}: {
  change: ClientChangeRequest;
  projectId: string;
  onRefresh: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const cfg = STATUS_CONFIG[change.status];
  const StatusIcon = cfg.icon;
  const ai = change.affected_items;

  const setStatus = async (status: ChangeStatus) => {
    setBusy(true);
    try {
      await updateClientChange(projectId, change.id, { status });
      onRefresh();
      toast.success(`Change ${status === "approved" ? "approved" : status === "rejected" ? "rejected" : status}.`);
    } catch {
      toast.error("Could not update change — engine offline.");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    setBusy(true);
    try {
      await deleteClientChange(projectId, change.id);
      onRefresh();
      toast.success("Change removed.");
    } catch {
      toast.error("Could not delete change.");
    } finally {
      setBusy(false);
    }
  };

  const ExpIcon = expanded ? ChevronDown : ChevronRight;

  return (
    <div className="rounded-lg border border-border/60 bg-card shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      {/* Header row */}
      <div className="flex items-start gap-2 p-3">
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-0.5 shrink-0"
          aria-label="Toggle change details"
        >
          <ExpIcon className="size-3.5 text-muted-foreground" />
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-[12px] font-medium leading-5 line-clamp-2">{change.request_text}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[10px] font-medium ${cfg.className}`}>
              <StatusIcon className="size-3" />
              {cfg.label}
            </span>
            {change.priority !== "medium" && (
              <span className={`text-[10px] font-medium ${change.priority === "urgent" || change.priority === "high" ? "text-red-600" : "text-muted-foreground"}`}>
                {change.priority.charAt(0).toUpperCase() + change.priority.slice(1)}
              </span>
            )}
            {ai && (
              <span className="text-[10px] text-muted-foreground">
                {ai.total_count} item{ai.total_count !== 1 ? "s" : ""} affected
              </span>
            )}
          </div>
          {change.summary && !expanded && (
            <p className="mt-1 text-[10px] leading-4 text-muted-foreground line-clamp-1">{change.summary}</p>
          )}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && ai && (
        <div className="border-t border-border/40 px-3 pb-3 pt-2 space-y-2">
          {ai.summary && (
            <p className="text-[11px] leading-4 text-foreground/80">{ai.summary}</p>
          )}
          {ai.cost_impact && (
            <div className="flex items-center gap-2 rounded-md bg-amber-50 border border-amber-100 px-2.5 py-1.5">
              <DollarSign className="size-3 shrink-0 text-amber-600" />
              <p className="text-[11px] text-amber-800">{ai.cost_impact}</p>
            </div>
          )}
          <div className="space-y-1.5">
            {Object.entries(MODULE_LABEL).map(([key, label]) => {
              const items = ai[key as keyof AffectedItems] as AffectedItem[] | undefined;
              if (!items || !Array.isArray(items) || items.length === 0) return null;
              return <AffectedSection key={key} title={label} items={items} />;
            })}
          </div>
        </div>
      )}

      {/* Action buttons */}
      {(change.status === "pending" || change.status === "approved") && (
        <div className="border-t border-border/40 flex items-center gap-2 px-3 py-2">
          {change.status === "pending" && (
            <>
              <Button
                variant="outline"
                size="sm"
                className="h-7 gap-1.5 text-[11px]"
                disabled={busy}
                onClick={() => void setStatus("approved")}
              >
                {busy ? <Loader2 className="size-3 animate-spin" /> : <ThumbsUp className="size-3" />}
                Approve
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-7 gap-1.5 text-[11px] text-muted-foreground"
                disabled={busy}
                onClick={() => void setStatus("rejected")}
              >
                <ThumbsDown className="size-3" />
                Reject
              </Button>
            </>
          )}
          {change.status === "approved" && (
            <Button
              variant="outline"
              size="sm"
              className="h-7 gap-1.5 text-[11px] text-emerald-700 border-emerald-200 hover:bg-emerald-50"
              disabled={busy}
              onClick={() => void setStatus("applied")}
            >
              <CheckCircle2 className="size-3" />
              Mark Applied
            </Button>
          )}
          <div className="flex-1" />
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-[10px] text-muted-foreground/60 hover:text-destructive"
            disabled={busy}
            onClick={() => void handleDelete()}
          >
            Remove
          </Button>
        </div>
      )}

      {change.status === "applied" && (
        <div className="border-t border-border/40 flex items-center gap-2 px-3 py-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1.5 text-[11px] text-muted-foreground"
            disabled={busy}
            onClick={() => void setStatus("reverted")}
          >
            <RotateCcw className="size-3" />
            Revert
          </Button>
          <div className="flex-1" />
          <span className="text-[10px] text-muted-foreground">
            {new Date(change.created_at).toLocaleDateString()}
          </span>
        </div>
      )}
    </div>
  );
}

// ── New change form ───────────────────────────────────────────────────────────

function NewChangeForm({ projectId, onCreated }: { projectId: string; onCreated: () => void }) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [priority, setPriority] = useState<CreateChangeBody["priority"]>("medium");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      await createClientChange(projectId, { request_text: text.trim(), priority, compute_affected: true });
      toast.success("Change request created with affected-item analysis.");
      setText("");
      setOpen(false);
      onCreated();
    } catch {
      toast.error("Could not create change request — engine offline.");
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="w-full justify-start gap-2 text-[11px]"
        onClick={() => setOpen(true)}
      >
        <Plus className="size-3.5" />
        Log client change request
      </Button>
    );
  }

  return (
    <div className="rounded-lg border border-border/60 bg-card p-3 space-y-2.5">
      <p className="text-[11px] font-medium">New change request</p>
      <textarea
        className="w-full resize-none rounded-md border border-border/60 bg-background px-3 py-2 text-[12px] placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-ring"
        rows={3}
        placeholder="e.g. Client asked to add an attached toilet to master bedroom"
        value={text}
        onChange={(e) => setText(e.target.value)}
        autoFocus
      />
      <div className="flex items-center gap-2">
        <select
          className="rounded border border-border/60 bg-background px-2 py-1 text-[11px] text-foreground focus:outline-none"
          value={priority}
          onChange={(e) => setPriority(e.target.value as CreateChangeBody["priority"])}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-[11px]"
          onClick={() => { setOpen(false); setText(""); }}
        >
          Cancel
        </Button>
        <Button
          size="sm"
          className="h-7 text-[11px]"
          disabled={busy || !text.trim()}
          onClick={() => void handleSubmit()}
        >
          {busy ? <Loader2 className="size-3 animate-spin" /> : null}
          Analyse & Log
        </Button>
      </div>
    </div>
  );
}

// ── Main ChangeInbox ──────────────────────────────────────────────────────────

export function ChangeInbox({ projectId }: { projectId: string | null }) {
  const [changes, setChanges] = useState<ClientChangeRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState<"all" | "pending" | "applied">("all");

  const load = useCallback(() => {
    if (!projectId) return;
    setLoading(true);
    listClientChanges(projectId)
      .then(setChanges)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  if (!projectId) {
    return (
      <p className="text-[11px] text-muted-foreground/70">
        Generate a plan to track client change requests.
      </p>
    );
  }

  const filtered = filter === "all" ? changes : changes.filter((c) => {
    if (filter === "pending") return c.status === "pending" || c.status === "approved";
    if (filter === "applied") return c.status === "applied" || c.status === "reverted";
    return true;
  });

  const pendingCount = changes.filter((c) => c.status === "pending").length;

  return (
    <div className="flex flex-col gap-3">
      {/* Summary row */}
      {changes.length > 0 && (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            {(["all", "pending", "applied"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${
                  filter === f
                    ? "bg-foreground text-background"
                    : "bg-muted text-muted-foreground hover:bg-muted/80"
                }`}
              >
                {f === "all" ? `All (${changes.length})` : f === "pending" ? `Pending (${pendingCount})` : "Applied"}
              </button>
            ))}
          </div>
          {loading && <Loader2 className="size-3 animate-spin text-muted-foreground" />}
        </div>
      )}

      {loading && changes.length === 0 && (
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <Loader2 className="size-3 animate-spin" /> Loading changes...
        </div>
      )}

      {!loading && filtered.length === 0 && changes.length > 0 && (
        <p className="text-[11px] text-muted-foreground/70">No {filter} changes.</p>
      )}

      {!loading && changes.length === 0 && (
        <p className="text-[11px] text-muted-foreground/70">
          No change requests yet. Log a client request to see affected items across plan, MEP, BOQ, and exports.
        </p>
      )}

      {filtered.map((change) => (
        <ChangeCard
          key={change.id}
          change={change}
          projectId={projectId}
          onRefresh={load}
        />
      ))}

      <NewChangeForm projectId={projectId} onCreated={load} />
    </div>
  );
}
