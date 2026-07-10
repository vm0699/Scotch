"use client";

/**
 * Phase 39 — Reference / scan-to-plan overlay panel.
 *
 * Renders an uploaded reference image semi-transparently over the 2D floor-plan
 * canvas. Supports:
 *   - Upload (image or PDF)
 *   - Opacity slider
 *   - Lock/unlock toggle
 *   - Calibration mode: mark two points on the image, enter known distance
 *   - Delete
 */

import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Lock,
  LockOpen,
  Minus,
  Plus,
  Ruler,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  calibrateReference,
  deleteReference,
  getReferenceFileUrl,
  listReferences,
  uploadReference,
} from "@/features/api/client";
import type { ReferenceAsset } from "@/features/project/types";

interface Props {
  projectId: string;
  /** Pixel size of the 2D canvas so the overlay can fill it exactly */
  canvasWidth: number;
  canvasHeight: number;
}

interface CalibPoint {
  x: number; // percentage 0–100 of image width
  y: number; // percentage 0–100 of image height
}

export function ReferenceOverlay({ projectId, canvasWidth, canvasHeight }: Props) {
  const [assets, setAssets] = useState<ReferenceAsset[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [opacity, setOpacity] = useState(0.4);
  const [locked, setLocked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Calibration state
  const [calibMode, setCalibMode] = useState(false);
  const [calibPoints, setCalibPoints] = useState<CalibPoint[]>([]);
  const [knownDist, setKnownDist] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  const activeAsset = assets.find((a) => a.id === activeId) ?? null;

  // ── Load references ─────────────────────────────────────────────────────────

  const reload = useCallback(async () => {
    if (!projectId) return;
    try {
      const list = await listReferences(projectId);
      setAssets(list);
      if (list.length > 0 && !activeId) setActiveId(list[0].id);
    } catch {
      // backend may not be running; fail silently
    }
  }, [projectId, activeId]);

  useEffect(() => {
    reload();
  }, [reload]);

  // ── Upload ──────────────────────────────────────────────────────────────────

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const asset = await uploadReference(projectId, file);
      setAssets((prev) => [asset, ...prev]);
      setActiveId(asset.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // ── Delete ──────────────────────────────────────────────────────────────────

  async function handleDelete(id: string) {
    try {
      await deleteReference(projectId, id);
      setAssets((prev) => prev.filter((a) => a.id !== id));
      if (activeId === id) setActiveId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  // ── Calibration ─────────────────────────────────────────────────────────────

  function handleOverlayClick(e: React.MouseEvent<HTMLDivElement>) {
    if (!calibMode || !overlayRef.current) return;
    const rect = overlayRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setCalibPoints((prev) => {
      if (prev.length >= 2) return [{ x, y }];
      return [...prev, { x, y }];
    });
  }

  async function applyCalibration() {
    if (!activeId || calibPoints.length < 2 || !knownDist) return;
    const dist = parseFloat(knownDist);
    if (isNaN(dist) || dist <= 0) {
      setError("Enter a valid distance in feet");
      return;
    }
    // Convert percentage points to approximate pixel coords on the overlay
    const p1 = { px: (calibPoints[0].x / 100) * canvasWidth, py: (calibPoints[0].y / 100) * canvasHeight };
    const p2 = { px: (calibPoints[1].x / 100) * canvasWidth, py: (calibPoints[1].y / 100) * canvasHeight };
    setLoading(true);
    setError(null);
    try {
      const updated = await calibrateReference(projectId, activeId, {
        p1_x: p1.px, p1_y: p1.py,
        p2_x: p2.px, p2_y: p2.py,
        known_distance_ft: dist,
      });
      setAssets((prev) => prev.map((a) => (a.id === updated.id ? updated : a)));
      setCalibMode(false);
      setCalibPoints([]);
      setKnownDist("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Calibration failed");
    } finally {
      setLoading(false);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  if (assets.length === 0 && !loading) {
    return (
      <div className="absolute inset-0 pointer-events-none">
        {/* Upload trigger — only the button is interactive */}
        <div className="absolute bottom-3 left-3 pointer-events-auto">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp,application/pdf"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button
            size="sm"
            variant="outline"
            className="gap-1.5 text-xs bg-white/90 backdrop-blur-sm shadow-sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Upload className="h-3 w-3" />
            Add Reference
          </Button>
          {error && (
            <p className="mt-1 text-xs text-destructive">{error}</p>
          )}
        </div>
      </div>
    );
  }

  const fileUrl = activeId ? getReferenceFileUrl(projectId, activeId) : null;

  return (
    <div className="absolute inset-0 pointer-events-none">
      {/* ── Overlay image ── */}
      {fileUrl && !locked && (
        <div
          ref={overlayRef}
          className="absolute inset-0 pointer-events-auto"
          style={{ cursor: calibMode ? "crosshair" : "default" }}
          onClick={handleOverlayClick}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={fileUrl}
            alt={activeAsset?.file_name ?? "reference"}
            className="absolute inset-0 w-full h-full object-contain select-none"
            style={{ opacity, mixBlendMode: "multiply" }}
            draggable={false}
          />
          {/* Calibration point markers */}
          {calibPoints.map((pt, i) => (
            <div
              key={i}
              className="absolute w-3 h-3 rounded-full border-2 border-blue-500 bg-white/80 -translate-x-1/2 -translate-y-1/2 pointer-events-none"
              style={{ left: `${pt.x}%`, top: `${pt.y}%` }}
            />
          ))}
          {calibPoints.length === 2 && (
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              style={{ overflow: "visible" }}
            >
              <line
                x1={`${calibPoints[0].x}%`} y1={`${calibPoints[0].y}%`}
                x2={`${calibPoints[1].x}%`} y2={`${calibPoints[1].y}%`}
                stroke="#3b82f6" strokeWidth={1.5} strokeDasharray="4 2"
              />
            </svg>
          )}
        </div>
      )}

      {/* ── Control bar ── */}
      <div className="absolute bottom-3 left-3 pointer-events-auto flex flex-col gap-1.5">
        {/* Main toolbar */}
        <div className="flex items-center gap-1.5 rounded-lg border border-border bg-white/95 backdrop-blur-sm shadow-sm px-2 py-1.5">
          {/* Asset selector */}
          {assets.length > 1 && (
            <select
              className="text-xs border-0 bg-transparent outline-none cursor-pointer max-w-[100px] truncate"
              value={activeId ?? ""}
              onChange={(e) => setActiveId(e.target.value)}
            >
              {assets.map((a) => (
                <option key={a.id} value={a.id}>{a.file_name}</option>
              ))}
            </select>
          )}
          {assets.length === 1 && (
            <span className="text-xs text-muted-foreground max-w-[80px] truncate">
              {activeAsset?.file_name}
            </span>
          )}

          <div className="w-px h-4 bg-border mx-0.5" />

          {/* Opacity */}
          <Minus className="h-3 w-3 text-muted-foreground cursor-pointer" onClick={() => setOpacity((o) => Math.max(0.05, o - 0.1))} />
          <input
            type="range" min={0.05} max={1} step={0.05}
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="w-16 accent-primary"
            title={`Opacity: ${Math.round(opacity * 100)}%`}
          />
          <Plus className="h-3 w-3 text-muted-foreground cursor-pointer" onClick={() => setOpacity((o) => Math.min(1, o + 0.1))} />

          <div className="w-px h-4 bg-border mx-0.5" />

          {/* Lock */}
          <button
            className="rounded p-0.5 hover:bg-muted transition-colors"
            onClick={() => setLocked((l) => !l)}
            title={locked ? "Unlock overlay" : "Lock (hide) overlay"}
          >
            {locked ? <Lock className="h-3.5 w-3.5 text-muted-foreground" /> : <LockOpen className="h-3.5 w-3.5 text-foreground" />}
          </button>

          {/* Calibrate */}
          <button
            className={`rounded p-0.5 hover:bg-muted transition-colors ${calibMode ? "bg-blue-50 text-blue-600" : ""}`}
            onClick={() => { setCalibMode((m) => !m); setCalibPoints([]); }}
            title="Calibrate scale"
          >
            <Ruler className="h-3.5 w-3.5" />
          </button>

          {/* Delete */}
          {activeId && (
            <button
              className="rounded p-0.5 hover:bg-red-50 hover:text-red-600 transition-colors"
              onClick={() => handleDelete(activeId)}
              title="Remove reference"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}

          <div className="w-px h-4 bg-border mx-0.5" />

          {/* Upload new */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/gif,image/webp,application/pdf"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            className="rounded p-0.5 hover:bg-muted transition-colors"
            onClick={() => fileInputRef.current?.click()}
            title="Upload another reference"
          >
            <Upload className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Calibration sub-toolbar */}
        {calibMode && (
          <div className="flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50/95 backdrop-blur-sm shadow-sm px-2 py-1.5 text-xs">
            {calibPoints.length < 2 ? (
              <span className="text-blue-700">
                Click point {calibPoints.length + 1} of 2 on the overlay
              </span>
            ) : (
              <>
                <input
                  type="number"
                  min={0.1}
                  step={0.5}
                  placeholder="Dist (ft)"
                  value={knownDist}
                  onChange={(e) => setKnownDist(e.target.value)}
                  className="w-20 border border-blue-300 rounded px-1 py-0.5 text-xs bg-white"
                />
                <Button size="sm" className="h-6 text-xs px-2" onClick={applyCalibration} disabled={loading}>
                  Set scale
                </Button>
                <button onClick={() => { setCalibPoints([]); }} className="ml-0.5 hover:text-blue-800">
                  <X className="h-3 w-3" />
                </button>
              </>
            )}
            {activeAsset?.calibration && (
              <span className="ml-1 text-blue-600">
                {activeAsset.calibration.pixels_per_foot.toFixed(1)} px/ft
              </span>
            )}
          </div>
        )}

        {/* Scale badge */}
        {activeAsset?.scale_status === "calibrated" && !calibMode && (
          <div className="rounded border border-green-200 bg-green-50/90 px-2 py-0.5 text-xs text-green-700">
            Calibrated · {activeAsset.calibration!.pixels_per_foot.toFixed(1)} px/ft
          </div>
        )}

        {error && (
          <p className="text-xs text-destructive bg-white/90 rounded px-1.5 py-0.5 border border-destructive/30">
            {error}
          </p>
        )}
      </div>
    </div>
  );
}
