"use client";

import { Check, Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { DesignOption } from "@/features/project/types";
import { cn } from "@/lib/utils";

// ── Mini plan renderer ────────────────────────────────────────────────────────

const ROOM_COLORS: Record<string, string> = {
  living: "#e8e0d8",
  kitchen: "#dde8e0",
  bedroom: "#dde4ee",
  bathroom: "#eee8dd",
  balcony: "#e8eed8",
  parking: "#e4e4e4",
  dining: "#e8dde8",
  study: "#dde8e8",
  storage: "#ebebeb",
  cafe_seating: "#e8e0d8",
  cafe_counter: "#dde8e0",
  office: "#dde4ee",
  default: "#efefef",
};

function MiniPlan({ option }: { option: DesignOption }) {
  const { site, rooms } = option.preview;
  const PAD = 4;
  const MAX = 120;
  const scale = Math.min((MAX - PAD * 2) / site.width, (MAX - PAD * 2) / site.depth);
  const w = site.width * scale + PAD * 2;
  const h = site.depth * scale + PAD * 2;

  return (
    <svg
      viewBox={`0 0 ${w} ${h}`}
      width={w}
      height={h}
      className="shrink-0 rounded-sm"
      aria-hidden
    >
      {/* site boundary */}
      <rect
        x={PAD}
        y={PAD}
        width={site.width * scale}
        height={site.depth * scale}
        fill="#f7f6f4"
        stroke="#c8c4bf"
        strokeWidth={0.75}
      />
      {rooms.map((room) => (
        <rect
          key={room.id}
          x={PAD + room.x * scale}
          y={PAD + room.y * scale}
          width={room.width * scale}
          height={room.depth * scale}
          fill={ROOM_COLORS[room.type] ?? ROOM_COLORS.default}
          stroke="#b8b4af"
          strokeWidth={0.5}
        />
      ))}
    </svg>
  );
}

// ── Score badge ───────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 8.5
      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
      : score >= 8.0
        ? "bg-blue-50 text-blue-700 border-blue-200"
        : "bg-amber-50 text-amber-700 border-amber-200";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold tabular-nums",
        color,
      )}
    >
      {score.toFixed(1)}
    </span>
  );
}

// ── Variant label ─────────────────────────────────────────────────────────────

const VARIANT_META: Record<
  DesignOption["variant"],
  { label: string; hint: string }
> = {
  compact: {
    label: "Compact",
    hint: "Efficient · Lower cost",
  },
  balanced: {
    label: "Balanced",
    hint: "Standard · Recommended",
  },
  spacious: {
    label: "Spacious",
    hint: "Generous · Premium feel",
  },
};

// ── Option card ───────────────────────────────────────────────────────────────

function OptionCard({
  option,
  selected,
  onApply,
}: {
  option: DesignOption;
  selected: boolean;
  onApply: () => void;
}) {
  const meta = VARIANT_META[option.variant];
  const rooms = option.preview.rooms;
  const builtArea = rooms.reduce((s, r) => s + r.width * r.depth, 0);

  return (
    <div
      className={cn(
        "flex flex-col gap-3 rounded-xl border bg-card p-4 transition-shadow",
        selected
          ? "border-foreground/30 shadow-[0_0_0_2px_hsl(var(--foreground)/0.12)]"
          : "border-border hover:border-border/80 hover:shadow-sm",
      )}
    >
      {/* header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold leading-tight">{meta.label}</p>
          <p className="mt-0.5 text-[11px] text-muted-foreground">{meta.hint}</p>
        </div>
        <ScoreBadge score={option.score} />
      </div>

      {/* mini plan */}
      <div className="flex justify-center">
        <MiniPlan option={option} />
      </div>

      {/* stats */}
      <div className="flex justify-between text-[11px] text-muted-foreground">
        <span>{rooms.length} rooms</span>
        <span>{Math.round(builtArea)} ft²</span>
      </div>

      {/* summary */}
      <p className="text-[11px] leading-relaxed text-muted-foreground/80">
        {option.summary}
      </p>

      {/* action */}
      <Button
        size="sm"
        variant={selected ? "default" : "outline"}
        className="mt-auto w-full"
        onClick={onApply}
      >
        {selected ? (
          <>
            <Check className="mr-1.5 size-3.5" />
            Applied
          </>
        ) : (
          "Apply this option"
        )}
      </Button>
    </div>
  );
}

// ── Options panel ─────────────────────────────────────────────────────────────

export function OptionsPanel({
  options,
  loading,
  selectedOptionId,
  onApply,
  onClose,
}: {
  options: DesignOption[] | null;
  loading: boolean;
  selectedOptionId: string | null;
  onApply: (option: DesignOption) => void;
  onClose: () => void;
}) {
  return (
    <div className="flex flex-col gap-4 rounded-xl border border-border bg-background p-4 shadow-sm">
      {/* header bar */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold">Design Options</h3>
          <p className="text-[11px] text-muted-foreground">
            Compare compact, balanced, and spacious variants — apply one to continue editing.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="ml-3 shrink-0 rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Close options"
        >
          <X className="size-4" />
        </button>
      </div>

      {/* content */}
      {loading ? (
        <div className="flex h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Generating options…
        </div>
      ) : options && options.length > 0 ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {options.map((opt) => (
            <OptionCard
              key={opt.option_id}
              option={opt}
              selected={opt.option_id === selectedOptionId}
              onApply={() => onApply(opt)}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}
