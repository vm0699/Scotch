"use client";

/**
 * Stage 43.4 — Interior Design Studio panel.
 *
 * Shows the currently selected room's furniture (real catalog-backed items),
 * a Generate control (deterministic / AI / hybrid + style), and per-item
 * edit controls (rotate / swap / delete / recolor). Selecting an item here
 * highlights it on the 2D plan and in the 3D view (Stage 43.2's room-focus
 * camera). Moving an item is done by dragging it directly on the 2D plan
 * (Stage 43.17, floor-plan-svg.tsx) — this panel doesn't duplicate that as a
 * button since drag is the more natural interaction for position.
 *
 * When no room is selected, this panel instead offers "Furnish all rooms"
 * (Stage 43.22) — the same generator run once per room in one action, for
 * filling a whole fresh project without clicking through each room.
 */

import { useEffect, useMemo, useState } from "react";
import { Armchair, Home, Loader2, RotateCw, Sofa, Sparkles, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { getCatalog, resolveCatalogAssetUrl, type CatalogItem, type InteriorEditAction } from "@/features/api/client";
import type { ArchitectureProject, FurnitureItem, InteriorGenerationMode } from "@/features/project/types";

const STYLE_PRESETS = ["modern", "minimalist", "classic", "vintage", "rustic", "industrial"];

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    designed: "bg-emerald-50 text-emerald-700 border-emerald-200",
    stale: "bg-amber-50 text-amber-700 border-amber-200",
    empty: "bg-muted text-muted-foreground border-border",
  };
  return (
    <span className={cn("rounded-full border px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide", styles[status] ?? styles.empty)}>
      {status}
    </span>
  );
}

function FurnitureRow({
  item,
  selected,
  onSelect,
  onRotate,
  onDelete,
  onSwap,
  onRecolor,
  tintColor,
  catalogByCategory,
  busy,
}: {
  item: FurnitureItem;
  selected: boolean;
  onSelect: () => void;
  onRotate: () => void;
  onDelete: () => void;
  onSwap: (catalogId: string) => void;
  onRecolor: (hex: string) => void;
  /** Currently-applied tint hex, resolved from material_overrides against project.materials. */
  tintColor: string | null;
  catalogByCategory: Map<string, CatalogItem[]>;
  busy: boolean;
}) {
  const catalogEntry = useMemo(
    () => Array.from(catalogByCategory.values()).flat().find((c) => c.id === item.catalog_id),
    [catalogByCategory, item.catalog_id],
  );
  const alternatives = catalogEntry ? catalogByCategory.get(catalogEntry.category) ?? [] : [];
  const recolorable = catalogEntry?.material_slots.some((s) => s.slot === "primary" && s.editable) ?? false;

  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-md border px-2 py-1.5 text-left text-xs transition-colors",
        selected ? "border-sky-300 bg-sky-50" : "border-transparent hover:bg-muted/60",
      )}
    >
      <button onClick={onSelect} className="flex flex-1 items-center gap-2 min-w-0 text-left" disabled={busy}>
        {catalogEntry ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={resolveCatalogAssetUrl(catalogEntry.thumbnail_url)}
            alt=""
            className="size-7 shrink-0 rounded border border-border/70 bg-white object-cover"
          />
        ) : (
          <span className="flex size-7 shrink-0 items-center justify-center rounded border border-border/70 bg-muted text-muted-foreground">
            <Armchair className="size-3.5" />
          </span>
        )}
        <span className="min-w-0 flex-1">
          <span className="block truncate font-medium text-foreground">{item.label || item.type}</span>
          <span className="block truncate text-[10px] text-muted-foreground">
            {item.width.toFixed(1)}×{item.depth.toFixed(1)} ft · {item.rotation}°
          </span>
        </span>
      </button>

      {alternatives.length > 1 && (
        <select
          className="h-6 rounded border border-border/70 bg-card px-1 text-[10px]"
          value={item.catalog_id ?? ""}
          disabled={busy}
          onChange={(e) => onSwap(e.target.value)}
          title="Swap for a different piece"
        >
          {alternatives.map((alt) => (
            <option key={alt.id} value={alt.id}>
              {alt.label}
            </option>
          ))}
        </select>
      )}

      {recolorable && (
        <label
          className="relative flex size-6 shrink-0 cursor-pointer items-center justify-center rounded border border-border/70 overflow-hidden"
          title="Recolor (tint)"
        >
          <span
            className="absolute inset-0"
            style={{ backgroundColor: tintColor ?? "#ffffff" }}
          />
          {!tintColor && <span className="relative text-[8px] text-muted-foreground">—</span>}
          <input
            type="color"
            value={tintColor ?? "#ffffff"}
            disabled={busy}
            onChange={(e) => onRecolor(e.target.value)}
            className="absolute inset-0 size-full cursor-pointer opacity-0"
          />
        </label>
      )}

      <Button variant="ghost" size="icon-sm" onClick={onRotate} disabled={busy} aria-label="Rotate 90°" title="Rotate 90°">
        <RotateCw className="size-3.5" />
      </Button>
      <Button variant="ghost" size="icon-sm" onClick={onDelete} disabled={busy} aria-label="Delete" title="Delete">
        <Trash2 className="size-3.5 text-destructive/80" />
      </Button>
    </div>
  );
}

export function InteriorStudio({
  project,
  selectedRoomId,
  selectedFurnitureId,
  onSelectFurniture,
  onGenerate,
  onEdit,
  onGenerateAll,
  busy,
}: {
  project: ArchitectureProject;
  selectedRoomId: string | null;
  selectedFurnitureId: string | null;
  onSelectFurniture: (id: string | null) => void;
  onGenerate: (roomId: string, opts: { mode: InteriorGenerationMode; style: string }) => void;
  onEdit: (roomId: string, edit: InteriorEditAction) => void;
  onGenerateAll?: (opts: { mode: InteriorGenerationMode; style: string; overwrite: boolean }) => void;
  busy: boolean;
}) {
  const [mode, setMode] = useState<InteriorGenerationMode>("deterministic");
  const [style, setStyle] = useState("modern");
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [overwriteAll, setOverwriteAll] = useState(false);

  useEffect(() => {
    getCatalog().then(setCatalog).catch(() => {});
  }, []);

  const catalogByCategory = useMemo(() => {
    const map = new Map<string, CatalogItem[]>();
    for (const item of catalog) {
      const list = map.get(item.category) ?? [];
      list.push(item);
      map.set(item.category, list);
    }
    return map;
  }, [catalog]);

  const materialsById = useMemo(() => new Map(project.materials.map((m) => [m.id, m])), [project.materials]);

  const room = project.rooms.find((r) => r.id === selectedRoomId) ?? null;
  const roomItems = room ? project.furniture.filter((f) => f.room_id === room.id) : [];
  const interior = room ? project.room_interiors.find((ri) => ri.room_id === room.id) : undefined;
  const status = interior?.status ?? (roomItems.length > 0 ? "designed" : "empty");

  if (!room) {
    const furnishedCount = new Set(project.furniture.map((f) => f.room_id)).size;
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-start gap-3">
          <Sofa className="mt-0.5 size-3.5 shrink-0 text-muted-foreground/60" />
          <p className="text-[11px] leading-4 text-muted-foreground/80">
            Click a room on the plan to design its interior — real furniture, editable in 2D and 3D.
          </p>
        </div>

        {onGenerateAll && project.rooms.length > 0 && (
          <div className="flex flex-col gap-1.5 rounded-md border border-border/70 bg-muted/30 p-2">
            <div className="flex items-center gap-1.5 text-[11px] font-medium text-foreground">
              <Home className="size-3.5 text-muted-foreground" />
              Furnish all rooms
            </div>
            <p className="text-[10px] leading-4 text-muted-foreground/80">
              {furnishedCount > 0
                ? `${furnishedCount} of ${project.rooms.length} room(s) already furnished.`
                : `Furnish all ${project.rooms.length} room(s) in one action.`}
            </p>
            <div className="flex gap-1">
              {(["deterministic", "ai", "hybrid"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={cn(
                    "flex-1 rounded-md border px-1.5 py-1 text-[10px] font-medium capitalize transition-colors",
                    mode === m ? "border-foreground/20 bg-foreground text-background" : "border-border text-muted-foreground hover:bg-muted/60",
                  )}
                >
                  {m === "deterministic" ? "Rule-based" : m.toUpperCase()}
                </button>
              ))}
            </div>
            <select
              className="h-7 rounded-md border border-border/70 bg-card px-2 text-[11px]"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
            >
              {STYLE_PRESETS.map((s) => (
                <option key={s} value={s} className="capitalize">
                  {s}
                </option>
              ))}
            </select>
            {furnishedCount > 0 && (
              <label className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                <input
                  type="checkbox"
                  checked={overwriteAll}
                  onChange={(e) => setOverwriteAll(e.target.checked)}
                  disabled={busy}
                />
                Regenerate already-furnished rooms too
              </label>
            )}
            <Button
              size="sm"
              variant="outline"
              className="w-full justify-center gap-2"
              disabled={busy}
              onClick={() => onGenerateAll({ mode, style, overwrite: overwriteAll })}
            >
              {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Home className="size-3.5" />}
              Furnish all rooms
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium text-foreground">{room.name}</span>
        <StatusBadge status={status} />
      </div>

      {interior?.warnings && interior.warnings.length > 0 && (
        <ul className="space-y-0.5 rounded-md border border-amber-200 bg-amber-50 p-1.5 text-[10px] text-amber-800">
          {interior.warnings.map((w, i) => (
            <li key={i}>· {w}</li>
          ))}
        </ul>
      )}

      <div className="flex flex-col gap-1.5">
        <div className="flex gap-1">
          {(["deterministic", "ai", "hybrid"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={cn(
                "flex-1 rounded-md border px-1.5 py-1 text-[10px] font-medium capitalize transition-colors",
                mode === m ? "border-foreground/20 bg-foreground text-background" : "border-border text-muted-foreground hover:bg-muted/60",
              )}
            >
              {m === "deterministic" ? "Rule-based" : m.toUpperCase()}
            </button>
          ))}
        </div>
        <select
          className="h-7 rounded-md border border-border/70 bg-card px-2 text-[11px]"
          value={style}
          onChange={(e) => setStyle(e.target.value)}
        >
          {STYLE_PRESETS.map((s) => (
            <option key={s} value={s} className="capitalize">
              {s}
            </option>
          ))}
        </select>
        <Button
          size="sm"
          className="w-full justify-center gap-2"
          disabled={busy}
          onClick={() => onGenerate(room.id, { mode, style })}
        >
          {busy ? <Loader2 className="size-3.5 animate-spin" /> : <Sparkles className="size-3.5" />}
          {roomItems.length > 0 ? "Regenerate interior" : "Generate interior"}
        </Button>
      </div>

      {roomItems.length > 0 && (
        <div className="flex flex-col gap-1">
          {roomItems.map((item) => (
            <FurnitureRow
              key={item.id}
              item={item}
              selected={item.id === selectedFurnitureId}
              onSelect={() => onSelectFurniture(item.id === selectedFurnitureId ? null : item.id)}
              onRotate={() => {
                const next = ((item.rotation + 90) % 360) as 0 | 90 | 180 | 270;
                onEdit(room.id, { action: "rotate", item_id: item.id, rotation: next });
              }}
              onDelete={() => onEdit(room.id, { action: "delete", item_id: item.id })}
              onSwap={(catalogId) => onEdit(room.id, { action: "swap", item_id: item.id, catalog_id: catalogId })}
              onRecolor={(hex) => onEdit(room.id, { action: "recolor", item_id: item.id, color: hex })}
              tintColor={
                item.material_overrides?.primary
                  ? materialsById.get(item.material_overrides.primary)?.base_color ?? null
                  : null
              }
              catalogByCategory={catalogByCategory}
              busy={busy}
            />
          ))}
        </div>
      )}

      {roomItems.length > 0 && (
        <a
          href={resolveCatalogAssetUrl("/CATALOG_LICENSES.md")}
          target="_blank"
          rel="noreferrer"
          className="text-[10px] text-muted-foreground/60 underline decoration-dotted underline-offset-2 hover:text-muted-foreground"
        >
          Furniture &amp; material credits (all CC0)
        </a>
      )}
    </div>
  );
}
