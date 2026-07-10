"use client";

import {
  AlertTriangle,
  Calculator,
  ChevronDown,
  ChevronRight,
  Download,
  Info,
} from "lucide-react";
import { useState } from "react";

import type {
  ArchitectureProject,
  BOQItem,
  CategoryTotal,
  CostPlan,
  RateEntry,
  TileSpec,
} from "@/features/project/types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function inr(n: number) {
  return "₹" + n.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

function ConfidenceBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 85
      ? "text-emerald-600"
      : pct >= 70
        ? "text-amber-600"
        : "text-red-500";
  return (
    <span className={`text-[10px] font-medium tabular-nums ${color}`}>
      {pct}%
    </span>
  );
}

function MissingRateBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-sm bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200">
      <AlertTriangle size={8} />
      Rate missing
    </span>
  );
}

// ── BOQ Line row ──────────────────────────────────────────────────────────────

function BOQRow({ item }: { item: BOQItem }) {
  return (
    <tr className="border-b border-gray-100 hover:bg-gray-50/50 text-xs">
      <td className="py-1.5 pr-3 text-gray-700 max-w-[200px] truncate">
        {item.description}
      </td>
      <td className="py-1.5 pr-3 text-gray-500 text-center">{item.unit}</td>
      <td className="py-1.5 pr-3 text-gray-700 text-right tabular-nums">
        {item.quantity.toLocaleString("en-IN", { maximumFractionDigits: 1 })}
      </td>
      <td className="py-1.5 pr-3 text-right tabular-nums">
        {item.rate === 0 ? (
          <MissingRateBadge />
        ) : (
          <span className="text-gray-700">{inr(item.rate)}</span>
        )}
      </td>
      <td className="py-1.5 text-right tabular-nums font-medium text-gray-900">
        {item.amount > 0 ? inr(item.amount) : "—"}
      </td>
    </tr>
  );
}

// ── Category accordion ────────────────────────────────────────────────────────

function CategorySection({
  category,
  items,
  total,
}: {
  category: string;
  items: BOQItem[];
  total: number;
}) {
  const [open, setOpen] = useState(false);
  const label =
    category.charAt(0).toUpperCase() + category.slice(1).replace(/_/g, " ");
  const hasMissing = items.some((i) => i.rate === 0);

  return (
    <div className="border border-gray-100 rounded-md overflow-hidden mb-2">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <span className="flex items-center gap-2">
          {open ? (
            <ChevronDown size={12} className="text-gray-400" />
          ) : (
            <ChevronRight size={12} className="text-gray-400" />
          )}
          <span className="text-xs font-medium text-gray-800">{label}</span>
          {hasMissing && <AlertTriangle size={10} className="text-amber-500" />}
        </span>
        <span className="text-xs font-semibold text-gray-900 tabular-nums">
          {inr(total)}
        </span>
      </button>
      {open && (
        <div className="px-3 pb-2 overflow-x-auto">
          <table className="w-full min-w-[480px]">
            <thead>
              <tr className="text-[10px] uppercase tracking-wide text-gray-400 border-b border-gray-100">
                <th className="py-1.5 pr-3 text-left font-medium">Item</th>
                <th className="py-1.5 pr-3 text-center font-medium">Unit</th>
                <th className="py-1.5 pr-3 text-right font-medium">Qty</th>
                <th className="py-1.5 pr-3 text-right font-medium">Rate</th>
                <th className="py-1.5 text-right font-medium">Amount</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <BOQRow key={item.id} item={item} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Tile spec editor ──────────────────────────────────────────────────────────

function TileSpecEditor({
  specs,
  onEdit,
}: {
  specs: TileSpec[];
  onEdit: (id: string, field: keyof TileSpec, value: number) => void;
}) {
  if (!specs.length) return null;
  return (
    <div className="mb-4">
      <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium mb-2">
        Tile Specifications
      </p>
      {specs.map((ts) => (
        <div
          key={ts.id}
          className="flex flex-wrap items-center gap-2 p-2 border border-gray-100 rounded-md mb-1 bg-gray-50 text-xs"
        >
          <span className="text-gray-700 font-medium flex-1 min-w-[80px]">
            {ts.label || `${ts.size_w}×${ts.size_h}″`}
          </span>
          <label className="flex items-center gap-1 text-gray-500">
            W
            <input
              type="number"
              defaultValue={ts.size_w}
              onBlur={(e) => onEdit(ts.id, "size_w", parseFloat(e.target.value))}
              className="w-12 border border-gray-200 rounded px-1 py-0.5 text-xs text-right"
            />
            ″
          </label>
          <label className="flex items-center gap-1 text-gray-500">
            H
            <input
              type="number"
              defaultValue={ts.size_h}
              onBlur={(e) => onEdit(ts.id, "size_h", parseFloat(e.target.value))}
              className="w-12 border border-gray-200 rounded px-1 py-0.5 text-xs text-right"
            />
            ″
          </label>
          <label className="flex items-center gap-1 text-gray-500">
            ₹/sqft
            <input
              type="number"
              defaultValue={ts.rate_per_sqft}
              onBlur={(e) => onEdit(ts.id, "rate_per_sqft", parseFloat(e.target.value))}
              className="w-16 border border-gray-200 rounded px-1 py-0.5 text-xs text-right"
            />
          </label>
          <label className="flex items-center gap-1 text-gray-500">
            Waste%
            <input
              type="number"
              defaultValue={ts.wastage_pct}
              onBlur={(e) => onEdit(ts.id, "wastage_pct", parseFloat(e.target.value))}
              className="w-12 border border-gray-200 rounded px-1 py-0.5 text-xs text-right"
            />
          </label>
        </div>
      ))}
    </div>
  );
}

// ── Rate override editor ──────────────────────────────────────────────────────

const RATE_LABELS: Record<string, string> = {
  "flooring/tile_supply":       "Tile supply (₹/sqft)",
  "flooring/tile_laying":       "Tile laying (₹/sqft)",
  "flooring/marble_supply":     "Marble supply (₹/sqft)",
  "paint/interior_paint":       "Interior paint (₹/sqft)",
  "paint/ceiling_paint":        "Ceiling paint (₹/sqft)",
  "doors/interior_door":        "Interior door (₹/nos)",
  "doors/main_door":            "Main door (₹/nos)",
  "windows/upvc_window":        "UPVC window (₹/nos)",
  "plumbing/wc":                "WC (₹/nos)",
  "plumbing/basin":             "Basin (₹/nos)",
  "plumbing/sink":              "Kitchen sink (₹/nos)",
  "electrical/light_point":     "Light point (₹/nos)",
  "electrical/socket_point":    "Socket (₹/nos)",
  "electrical/switch_point":    "Switch (₹/nos)",
};

function RateEditor({
  rates,
  onEdit,
}: {
  rates: RateEntry[];
  onEdit: (category: string, item: string, rate: number) => void;
}) {
  const [open, setOpen] = useState(false);
  if (!rates.length) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-400 p-2 border border-dashed border-gray-200 rounded-md mb-3">
        <Info size={12} />
        Calculate BOQ first to see the rate table.
      </div>
    );
  }
  return (
    <div className="mb-4">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-gray-400 font-medium mb-1 hover:text-gray-600"
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
        Edit Rates
      </button>
      {open && (
        <div className="space-y-1">
          {rates.map((r) => {
            const key = `${r.category}/${r.item}`;
            const label = RATE_LABELS[key] ?? key;
            return (
              <div
                key={key}
                className="flex items-center justify-between gap-2 text-xs"
              >
                <span className="text-gray-600 flex-1 truncate">{label}</span>
                <input
                  type="number"
                  defaultValue={r.rate}
                  onBlur={(e) =>
                    onEdit(r.category, r.item, parseFloat(e.target.value))
                  }
                  className="w-20 border border-gray-200 rounded px-1.5 py-0.5 text-right tabular-nums text-xs"
                />
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Main BOQ Studio ───────────────────────────────────────────────────────────

export interface BOQStudioProps {
  project: ArchitectureProject;
  onCalculate: () => Promise<void>;
  onEditRate: (category: string, item: string, rate: number) => Promise<void>;
  onEditTileSpec: (id: string, field: string, value: number) => Promise<void>;
  calculating: boolean;
}

export function BOQStudio({
  project,
  onCalculate,
  onEditRate,
  onEditTileSpec,
  calculating,
}: BOQStudioProps) {
  const cost = project.cost_plan;
  const mat = project.material_plan;

  // Group items by category
  const grouped: Record<string, BOQItem[]> = {};
  for (const item of cost.boq_items) {
    if (!grouped[item.category]) grouped[item.category] = [];
    grouped[item.category].push(item);
  }
  const totalsMap: Record<string, number> = {};
  for (const ct of cost.category_totals) totalsMap[ct.category] = ct.total;

  const hasMissing = cost.missing_rates.length > 0;

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold text-gray-800">
            Bill of Quantities
          </p>
          {cost.generated && (
            <p className="text-[10px] text-gray-400 mt-0.5">
              Advisory estimate — verify before procurement
            </p>
          )}
        </div>
        <button
          onClick={onCalculate}
          disabled={calculating}
          className="flex items-center gap-1.5 rounded-md bg-gray-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-gray-700 transition-colors disabled:opacity-50"
        >
          <Calculator size={12} />
          {calculating ? "Calculating…" : cost.generated ? "Recalculate" : "Calculate BOQ"}
        </button>
      </div>

      {/* Summary bar */}
      {cost.generated && (
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Grand Total</span>
            <span className="text-base font-bold text-gray-900 tabular-nums">
              {inr(cost.grand_total)}
            </span>
          </div>
          <div className="flex items-center justify-between text-[10px] text-gray-400">
            <span>Confidence</span>
            <ConfidenceBadge value={cost.confidence} />
          </div>
          {hasMissing && (
            <div className="flex items-start gap-1.5 rounded-md bg-amber-50 border border-amber-100 p-2">
              <AlertTriangle size={11} className="text-amber-500 mt-0.5 shrink-0" />
              <p className="text-[10px] text-amber-700">
                {cost.missing_rates.length} item
                {cost.missing_rates.length !== 1 ? "s" : ""} excluded — rates
                not set
              </p>
            </div>
          )}
        </div>
      )}

      {/* Category breakdown */}
      {cost.generated && Object.keys(grouped).length > 0 && (
        <div>
          <p className="text-[10px] uppercase tracking-wide text-gray-400 font-medium mb-2">
            Breakdown by Category
          </p>
          {Object.entries(grouped).map(([cat, items]) => (
            <CategorySection
              key={cat}
              category={cat}
              items={items}
              total={totalsMap[cat] ?? 0}
            />
          ))}
        </div>
      )}

      {/* Tile spec editor */}
      <TileSpecEditor specs={mat.tile_specs} onEdit={onEditTileSpec} />

      {/* Rate editor */}
      <RateEditor
        rates={mat.editable_rates}
        onEdit={async (cat, item, rate) => {
          await onEditRate(cat, item, rate);
        }}
      />

      {/* Assumptions */}
      {cost.generated && cost.assumptions.length > 0 && (
        <div className="rounded-md border border-blue-100 bg-blue-50/50 p-2 space-y-1">
          <p className="text-[10px] uppercase tracking-wide text-blue-400 font-medium">
            Assumptions
          </p>
          {cost.assumptions.map((a, i) => (
            <p key={i} className="text-[10px] text-blue-700">
              • {a}
            </p>
          ))}
        </div>
      )}

      {/* Export links */}
      {cost.generated && (
        <div className="flex gap-2 pt-1">
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              /* download handled by workspace */
            }}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-800 transition-colors"
          >
            <Download size={10} />
            Export CSV
          </a>
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
            }}
            className="flex items-center gap-1 text-[10px] text-gray-500 hover:text-gray-800 transition-colors"
          >
            <Download size={10} />
            Export JSON
          </a>
        </div>
      )}

      {/* Empty state */}
      {!cost.generated && (
        <div className="flex flex-col items-center justify-center py-8 gap-2 text-center">
          <Calculator size={28} className="text-gray-200" />
          <p className="text-xs text-gray-400 max-w-[200px]">
            Calculate the Bill of Quantities to see material costs and a
            breakdown by category.
          </p>
        </div>
      )}
    </div>
  );
}
