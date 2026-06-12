"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ParameterChange } from "@/features/api/client";
import type { ArchitectureProject, Parameter } from "@/features/project/types";

const ORIENTATIONS = ["north", "south", "east", "west"] as const;
const EDITABLE_KEYS = new Set<ParameterChange["key"]>([
  "site_width",
  "site_depth",
  "orientation",
  "floors",
  "floor_height",
  "style",
]);

function isNumeric(param: Parameter): boolean {
  return typeof param.value === "number";
}

/** Site/building parameter form (Stage 6.2): number, text, and dropdown
 *  inputs with units and a single Apply for all dirty fields. */
export function ParameterEditor({
  project,
  busy,
  onApply,
}: {
  project: ArchitectureProject;
  busy: boolean;
  onApply: (changes: ParameterChange[]) => void;
}) {
  const editable = useMemo(
    () =>
      project.parameters.filter(
        (p) => p.editable && EDITABLE_KEYS.has(p.key as ParameterChange["key"]),
      ),
    [project.parameters],
  );

  const [drafts, setDrafts] = useState<Record<string, string>>({});
  useEffect(() => {
    setDrafts(
      Object.fromEntries(editable.map((p) => [p.key, String(p.value)])),
    );
  }, [editable]);

  const changes: ParameterChange[] = [];
  let invalid = false;
  for (const param of editable) {
    const draft = drafts[param.key];
    if (draft === undefined || draft === String(param.value)) continue;
    if (isNumeric(param)) {
      const num = Number(draft);
      const min = param.min ?? Number.NEGATIVE_INFINITY;
      const max = param.max ?? Number.POSITIVE_INFINITY;
      if (draft === "" || Number.isNaN(num) || num < min || num > max) {
        invalid = true;
        continue;
      }
      changes.push({ key: param.key as ParameterChange["key"], value: num });
    } else if (draft.trim()) {
      changes.push({ key: param.key as ParameterChange["key"], value: draft.trim() });
    }
  }
  const dirty = changes.length > 0;

  function submit() {
    if (dirty && !invalid && !busy) {
      onApply(changes);
    }
  }

  function renderInput(param: Parameter) {
    const draft = drafts[param.key] ?? String(param.value);
    if (param.key === "orientation") {
      return (
        <Select
          value={draft}
          onValueChange={(v) => setDrafts((d) => ({ ...d, [param.key]: v }))}
          disabled={busy}
        >
          <SelectTrigger size="sm" className="h-7 w-28 text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ORIENTATIONS.map((o) => (
              <SelectItem key={o} value={o}>
                {o}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );
    }
    if (isNumeric(param)) {
      const num = Number(draft);
      const outOfRange =
        draft === "" ||
        Number.isNaN(num) ||
        (param.min != null && num < param.min) ||
        (param.max != null && num > param.max);
      return (
        <span className="relative">
          <Input
            aria-label={param.label}
            type="number"
            value={draft}
            min={param.min ?? undefined}
            max={param.max ?? undefined}
            step={param.key === "floors" ? 1 : 0.5}
            onChange={(e) =>
              setDrafts((d) => ({ ...d, [param.key]: e.target.value }))
            }
            onKeyDown={(e) => e.key === "Enter" && submit()}
            className={`h-7 w-28 pr-7 text-xs tabular-nums ${outOfRange ? "border-destructive" : ""}`}
            disabled={busy}
          />
          {param.unit && (
            <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-[10px] text-muted-foreground">
              {param.unit}
            </span>
          )}
        </span>
      );
    }
    return (
      <Input
        aria-label={param.label}
        value={draft}
        onChange={(e) =>
          setDrafts((d) => ({ ...d, [param.key]: e.target.value }))
        }
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className="h-7 w-28 text-xs"
        disabled={busy}
      />
    );
  }

  return (
    <div>
      <div className="divide-y divide-border/60">
        {editable.map((param) => (
          <div
            key={param.key}
            className="flex items-center justify-between gap-3 py-1.5"
          >
            <span className="text-xs text-muted-foreground">
              {param.label}
            </span>
            {renderInput(param)}
          </div>
        ))}
      </div>
      <div className="mt-2.5 flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground/70">
          {invalid
            ? "Some values are out of range"
            : dirty
              ? `${changes.length} pending change${changes.length > 1 ? "s" : ""}`
              : "Edit values, then apply"}
        </span>
        <Button size="sm" onClick={submit} disabled={!dirty || invalid || busy}>
          {busy ? (
            <Loader2 className="size-3 animate-spin" />
          ) : (
            <Check className="size-3" />
          )}
          Apply
        </Button>
      </div>
    </div>
  );
}
