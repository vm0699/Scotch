"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ParameterChange } from "@/features/api/client";
import { roomArea, unitLabel, type Room, type Units } from "@/features/project/types";

const ROOM_MIN = 3;
const ROOM_MAX = 60;

/**
 * Shared room editing form — rendered both in the Design Data panel and in
 * the on-canvas popover (the CADAM signature interaction). Emits only the
 * fields that actually changed, as ParameterChange entries.
 */
export function RoomEditor({
  room,
  units,
  busy,
  compact = false,
  onApply,
}: {
  room: Room;
  units: Units;
  busy: boolean;
  compact?: boolean;
  onApply: (changes: ParameterChange[]) => void;
}) {
  const [name, setName] = useState(room.name);
  const [width, setWidth] = useState(String(room.width));
  const [depth, setDepth] = useState(String(room.depth));

  // Re-sync drafts when the selection or the underlying room changes.
  useEffect(() => {
    setName(room.name);
    setWidth(String(room.width));
    setDepth(String(room.depth));
  }, [room]);

  const widthNum = Number(width);
  const depthNum = Number(depth);
  const widthValid =
    width !== "" && widthNum >= ROOM_MIN && widthNum <= ROOM_MAX;
  const depthValid =
    depth !== "" && depthNum >= ROOM_MIN && depthNum <= ROOM_MAX;

  const changes: ParameterChange[] = [];
  if (name.trim() && name.trim() !== room.name) {
    changes.push({ key: "room_name", value: name.trim(), target_id: room.id });
  }
  if (widthValid && widthNum !== room.width) {
    changes.push({ key: "room_width", value: widthNum, target_id: room.id });
  }
  if (depthValid && depthNum !== room.depth) {
    changes.push({ key: "room_depth", value: depthNum, target_id: room.id });
  }
  const dirty = changes.length > 0;
  const valid = widthValid && depthValid;
  const unit = unitLabel(units);

  function submit() {
    if (dirty && valid && !busy) {
      onApply(changes);
    }
  }

  const inputSize = compact ? "h-7 text-xs" : "h-8 text-sm";

  return (
    <div className="flex flex-col gap-2">
      <Input
        aria-label="Room name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className={inputSize}
        disabled={busy}
      />
      <div className="grid grid-cols-2 gap-2">
        {(
          [
            ["Width", width, setWidth, widthValid],
            ["Depth", depth, setDepth, depthValid],
          ] as const
        ).map(([label, value, setValue, isValid]) => (
          <label key={label} className="flex flex-col gap-1">
            <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              {label}
            </span>
            <span className="relative">
              <Input
                aria-label={`Room ${label.toLowerCase()}`}
                type="number"
                min={ROOM_MIN}
                max={ROOM_MAX}
                step={0.5}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && submit()}
                className={`${inputSize} pr-7 tabular-nums ${isValid ? "" : "border-destructive"}`}
                disabled={busy}
              />
              <span className="pointer-events-none absolute inset-y-0 right-2 flex items-center text-[10px] text-muted-foreground">
                {unit}
              </span>
            </span>
          </label>
        ))}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-[11px] tabular-nums text-muted-foreground">
          {widthValid && depthValid
            ? `${(widthNum * depthNum).toFixed(0)} ${unit}²`
            : `${ROOM_MIN}–${ROOM_MAX} ${unit}`}
          {!dirty && valid && ` · ${roomArea(room).toFixed(0)} ${unit}² now`}
        </span>
        <Button
          size={compact ? "xs" : "sm"}
          onClick={submit}
          disabled={!dirty || !valid || busy}
        >
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
