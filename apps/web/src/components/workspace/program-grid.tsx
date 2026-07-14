"use client";

import { useEffect, useRef, useState } from "react";
import { Loader2, Plus, X } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ParameterChange } from "@/features/api/client";
import type { ArchitectureProject } from "@/features/project/types";
import { cn } from "@/lib/utils";

// ── Constants ──────────────────────────────────────────────────────────────────

const ROOM_TYPES = [
  // "Bedroom" auto-becomes "Master Bedroom" for the first one added to a
  // project (regenerate.py's _default_room_name) — there's no separate
  // "master_bedroom" room type, so it isn't a distinct dropdown entry.
  { value: "bedroom", label: "Bedroom" },
  { value: "bathroom", label: "Bathroom" },
  { value: "restroom", label: "Restroom" },
  { value: "living", label: "Living Room" },
  { value: "seating", label: "Seating Area" },
  { value: "kitchen", label: "Kitchen" },
  { value: "kitchenette", label: "Kitchenette" },
  { value: "dining", label: "Dining" },
  { value: "study", label: "Study" },
  { value: "foyer", label: "Foyer" },
  { value: "storage", label: "Storage" },
  { value: "balcony", label: "Balcony" },
  { value: "parking", label: "Parking" },
  { value: "office", label: "Office / Workspace" },
  { value: "cafe_seating", label: "Café Seating" },
  { value: "cafe_counter", label: "Café Counter" },
] as const;

const ORIENTATIONS = ["north", "south", "east", "west"] as const;
const DEBOUNCE_MS = 400;
const SITE_MIN = 10;
const SITE_MAX = 300;
const SITE_FLOORS_MAX = 4;
const ROOM_MIN = 3;
const ROOM_MAX = 60;

// ── Helpers ────────────────────────────────────────────────────────────────────

function numValid(v: string, min: number, max: number): boolean {
  const n = Number(v);
  return v !== "" && !Number.isNaN(n) && n >= min && n <= max;
}

/** Compact inline number cell (no spinner arrows, tabular-nums). */
function NumCell({
  value,
  min,
  max,
  step = 0.5,
  suffix,
  disabled,
  onChange,
  onCommit,
}: {
  value: string;
  min: number;
  max: number;
  step?: number;
  suffix?: string;
  disabled: boolean;
  onChange: (v: string) => void;
  onCommit?: () => void;
}) {
  const valid = numValid(value, min, max);
  return (
    <div className="relative">
      <input
        type="number"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onCommit?.()}
        className={cn(
          "h-7 w-full rounded border bg-transparent px-1.5 text-right text-xs tabular-nums outline-none transition-colors",
          "focus:border-sky-400 focus:ring-1 focus:ring-sky-400/30",
          valid
            ? "border-border/60 hover:border-border"
            : "border-destructive/60",
          suffix ? "pr-6" : "",
          disabled && "cursor-not-allowed opacity-50",
        )}
      />
      {suffix && (
        <span className="pointer-events-none absolute inset-y-0 right-1.5 flex items-center text-[9px] text-muted-foreground/60">
          {suffix}
        </span>
      )}
    </div>
  );
}

/** Compact inline text cell. */
function TextCell({
  value,
  disabled,
  onChange,
  onCommit,
}: {
  value: string;
  disabled: boolean;
  onChange: (v: string) => void;
  onCommit?: () => void;
}) {
  return (
    <input
      type="text"
      value={value}
      disabled={disabled}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => e.key === "Enter" && onCommit?.()}
      className={cn(
        "h-7 w-full rounded border border-border/60 bg-transparent px-1.5 text-xs outline-none transition-colors",
        "hover:border-border focus:border-sky-400 focus:ring-1 focus:ring-sky-400/30",
        disabled && "cursor-not-allowed opacity-50",
      )}
    />
  );
}

// ── Column header ──────────────────────────────────────────────────────────────

function ColHead({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "px-1 py-1 text-[9px] font-medium uppercase tracking-wider text-muted-foreground/60",
        className,
      )}
    >
      {children}
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────

type SiteDrafts = {
  site_width: string;
  site_depth: string;
  orientation: string;
  floors: string;
};

type RoomDraft = { name: string; width: string; depth: string };

/**
 * Snaptrude-style unified program grid — replaces the separate Parameters and
 * Room Schedule sections. One editable cell → debounce 400 ms → regenerate.
 */
export function ProgramGrid({
  project,
  selectedRoomId,
  onSelectRoom,
  busy,
  onApplyChanges,
}: {
  project: ArchitectureProject;
  selectedRoomId: string | null;
  onSelectRoom: (id: string | null) => void;
  busy: boolean;
  onApplyChanges: (changes: ParameterChange[]) => void;
}) {
  // ── Draft state ──────────────────────────────────────────────────────────────
  const [site, setSite] = useState<SiteDrafts>({
    site_width: String(project.site.width),
    site_depth: String(project.site.depth),
    orientation: project.site.orientation,
    floors: String(project.building.floors),
  });

  const [rooms, setRooms] = useState<Record<string, RoomDraft>>(() =>
    Object.fromEntries(
      project.rooms.map((r) => [r.id, { name: r.name, width: String(r.width), depth: String(r.depth) }]),
    ),
  );

  const [addType, setAddType] = useState<string>("bedroom");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingRef = useRef(false);

  // Sync drafts when the project updates from outside (after apply or restore).
  useEffect(() => {
    if (pendingRef.current) return; // don't reset while debounce is in flight
    setSite({
      site_width: String(project.site.width),
      site_depth: String(project.site.depth),
      orientation: project.site.orientation,
      floors: String(project.building.floors),
    });
    setRooms(
      Object.fromEntries(
        project.rooms.map((r) => [r.id, { name: r.name, width: String(r.width), depth: String(r.depth) }]),
      ),
    );
  }, [project]);

  // ── Debounced change collection ───────────────────────────────────────────────

  function scheduleApply(newSite: SiteDrafts, newRooms: Record<string, RoomDraft>) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    pendingRef.current = true;
    debounceRef.current = setTimeout(() => {
      pendingRef.current = false;
      const changes: ParameterChange[] = [];

      if (numValid(newSite.site_width, SITE_MIN, SITE_MAX)) {
        const v = Number(newSite.site_width);
        if (v !== project.site.width) changes.push({ key: "site_width", value: v });
      }
      if (numValid(newSite.site_depth, SITE_MIN, SITE_MAX)) {
        const v = Number(newSite.site_depth);
        if (v !== project.site.depth) changes.push({ key: "site_depth", value: v });
      }
      if (newSite.orientation !== project.site.orientation) {
        changes.push({ key: "orientation", value: newSite.orientation });
      }
      if (numValid(newSite.floors, 1, SITE_FLOORS_MAX)) {
        const v = Number(newSite.floors);
        if (v !== project.building.floors) changes.push({ key: "floors", value: v });
      }

      for (const room of project.rooms) {
        const draft = newRooms[room.id];
        if (!draft) continue;
        if (draft.name.trim() && draft.name.trim() !== room.name) {
          changes.push({ key: "room_name", value: draft.name.trim(), target_id: room.id });
        }
        if (numValid(draft.width, ROOM_MIN, ROOM_MAX)) {
          const v = Number(draft.width);
          if (v !== room.width) changes.push({ key: "room_width", value: v, target_id: room.id });
        }
        if (numValid(draft.depth, ROOM_MIN, ROOM_MAX)) {
          const v = Number(draft.depth);
          if (v !== room.depth) changes.push({ key: "room_depth", value: v, target_id: room.id });
        }
      }

      if (changes.length > 0) onApplyChanges(changes);
    }, DEBOUNCE_MS);
  }

  function updateSite(key: keyof SiteDrafts, value: string) {
    const next = { ...site, [key]: value };
    setSite(next);
    scheduleApply(next, rooms);
  }

  function updateRoom(id: string, key: keyof RoomDraft, value: string) {
    const next = { ...rooms, [id]: { ...rooms[id]!, [key]: value } };
    setRooms(next);
    scheduleApply(site, next);
  }

  // ── Structural changes (immediate, no debounce) ───────────────────────────────

  function handleAddRoom() {
    if (busy) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    pendingRef.current = false;
    onApplyChanges([{ key: "add_room", value: addType }]);
  }

  function handleRemoveRoom(roomId: string) {
    if (busy) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    pendingRef.current = false;
    onApplyChanges([{ key: "remove_room", value: "", target_id: roomId }]);
  }

  function handleRoomLevel(roomId: string, level: number) {
    if (busy) return;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    pendingRef.current = false;
    onApplyChanges([{ key: "room_level", value: level, target_id: roomId }]);
  }

  // ── Computed totals ───────────────────────────────────────────────────────────
  const builtArea = project.rooms.reduce((s, r) => s + r.width * r.depth, 0);
  const siteArea = project.site.width * project.site.depth;
  const coverage = siteArea > 0 ? (builtArea / siteArea) * 100 : 0;
  const unit = project.units === "meters" ? "m" : "ft";
  const multiFloor = project.building.floors > 1;

  return (
    <div className="flex flex-col gap-3">
      {/* ── Site block ── */}
      <div className="overflow-hidden rounded-lg border border-border">
        <div className="border-b border-border bg-muted/50 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Site
        </div>
        <div className="grid grid-cols-2 gap-x-3 gap-y-1.5 px-3 py-2">
          {(
            [
              { key: "site_width" as const, label: "Width", min: SITE_MIN, max: SITE_MAX, step: 0.5, suffix: unit },
              { key: "site_depth" as const, label: "Depth", min: SITE_MIN, max: SITE_MAX, step: 0.5, suffix: unit },
              { key: "floors" as const, label: "Floors", min: 1, max: SITE_FLOORS_MAX, step: 1, suffix: undefined },
            ] satisfies { key: keyof SiteDrafts; label: string; min: number; max: number; step: number; suffix: string | undefined }[]
          ).map(({ key, label, min, max, step, suffix }) => (
            <label key={key} className="flex flex-col gap-0.5">
              <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/60">
                {label}
              </span>
              <NumCell
                value={site[key]}
                min={min}
                max={max}
                step={step}
                suffix={suffix}
                disabled={busy}
                onChange={(v) => updateSite(key, v)}
              />
            </label>
          ))}
          <label className="flex flex-col gap-0.5">
            <span className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground/60">
              Facing
            </span>
            <Select
              value={site.orientation}
              onValueChange={(v) => updateSite("orientation", v)}
              disabled={busy}
            >
              <SelectTrigger size="sm" className="h-7 text-xs capitalize">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ORIENTATIONS.map((o) => (
                  <SelectItem key={o} value={o} className="capitalize">
                    {o}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
        </div>
      </div>

      {/* ── Room rows ── */}
      <div className="overflow-hidden rounded-lg border border-border">
        {/* Column headers */}
        <div className={cn(
          "gap-1 border-b border-border bg-muted/50 px-2 py-0",
          multiFloor
            ? "grid grid-cols-[1fr_52px_52px_32px_44px_24px]"
            : "grid grid-cols-[1fr_52px_52px_44px_24px]",
        )}>
          <ColHead>Room</ColHead>
          <ColHead className="text-right">W</ColHead>
          <ColHead className="text-right">D</ColHead>
          {multiFloor && <ColHead className="text-right">Lvl</ColHead>}
          <ColHead className="text-right">Area</ColHead>
          <div />
        </div>

        {project.rooms.map((room, i) => {
          const draft = rooms[room.id] ?? { name: room.name, width: String(room.width), depth: String(room.depth) };
          const wNum = Number(draft.width);
          const dNum = Number(draft.depth);
          const area =
            numValid(draft.width, ROOM_MIN, ROOM_MAX) && numValid(draft.depth, ROOM_MIN, ROOM_MAX)
              ? Math.round(wNum * dNum)
              : Math.round(room.width * room.depth);
          const isSelected = room.id === selectedRoomId;

          return (
            <div
              key={room.id}
              className={cn(
                "items-center gap-1 border-b border-border/60 px-2 py-1 last:border-b-0",
                multiFloor
                  ? "grid grid-cols-[1fr_52px_52px_32px_44px_24px]"
                  : "grid grid-cols-[1fr_52px_52px_44px_24px]",
                isSelected ? "bg-sky-50" : i % 2 === 0 ? "bg-transparent" : "bg-muted/20",
              )}
            >
              {/* Name cell — click selects the room */}
              <button
                type="button"
                onClick={() => onSelectRoom(room.id === selectedRoomId ? null : room.id)}
                className="min-w-0 text-left"
                title="Click to select room"
              >
                <TextCell
                  value={draft.name}
                  disabled={busy}
                  onChange={(v) => updateRoom(room.id, "name", v)}
                />
              </button>

              <NumCell
                value={draft.width}
                min={ROOM_MIN}
                max={ROOM_MAX}
                suffix={unit}
                disabled={busy}
                onChange={(v) => updateRoom(room.id, "width", v)}
              />
              <NumCell
                value={draft.depth}
                min={ROOM_MIN}
                max={ROOM_MAX}
                suffix={unit}
                disabled={busy}
                onChange={(v) => updateRoom(room.id, "depth", v)}
              />

              {/* Level column — shown only for multi-floor projects */}
              {multiFloor && (
                <select
                  value={room.level}
                  disabled={busy}
                  onChange={(e) => handleRoomLevel(room.id, Number(e.target.value))}
                  className={cn(
                    "h-7 w-full rounded border border-border/60 bg-transparent px-1 text-right text-xs tabular-nums outline-none",
                    "hover:border-border focus:border-sky-400",
                    busy && "cursor-not-allowed opacity-50",
                  )}
                  aria-label="Floor level"
                >
                  {Array.from({ length: project.building.floors }, (_, i) => (
                    <option key={i} value={i}>{i}</option>
                  ))}
                </select>
              )}

              {/* Area — read-only */}
              <span className="px-1 text-right text-[11px] tabular-nums text-muted-foreground">
                {area}
              </span>

              {/* Delete button */}
              <button
                type="button"
                aria-label={`Remove ${room.name}`}
                onClick={() => handleRemoveRoom(room.id)}
                disabled={busy || project.rooms.length <= 1}
                className={cn(
                  "flex size-5 items-center justify-center rounded text-muted-foreground/40 transition-colors",
                  "hover:bg-destructive/10 hover:text-destructive/70",
                  "disabled:cursor-not-allowed disabled:opacity-25",
                )}
              >
                <X className="size-3" />
              </button>
            </div>
          );
        })}

        {/* Totals row */}
        <div className={cn(
          "items-center gap-1 border-t border-border bg-muted/30 px-2 py-1.5",
          multiFloor
            ? "grid grid-cols-[1fr_52px_52px_32px_44px_24px]"
            : "grid grid-cols-[1fr_52px_52px_44px_24px]",
        )}>
          <span className="text-[11px] font-medium text-muted-foreground">
            Built-up
          </span>
          <span />
          <span />
          {multiFloor && <span />}
          <span className="px-1 text-right text-[11px] font-medium tabular-nums">
            {Math.round(builtArea)}
          </span>
          <span />
        </div>
      </div>

      {/* Coverage + busy hint */}
      <div className="flex items-center justify-between px-0.5">
        <span className="text-[10px] tabular-nums text-muted-foreground/60">
          Coverage {coverage.toFixed(0)}% · Site {Math.round(siteArea)} {unit}²
        </span>
        {busy && (
          <span className="flex items-center gap-1 text-[10px] text-muted-foreground/60">
            <Loader2 className="size-3 animate-spin" />
            Updating…
          </span>
        )}
      </div>

      {/* ── Add room row ── */}
      <div className="flex items-center gap-2">
        <Select value={addType} onValueChange={setAddType} disabled={busy}>
          <SelectTrigger size="sm" className="h-7 flex-1 text-xs">
            <SelectValue placeholder="Room type" />
          </SelectTrigger>
          <SelectContent>
            {ROOM_TYPES.map(({ value, label }) => (
              <SelectItem key={value} value={value} className="text-xs">
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <button
          type="button"
          onClick={handleAddRoom}
          disabled={busy}
          className={cn(
            "flex h-7 items-center gap-1 rounded-md border border-border px-2.5 text-xs text-muted-foreground transition-colors",
            "hover:border-foreground/30 hover:text-foreground",
            "disabled:cursor-not-allowed disabled:opacity-40",
          )}
        >
          <Plus className="size-3" />
          Add room
        </button>
      </div>
    </div>
  );
}

/** Skeleton placeholder while no project is loaded. */
export function ProgramGridSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <div className="overflow-hidden rounded-lg border border-border">
        <div className="border-b border-border bg-muted/50 px-3 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          Site
        </div>
        <div className="grid grid-cols-2 gap-3 px-3 py-2">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="flex flex-col gap-0.5">
              <div className="h-2.5 w-10 rounded bg-muted" />
              <div className="h-7 rounded bg-muted" />
            </div>
          ))}
        </div>
      </div>
      <div className="overflow-hidden rounded-lg border border-border">
        <div className="border-b border-border bg-muted/50 px-2 py-0">
          <div className="h-6" />
        </div>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="grid grid-cols-[1fr_52px_52px_44px_24px] gap-1 border-b border-border/60 px-2 py-1.5 last:border-b-0"
          >
            <div className="h-4 rounded bg-muted" />
            <div className="h-4 rounded bg-muted" />
            <div className="h-4 rounded bg-muted" />
            <div className="h-4 rounded bg-muted" />
            <div />
          </div>
        ))}
      </div>
    </div>
  );
}
