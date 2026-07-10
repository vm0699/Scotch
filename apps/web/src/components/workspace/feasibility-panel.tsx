"use client";

import { useState } from "react";
import type { Feasibility, FeasibilityOption } from "@/features/project/types";
import { runFeasibility } from "@/features/api/client";

interface Props {
  projectId: string;
}

function OptionCard({ opt }: { opt: FeasibilityOption }) {
  const pct = Math.round(opt.coverage_pct);
  return (
    <div className="border border-stone-200 rounded-lg p-3 space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-stone-700 uppercase tracking-wide">
          {opt.label}
        </span>
        <span className="text-xs text-stone-500">{opt.unit_type}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-xs text-stone-600">
        <span>
          <span className="font-medium text-stone-800">{opt.unit_count}</span> units
        </span>
        <span>
          <span className="font-medium text-stone-800">{pct}%</span> coverage
        </span>
        <span>
          <span className="font-medium text-stone-800">{opt.parking_slots}</span> parking
        </span>
      </div>
      <p className="text-xs text-stone-500 leading-relaxed">{opt.description}</p>
      {opt.trade_offs.length > 0 && (
        <ul className="text-xs text-stone-400 space-y-0.5 mt-1">
          {opt.trade_offs.map((t, i) => (
            <li key={i} className="flex gap-1">
              <span>·</span>
              <span>{t}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function FeasibilityPanel({ projectId }: Props) {
  const [roadWidth, setRoadWidth] = useState("");
  const [result, setResult] = useState<Feasibility | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const rw = parseFloat(roadWidth) || 0;
      const data = await runFeasibility(projectId, rw);
      setResult(data);
    } catch {
      setError("Failed to compute feasibility. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h3 className="text-xs font-semibold text-stone-500 uppercase tracking-widest">
          Feasibility / Yield Analysis
        </h3>
        <p className="text-xs text-stone-400">
          Tamil Nadu setback table · FSI 1.5 · 5 development options
        </p>
      </div>

      <div className="flex gap-2">
        <div className="flex-1">
          <label className="block text-xs text-stone-500 mb-1">Road width (ft)</label>
          <input
            type="number"
            min={0}
            step={5}
            value={roadWidth}
            onChange={(e) => setRoadWidth(e.target.value)}
            placeholder="e.g. 30"
            className="w-full text-xs border border-stone-200 rounded px-2 py-1.5 bg-white text-stone-800 placeholder-stone-300 focus:outline-none focus:border-stone-400"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={run}
            disabled={loading}
            className="text-xs px-3 py-1.5 bg-stone-800 text-white rounded hover:bg-stone-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Computing…" : "Run"}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-500">{error}</p>
      )}

      {result && (
        <div className="space-y-4">
          {result.missing_inputs.length > 0 && (
            <div className="bg-amber-50 border border-amber-200 rounded p-2">
              <p className="text-xs font-medium text-amber-700 mb-1">Missing inputs</p>
              {result.missing_inputs.map((m) => (
                <p key={m} className="text-xs text-amber-600">· {m}</p>
              ))}
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="bg-stone-50 rounded p-2 space-y-0.5">
              <p className="text-stone-400">Site area</p>
              <p className="font-semibold text-stone-800">{result.site_area.toFixed(0)} sqft</p>
            </div>
            <div className="bg-stone-50 rounded p-2 space-y-0.5">
              <p className="text-stone-400">Usable footprint</p>
              <p className="font-semibold text-stone-800">{result.usable_footprint.toFixed(0)} sqft</p>
            </div>
            <div className="bg-stone-50 rounded p-2 space-y-0.5">
              <p className="text-stone-400">FSI / FAR</p>
              <p className="font-semibold text-stone-800">{result.fsi_far}</p>
            </div>
            <div className="bg-stone-50 rounded p-2 space-y-0.5">
              <p className="text-stone-400">Buildable area</p>
              <p className="font-semibold text-stone-800">{result.buildable_area.toFixed(0)} sqft</p>
            </div>
            <div className="bg-stone-50 rounded p-2 space-y-0.5">
              <p className="text-stone-400">Parking estimate</p>
              <p className="font-semibold text-stone-800">{result.parking_estimate} slots</p>
            </div>
            <div className="bg-stone-50 rounded p-2 space-y-0.5">
              <p className="text-stone-400">Confidence</p>
              <p className="font-semibold text-stone-800">{Math.round(result.confidence * 100)}%</p>
            </div>
          </div>

          {result.assumptions.length > 0 && (
            <div className="space-y-1">
              <p className="text-xs font-medium text-stone-500">Assumptions</p>
              {result.assumptions.map((a, i) => (
                <p key={i} className="text-xs text-stone-400">· {a}</p>
              ))}
            </div>
          )}

          {result.options.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-stone-600">Development Options</p>
              {result.options.map((opt) => (
                <OptionCard key={opt.name} opt={opt} />
              ))}
            </div>
          )}

          {result.needs_review && (
            <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded p-2">
              This analysis requires professional verification before submission.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
