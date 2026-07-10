"use client";

import { useEffect, useState } from "react";
import { BarChart2, AlertTriangle, Info, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { runFeasibility } from "@/features/api/client";
import type { Feasibility } from "@/features/project/types";

function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-muted-foreground/70 uppercase tracking-wider">{label}</span>
      <span className="text-[13px] font-semibold tabular-nums">{value}</span>
      {sub && <span className="text-[10px] text-muted-foreground">{sub}</span>}
    </div>
  );
}

export function FeasibilitySection({ projectId }: { projectId: string | null }) {
  const [data, setData] = useState<Feasibility | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await runFeasibility(projectId);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Feasibility unavailable");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (projectId) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  if (!projectId) {
    return (
      <p className="text-[11px] text-muted-foreground/70">
        Generate a design to run feasibility analysis.
      </p>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <RefreshCw className="h-3 w-3 animate-spin" /> Computing…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-destructive">
        <AlertTriangle className="h-3 w-3" /> {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-2 rounded-lg border border-border bg-muted/30 p-2.5">
        <Metric
          label="Site area"
          value={`${data.site_area.toFixed(0)} ft²`}
        />
        <Metric
          label="Usable footprint"
          value={`${data.usable_footprint.toFixed(0)} ft²`}
          sub={`${data.coverage_pct.toFixed(0)}% coverage`}
        />
        <Metric
          label="Buildable area"
          value={`${data.buildable_area.toFixed(0)} ft²`}
          sub={`FSI ${data.fsi_far.toFixed(1)}`}
        />
        <Metric
          label="Parking"
          value={`${data.parking_estimate} slot${data.parking_estimate !== 1 ? "s" : ""}`}
        />
      </div>

      {data.options.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground/70">
            Development options
          </span>
          <div className="flex flex-col gap-1">
            {data.options.slice(0, 3).map((opt) => (
              <div
                key={opt.name}
                className="flex items-center justify-between rounded-md border border-border bg-card px-2.5 py-1.5 text-[11px]"
              >
                <div className="flex flex-col">
                  <span className="font-medium">{opt.label}</span>
                  <span className="text-muted-foreground">{opt.description}</span>
                </div>
                <span className="ml-2 shrink-0 tabular-nums text-muted-foreground">
                  {opt.built_up_area.toFixed(0)} ft²
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.missing_inputs.length > 0 && (
        <div className="rounded-md border border-amber-200 bg-amber-50/80 px-2.5 py-2 text-[11px] text-amber-800">
          <p className="font-medium">Missing inputs:</p>
          <ul className="mt-0.5 list-disc pl-3">
            {data.missing_inputs.map((m) => <li key={m}>{m}</li>)}
          </ul>
        </div>
      )}

      {data.warnings.map((w) => (
        <div key={w} className="flex items-start gap-1.5 text-[11px] text-amber-700">
          <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
          {w}
        </div>
      ))}

      {data.assumptions.length > 0 && (
        <div className="flex items-start gap-1.5 text-[10px] text-muted-foreground/60">
          <Info className="mt-0.5 h-3 w-3 shrink-0" />
          <span>{data.assumptions[0]}</span>
        </div>
      )}

      <Button
        variant="outline"
        size="sm"
        className="w-full gap-1.5 text-xs"
        onClick={load}
        disabled={loading}
      >
        <BarChart2 className="h-3 w-3" />
        Refresh feasibility
      </Button>
    </div>
  );
}
