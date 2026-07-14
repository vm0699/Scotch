/**
 * Stage 43.2 — Interior environment manifest (HDRI + PBR floor/wall materials).
 *
 * env-materials.json is a static file vendored alongside the furniture catalog
 * (built by tools/catalog-pipeline/download-env.mjs, served by the same
 * /catalog-assets StaticFiles mount) — fetched directly, no backend route.
 */

import { API_BASE_URL } from "@/features/api/client";

export interface EnvMaterialEntry {
  key: string;
  label: string;
  /** World-space tile size in feet — used to compute per-box UV repeat. */
  repeat_ft: number;
  color_url: string | null;
  normal_url: string | null;
  roughness_url: string | null;
  license: { source: string; asset_id: string; spdx: string; source_url: string };
}

export interface EnvManifest {
  version: number;
  generated_at: string;
  hdri: {
    key: string;
    label: string;
    url: string;
    license: { source: string; spdx: string; source_url: string };
  };
  materials: EnvMaterialEntry[];
}

const MANIFEST_URL = "/catalog-assets/env-materials.json";

let _manifestPromise: Promise<EnvManifest | null> | null = null;

/** Fetches once per session; resolves to null (not throws) if unavailable so the
 *  viewer can fall back to flat colors instead of breaking the whole scene. */
export function loadEnvManifest(): Promise<EnvManifest | null> {
  if (!_manifestPromise) {
    _manifestPromise = fetch(`${API_BASE_URL}${MANIFEST_URL}`, { cache: "force-cache" })
      .then((res) => (res.ok ? (res.json() as Promise<EnvManifest>) : null))
      .catch(() => null);
  }
  return _manifestPromise;
}

export function resolveAssetUrl(relativeUrl: string): string {
  return `${API_BASE_URL}${relativeUrl}`;
}
