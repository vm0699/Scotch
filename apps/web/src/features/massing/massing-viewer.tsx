/**
 * Stage 8.2–8.6 / 17.3 — 3D Massing Viewer.
 *
 * React Three Fiber canvas rendered in the 3D tab. Dynamically imported
 * (ssr:false) in preview-panel.tsx because R3F uses browser-only WebGL APIs.
 *
 * 8.2  OrbitControls, soft lighting, neutral background, ground plane.
 * 8.3  Walls extruded from room boundaries, floor + roof slabs.
 * 8.4  meshStandardMaterial palette: wall, floor, roof, glass, ground.
 * 8.5  Derives entirely from `project` prop — parameter edits flow through
 *       workspace state so sync is automatic (no additional wiring needed).
 * 8.6  GLTFExporter wired behind exportGltf(); GLTF button in toolbar.
 * 17.3 Camera preset buttons from GET /projects/{id}/cameras.
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { RotateCcw, Box as BoxIcon, Camera, Sun } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ArchitectureProject, CameraSuggestion } from "@/features/project/types";
import { buildMassingData, type MaterialId } from "@/features/massing/massing-data";
import { getCameras } from "@/features/api/client";

// ── Stage 27.7 — solar utilities ─────────────────────────────────────────────

const _DEG = Math.PI / 180;
const _MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function _solarPos(hour: number, month: number, latDeg = 20) {
  const lat = latDeg * _DEG;
  const doy = (month - 1) * 30.4 + 15;
  const dec = 23.45 * Math.sin((2 * Math.PI / 365) * (doy - 81)) * _DEG;
  const H   = (hour - 12) * 15 * _DEG;
  const sinAlt = Math.sin(lat) * Math.sin(dec) + Math.cos(lat) * Math.cos(dec) * Math.cos(H);
  const altitude = Math.asin(Math.max(-0.1, Math.min(1, sinAlt)));
  if (altitude <= 0) return null;
  const cosAlt = Math.cos(altitude);
  const cosAzClamp = cosAlt > 1e-4
    ? Math.max(-1, Math.min(1, (Math.sin(dec) - Math.sin(lat) * sinAlt) / (Math.cos(lat) * cosAlt)))
    : 0;
  const azFromSouth = hour < 12 ? -Math.acos(cosAzClamp) : Math.acos(cosAzClamp);
  return { altitude, azFromSouth };
}

function _fmtHour(h: number): string {
  const hh   = Math.floor(h);
  const mm   = Math.round((h - hh) * 60);
  const ampm = hh < 12 ? "AM" : "PM";
  const h12  = hh === 0 ? 12 : hh > 12 ? hh - 12 : hh;
  return `${h12}:${mm.toString().padStart(2, "0")} ${ampm}`;
}

// ── Sun light (directional, positional, shadow-capable) ───────────────────────

function SunLight({
  sunHour, sunMonth, enableShadows, centerX, centerZ,
}: {
  sunHour: number; sunMonth: number; enableShadows: boolean;
  centerX: number; centerZ: number;
}) {
  const sol = _solarPos(sunHour, sunMonth);
  if (!sol) return null; // below horizon
  const D = 120;
  const lx = centerX + Math.sin(sol.azFromSouth) * Math.cos(sol.altitude) * D;
  const ly = Math.max(5, Math.sin(sol.altitude) * D);
  const lz = centerZ - Math.cos(sol.azFromSouth) * Math.cos(sol.altitude) * D;
  return (
    <directionalLight
      position={[lx, ly, lz]}
      intensity={0.95}
      castShadow={enableShadows}
      shadow-mapSize-width={1024}
      shadow-mapSize-height={1024}
      shadow-camera-near={1}
      shadow-camera-far={D * 3}
      shadow-camera-left={-D * 1.5}
      shadow-camera-right={D * 1.5}
      shadow-camera-top={D * 1.5}
      shadow-camera-bottom={-D * 1.5}
    />
  );
}

// ── Ground shadow receiver ─────────────────────────────────────────────────────

function GroundPlane({ centerX, centerZ, maxDim, enableShadows }: {
  centerX: number; centerZ: number; maxDim: number; enableShadows: boolean;
}) {
  if (!enableShadows) return null;
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[centerX, -0.02, centerZ]} receiveShadow>
      <planeGeometry args={[maxDim * 6, maxDim * 6]} />
      <shadowMaterial opacity={0.18} />
    </mesh>
  );
}

// ── Re-render trigger when sun params change (demand frameloop) ───────────────

function _Invalidator({ deps }: { deps: unknown[] }) {
  const { invalidate } = useThree();
  useEffect(() => { invalidate(); }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

// ── Stage 8.4 — material palette ─────────────────────────────────────────────

type MatDef = {
  color: string;
  opacity: number;
  metalness: number;
  roughness: number;
};

const MAT: Record<MaterialId, MatDef> = {
  wall:             { color: "#f8f7f5", opacity: 1,    metalness: 0,    roughness: 0.65 },
  floor:            { color: "#e8e3dc", opacity: 1,    metalness: 0,    roughness: 0.9  },
  roof:             { color: "#d4cec6", opacity: 1,    metalness: 0,    roughness: 0.8  },
  glass:            { color: "#a8cadf", opacity: 0.42, metalness: 0.15, roughness: 0.05 },
  ground:           { color: "#ede9e2", opacity: 1,    metalness: 0,    roughness: 1    },
  furniture:        { color: "#c4b89a", opacity: 1,    metalness: 0,    roughness: 0.75 },
  // Phase 35 — floor tile materials
  floor_tile_light: { color: "#f0ece4", opacity: 1,    metalness: 0,    roughness: 0.55 },
  floor_tile_dark:  { color: "#8c7e6c", opacity: 1,    metalness: 0,    roughness: 0.60 },
  floor_marble:     { color: "#f5f2ee", opacity: 1,    metalness: 0.04, roughness: 0.25 },
  // Phase 35 — architectural elements
  counter:          { color: "#a89880", opacity: 1,    metalness: 0.05, roughness: 0.55 },
  mep_block:        { color: "#b8ccd6", opacity: 0.88, metalness: 0.08, roughness: 0.45 },
  stair:            { color: "#d4cfc8", opacity: 1,    metalness: 0,    roughness: 0.75 },
};

// ── Scene internals ───────────────────────────────────────────────────────────

function MassingMesh({ project, enableShadows }: { project: ArchitectureProject; enableShadows: boolean }) {
  const data = useMemo(() => buildMassingData(project), [project]);

  const { camera } = useThree();
  useEffect(() => {
    const d = data.maxDim * 1.15;
    camera.position.set(
      data.centerX + d * 0.65,
      d * 0.55,
      data.centerZ + d * 0.85,
    );
    camera.lookAt(data.centerX, 0, data.centerZ);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      {data.boxes.map((box) => {
        const m = MAT[box.mat];
        const transparent = m.opacity < 1;
        return (
          <mesh
            key={box.id}
            name={box.name}
            position={box.pos}
            castShadow={enableShadows}
            receiveShadow={enableShadows}
          >
            <boxGeometry args={box.size} />
            <meshStandardMaterial
              color={m.color}
              opacity={m.opacity}
              transparent={transparent}
              metalness={m.metalness}
              roughness={m.roughness}
              depthWrite={!transparent}
            />
          </mesh>
        );
      })}
    </>
  );
}

/** Exposes `gl.domElement.toDataURL()` so the render tab can capture the canvas. */
function CanvasCapture({ onReady }: { onReady: (fn: () => string) => void }) {
  const { gl } = useThree();
  const glRef = useRef(gl);
  glRef.current = gl;
  useEffect(() => {
    onReady(() => glRef.current.domElement.toDataURL("image/png"));
  }, [onReady]);
  return null;
}

/** Wires scene reference for GLTF export (Stage 8.6). */
function SceneExporter({
  onReady,
}: {
  onReady: (exportFn: () => void) => void;
}) {
  const { scene } = useThree();
  useEffect(() => {
    onReady(async () => {
      try {
        const { GLTFExporter } = await import(
          "three/examples/jsm/exporters/GLTFExporter.js"
        );
        const exporter = new GLTFExporter();
        exporter.parse(
          scene,
          (gltf) => {
            const data =
              gltf instanceof ArrayBuffer ? gltf : JSON.stringify(gltf);
            const blob = new Blob(
              [data],
              { type: gltf instanceof ArrayBuffer ? "model/gltf-binary" : "model/gltf+json" },
            );
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = gltf instanceof ArrayBuffer ? "massing.glb" : "massing.gltf";
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
          },
          (err) => console.error("GLTF export error", err),
          { binary: false },
        );
      } catch (e) {
        console.error("GLTF export unavailable", e);
      }
    });
  }, [scene, onReady]);
  return null;
}

/** Jumps the camera to a CameraSuggestion position (Stage 17.3). */
function CameraController({ jumpTo }: { jumpTo: CameraSuggestion | null }) {
  const { camera, invalidate } = useThree();

  useEffect(() => {
    if (!jumpTo) return;
    const [px, py, pz] = jumpTo.position;
    const [tx, ty, tz] = jumpTo.target;
    camera.position.set(px, py, pz);
    camera.lookAt(tx, ty, tz);
    invalidate();
  }, [jumpTo, camera, invalidate]);

  return null;
}

// ── Public component ──────────────────────────────────────────────────────────

export function MassingViewer({
  project,
  projectId,
  onCaptureReady,
}: {
  project: ArchitectureProject;
  /** Optional: supply to enable camera preset loading from the API. */
  projectId?: string;
  /** Called with a fn that captures the WebGL canvas as a base64 PNG data URL. */
  onCaptureReady?: (fn: () => string) => void;
}) {
  const controlsRef = useRef<any>(null);
  const exportFnRef = useRef<(() => void) | null>(null);
  const [cameras, setCameras] = useState<CameraSuggestion[]>([]);
  const [activeCamera, setActiveCamera] = useState<CameraSuggestion | null>(null);
  const [showCamMenu, setShowCamMenu] = useState(false);
  // Stage 27.7 — sun / shadow state
  const [sunHour, setSunHour] = useState(10);
  const [sunMonth, setSunMonth] = useState(6);
  const [showShadows, setShowShadows] = useState(false);
  const [showSunPanel, setShowSunPanel] = useState(false);

  const data = useMemo(() => buildMassingData(project), [project]);

  // Fetch camera suggestions when projectId is available
  useEffect(() => {
    if (!projectId) return;
    const ctrl = new AbortController();
    getCameras(projectId, ctrl.signal)
      .then(setCameras)
      .catch(() => {});
    return () => ctrl.abort();
  }, [projectId]);

  const handleExportReady = useCallback((fn: () => void) => {
    exportFnRef.current = fn;
  }, []);

  const handleCaptureReady = useCallback(
    (fn: () => string) => {
      onCaptureReady?.(fn);
    },
    [onCaptureReady],
  );

  const resetCamera = useCallback(() => {
    setActiveCamera(null);
    controlsRef.current?.reset();
  }, []);

  const triggerGltf = useCallback(() => {
    exportFnRef.current?.();
  }, []);

  const jumpToCamera = useCallback((cam: CameraSuggestion) => {
    // Spread to create a new reference so useEffect inside CameraController fires
    setActiveCamera({ ...cam });
    setShowCamMenu(false);
  }, []);

  return (
    <div className="relative h-full w-full">
      <Canvas
        frameloop="demand"
        shadows
        gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
        camera={{ fov: 42, near: 0.1, far: 2000 }}
        style={{ background: "#f5f4f1" }}
      >
        {/* Ambient + fill lights (always on) */}
        <ambientLight intensity={showShadows ? 0.45 : 0.65} />
        <directionalLight
          position={[data.centerX - 15, 20, data.centerZ + 20]}
          intensity={showShadows ? 0.18 : 0.25}
        />
        {/* Sun light — Stage 27.7 (replaces original key light when sun panel active) */}
        {showSunPanel ? (
          <SunLight
            sunHour={sunHour}
            sunMonth={sunMonth}
            enableShadows={showShadows}
            centerX={data.centerX}
            centerZ={data.centerZ}
          />
        ) : (
          <directionalLight
            position={[data.centerX + 20, 30, data.centerZ - 10]}
            intensity={0.85}
          />
        )}
        {/* Ground plane shadow receiver */}
        <GroundPlane
          centerX={data.centerX}
          centerZ={data.centerZ}
          maxDim={data.maxDim}
          enableShadows={showShadows}
        />

        {/* Geometry — Stage 8.3 walls + slabs from massing-data */}
        <MassingMesh project={project} enableShadows={showShadows} />

        {/* Invalidate on sun param changes */}
        <_Invalidator deps={[sunHour, sunMonth, showShadows, showSunPanel]} />

        {/* OrbitControls — Stage 8.2 */}
        <OrbitControls
          ref={controlsRef}
          target={[data.centerX, 0, data.centerZ]}
          minDistance={data.maxDim * 0.4}
          maxDistance={data.maxDim * 4}
          maxPolarAngle={Math.PI / 2 - 0.02}
          enableDamping
          dampingFactor={0.07}
        />

        {/* GLTF exporter hook — Stage 8.6 */}
        <SceneExporter onReady={handleExportReady} />

        {/* Camera jump controller — Stage 17.3 */}
        <CameraController jumpTo={activeCamera} />

        {/* Canvas capture hook — Stage 23.2 */}
        {onCaptureReady && <CanvasCapture onReady={handleCaptureReady} />}
      </Canvas>

      {/* Stage 27.7 — Sun / shadow panel */}
      {showSunPanel && (
        <div className="absolute bottom-14 right-3 z-40 w-56 rounded-lg border border-border/70 bg-card/97 p-3 shadow-md backdrop-blur-sm">
          <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
            Sun Context — Lat 20°N (India)
          </div>
          <div className="space-y-3">
            <div>
              <div className="mb-0.5 flex justify-between text-[10px] text-muted-foreground">
                <span>Time of day</span>
                <span className="font-mono">{_fmtHour(sunHour)}</span>
              </div>
              <input
                type="range" min={4} max={20} step={0.25} value={sunHour}
                onChange={(e) => setSunHour(Number(e.target.value))}
                className="w-full accent-foreground"
              />
            </div>
            <div>
              <div className="mb-0.5 flex justify-between text-[10px] text-muted-foreground">
                <span>Month</span>
                <span className="font-mono">{_MONTHS[sunMonth - 1]}</span>
              </div>
              <input
                type="range" min={1} max={12} step={1} value={sunMonth}
                onChange={(e) => setSunMonth(Number(e.target.value))}
                className="w-full accent-foreground"
              />
            </div>
            <label className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox" checked={showShadows}
                onChange={(e) => setShowShadows(e.target.checked)}
                className="size-3 accent-foreground"
              />
              <span className="text-[10px] text-muted-foreground">Cast shadows</span>
            </label>
            {_solarPos(sunHour, sunMonth) === null && (
              <p className="text-[10px] text-muted-foreground/50 italic">Sun below horizon at this time.</p>
            )}
          </div>
        </div>
      )}

      {/* Overlay controls */}
      <div className="absolute bottom-3 right-3 flex items-center gap-1.5 rounded-lg border border-border/70 bg-card/90 p-0.5 shadow-[0_1px_3px_rgba(0,0,0,0.08)] backdrop-blur-sm">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={resetCamera}
              aria-label="Reset camera"
            >
              <RotateCcw className="size-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">Reset camera</TooltipContent>
        </Tooltip>

        {/* Stage 17.3 — Camera preset picker (appears when projectId is set) */}
        {cameras.length > 0 && (
          <>
            <div className="mx-0.5 h-4 w-px bg-border/60" />
            <div className="relative">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setShowCamMenu((v) => !v)}
                    aria-label="Camera presets"
                  >
                    <Camera className="size-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="top">Camera presets</TooltipContent>
              </Tooltip>

              {showCamMenu && (
                <div className="absolute bottom-8 right-0 z-50 min-w-[190px] rounded-md border border-border/70 bg-card shadow-md">
                  <div className="px-2.5 py-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60">
                    Render presets
                  </div>
                  {cameras.map((cam) => (
                    <button
                      key={cam.name}
                      onClick={() => jumpToCamera(cam)}
                      className="flex w-full flex-col px-2.5 py-1.5 text-left hover:bg-muted/60 transition-colors"
                    >
                      <span className="text-[11px] font-medium leading-tight capitalize">
                        {cam.name.replace(/_/g, " ")}
                      </span>
                      <span className="text-[10px] text-muted-foreground/70 leading-tight mt-px">
                        {cam.description}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </>
        )}

        <div className="mx-0.5 h-4 w-px bg-border/60" />

        {/* Stage 27.7 — Sun / shadow toggle */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => setShowSunPanel((v) => !v)}
              aria-label="Sun context"
              aria-pressed={showSunPanel}
              className={showSunPanel ? "bg-muted" : undefined}
            >
              <Sun className="size-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">Sun / shadow context</TooltipContent>
        </Tooltip>

        <div className="mx-0.5 h-4 w-px bg-border/60" />

        {/* Stage 8.6 — GLTF export */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={triggerGltf}
              aria-label="Export GLTF"
            >
              <BoxIcon className="size-3.5" />
            </Button>
          </TooltipTrigger>
          <TooltipContent side="top">Export GLTF / GLB (render-ready)</TooltipContent>
        </Tooltip>
      </div>
    </div>
  );
}
