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
import { RotateCcw, Box as BoxIcon, Camera } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { ArchitectureProject, CameraSuggestion } from "@/features/project/types";
import { buildMassingData, type MaterialId } from "@/features/massing/massing-data";
import { getCameras } from "@/features/api/client";

// ── Stage 8.4 — material palette ─────────────────────────────────────────────

type MatDef = {
  color: string;
  opacity: number;
  metalness: number;
  roughness: number;
};

const MAT: Record<MaterialId, MatDef> = {
  wall:   { color: "#f8f7f5", opacity: 1,    metalness: 0,    roughness: 0.65 },
  floor:  { color: "#e8e3dc", opacity: 1,    metalness: 0,    roughness: 0.9  },
  roof:   { color: "#d4cec6", opacity: 1,    metalness: 0,    roughness: 0.8  },
  glass:  { color: "#a8cadf", opacity: 0.42, metalness: 0.15, roughness: 0.05 },
  ground: { color: "#ede9e2", opacity: 1,    metalness: 0,    roughness: 1    },
};

// ── Scene internals ───────────────────────────────────────────────────────────

function MassingMesh({ project }: { project: ArchitectureProject }) {
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
          <mesh key={box.id} name={box.name} position={box.pos}>
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
}: {
  project: ArchitectureProject;
  /** Optional: supply to enable camera preset loading from the API. */
  projectId?: string;
}) {
  const controlsRef = useRef<any>(null);
  const exportFnRef = useRef<(() => void) | null>(null);
  const [cameras, setCameras] = useState<CameraSuggestion[]>([]);
  const [activeCamera, setActiveCamera] = useState<CameraSuggestion | null>(null);
  const [showCamMenu, setShowCamMenu] = useState(false);

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
        gl={{ antialias: true, alpha: false }}
        camera={{ fov: 42, near: 0.1, far: 2000 }}
        style={{ background: "#f5f4f1" }}
      >
        {/* Lighting */}
        <ambientLight intensity={0.65} />
        <directionalLight
          position={[data.centerX + 20, 30, data.centerZ - 10]}
          intensity={0.85}
          castShadow={false}
        />
        <directionalLight
          position={[data.centerX - 15, 20, data.centerZ + 20]}
          intensity={0.25}
        />

        {/* Geometry — Stage 8.3 walls + slabs from massing-data */}
        <MassingMesh project={project} />

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
      </Canvas>

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
