/**
 * Stage 43.2 — Real GLB furniture meshes for FurnitureItem.catalog_id.
 *
 * Items WITHOUT catalog_id keep rendering as the existing plain box (see
 * massing-data.ts / MassingMesh) — this layer only covers catalog-backed items,
 * so the box fallback stays exactly as graceful/progressive as before.
 *
 * Placement math:
 *   - Vendored GLBs are pre-normalized (tools/catalog-pipeline/normalize.mjs):
 *     X/Z centered on the object, Y=0 at the object's floor contact point.
 *   - We measure the ACTUAL loaded mesh bounding box at runtime (not just the
 *     catalog's footprint metadata) and scale to match footprint_w/footprint_d/
 *     height exactly — this is what keeps floor contact and centering exact
 *     even if a mesh's authored bounds differ slightly from its metadata.
 *   - World position = the FurnitureItem's placed footprint center; rotation.y
 *     mirrors item.rotation so the AABB swap for east/west-wall items (which
 *     the deterministic placer already bakes into width/depth) renders as an
 *     actual 90°/270° turn instead of a distorted non-uniform scale.
 */

"use client";

import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { useGLTF } from "@react-three/drei";

import type { ArchitectureProject, CatalogItem, FurnitureItem } from "@/features/project/types";
import { getCatalog, resolveCatalogAssetUrl } from "@/features/api/client";

const FT_TO_M = 0.3048;

let _catalogPromise: Promise<CatalogItem[]> | null = null;

/** Fetches the furniture catalog once per session (module-level cache). */
function useCatalogItems(): CatalogItem[] {
  const [items, setItems] = useState<CatalogItem[]>([]);
  useEffect(() => {
    if (!_catalogPromise) _catalogPromise = getCatalog();
    let cancelled = false;
    _catalogPromise.then((data) => {
      if (!cancelled) setItems(data);
    }).catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  return items;
}

function CatalogMesh({
  furnitureItem,
  catalogItem,
  baseY,
  enableShadows,
  tintColor,
}: {
  furnitureItem: FurnitureItem;
  catalogItem: CatalogItem;
  baseY: number;
  enableShadows: boolean;
  /** Stage 43.16 — hex color from material_overrides, resolved against
   *  project.materials. meshStandardMaterial.color multiplies the diffuse
   *  map by default, so this "recolor" is a tint over the baked texture, not
   *  a per-region texture swap — the whole item tints uniformly. */
  tintColor?: string | null;
}) {
  const url = resolveCatalogAssetUrl(catalogItem.mesh_url);
  const { scene } = useGLTF(url);

  const prepared = useMemo(() => {
    const clone = scene.clone(true);
    const box = new THREE.Box3().setFromObject(clone);
    const size = new THREE.Vector3();
    box.getSize(size);
    clone.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.isMesh) {
        mesh.castShadow = enableShadows;
        mesh.receiveShadow = enableShadows;
        // Poly Haven's baked diffuse/normal/ARM textures read correctly with
        // sRGB color on the albedo map and a properly weighted HDRI response —
        // without this every catalog piece looks washed out against the room.
        // Clone each material too — otherwise a tint on one placed instance
        // would repaint every other instance sharing the same cached GLTF.
        mesh.material = Array.isArray(mesh.material) ? mesh.material.map((m) => m.clone()) : mesh.material.clone();
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        for (const mat of materials) {
          const std = mat as THREE.MeshStandardMaterial;
          if (std.map) std.map.colorSpace = THREE.SRGBColorSpace;
          std.envMapIntensity = 1.15;
          if (tintColor) std.color.set(tintColor);
          std.needsUpdate = true;
        }
      }
    });
    return { clone, size };
  }, [scene, enableShadows, tintColor]);

  const targetW = catalogItem.footprint_w * FT_TO_M;
  const targetD = catalogItem.footprint_d * FT_TO_M;
  const targetH = catalogItem.height * FT_TO_M;
  const scale: [number, number, number] = [
    prepared.size.x > 1e-6 ? targetW / prepared.size.x : 1,
    prepared.size.y > 1e-6 ? targetH / prepared.size.y : 1,
    prepared.size.z > 1e-6 ? targetD / prepared.size.z : 1,
  ];

  const centerX = furnitureItem.x + furnitureItem.width / 2;
  const centerZ = furnitureItem.y + furnitureItem.depth / 2;
  const posY = baseY + (furnitureItem.z ?? 0);
  const rotY = (furnitureItem.rotation * Math.PI) / 180;

  return (
    <group
      name={`Scotch_Furniture_${catalogItem.id}_${furnitureItem.id.slice(0, 6)}`}
      position={[centerX, posY, centerZ]}
      rotation={[0, rotY, 0]}
    >
      <primitive object={prepared.clone} scale={scale} />
    </group>
  );
}

/** Renders every FurnitureItem with a resolved catalog_id as a real mesh. */
export function CatalogFurnitureLayer({
  project,
  enableShadows,
}: {
  project: ArchitectureProject;
  enableShadows: boolean;
}) {
  const catalogItems = useCatalogItems();
  const catalogMap = useMemo(() => new Map(catalogItems.map((c) => [c.id, c])), [catalogItems]);
  const h = project.building.floor_height;

  if (!project.show_furniture || catalogMap.size === 0) return null;

  const placed = project.furniture.filter((f) => f.catalog_id && catalogMap.has(f.catalog_id));
  if (placed.length === 0) return null;

  const materialsById = new Map(project.materials.map((m) => [m.id, m]));

  return (
    <>
      {placed.map((item) => {
        const room = project.rooms.find((r) => r.id === item.room_id);
        const baseY = room ? room.level * h : 0;
        const catalogItem = catalogMap.get(item.catalog_id!)!;
        const tintMaterialId = item.material_overrides?.primary;
        const tintColor = tintMaterialId ? materialsById.get(tintMaterialId)?.base_color ?? null : null;
        return (
          <CatalogMesh
            key={item.id}
            furnitureItem={item}
            catalogItem={catalogItem}
            baseY={baseY}
            enableShadows={enableShadows}
            tintColor={tintColor}
          />
        );
      })}
    </>
  );
}
