// Downloads Kenney's "Furniture Kit" (CC0, https://kenney.nl/assets/furniture-kit)
// once, caches the zip, and extracts specific named GLBs into raw/{id}/ in the
// exact shape normalize.mjs already expects from the Poly Haven downloader —
// so the SAME normalize.mjs run processes both sources identically.
//
// Why a second source: Poly Haven has no toilet/sink/bathtub models at all
// (checked directly via their API before reaching for this) — Kenney's kit
// does, under the same CC0 terms.
import { mkdir, writeFile, readFile, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { NodeIO, getBounds } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RAW_DIR = path.join(__dirname, "raw");
const CACHE_DIR = path.join(__dirname, "raw-kenney-source");
const ZIP_URL =
  "https://kenney.nl/media/pages/assets/furniture-kit/440e0608a4-1677580847/kenney_furniture-kit.zip";
const ZIP_PATH = path.join(CACHE_DIR, "kenney_furniture-kit.zip");

// catalog id -> { glb: path inside the zip, thumb: isometric PNG inside the zip }
const KENNEY_ITEMS = {
  toilet_standard: {
    glb: "Models/GLTF format/toilet.glb",
    thumb: "Isometric/toilet_SE.png",
    label: "Toilet",
  },
  bathroom_sink: {
    glb: "Models/GLTF format/bathroomSink.glb",
    thumb: "Isometric/bathroomSink_SE.png",
    label: "Bathroom Sink",
  },
  bathtub_standard: {
    glb: "Models/GLTF format/bathtub.glb",
    thumb: "Isometric/bathtub_SE.png",
    label: "Bathtub",
  },
  kitchen_sink_unit: {
    glb: "Models/GLTF format/kitchenSink.glb",
    thumb: "Isometric/kitchenSink_SE.png",
    label: "Kitchen Sink Unit",
  },
};

async function ensureZip() {
  if (existsSync(ZIP_PATH)) return;
  await mkdir(CACHE_DIR, { recursive: true });
  console.log("[kenney] downloading kenney_furniture-kit.zip ...");
  await execFileAsync("curl", ["-sSL", "--max-time", "60", "-o", ZIP_PATH, ZIP_URL]);
}

async function main() {
  await ensureZip();

  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS);

  for (const [id, spec] of Object.entries(KENNEY_ITEMS)) {
    const itemDir = path.join(RAW_DIR, id);
    await mkdir(itemDir, { recursive: true });

    const glbDest = path.join(itemDir, `${id}.glb`);
    const thumbDest = path.join(itemDir, "thumbnail_source.png");
    if (!existsSync(glbDest)) {
      await execFileAsync("unzip", ["-o", "-j", ZIP_PATH, spec.glb, "-d", itemDir]);
      const extracted = path.join(itemDir, path.basename(spec.glb));
      const { rename } = await import("node:fs/promises");
      await rename(extracted, glbDest);
    }
    if (!existsSync(thumbDest)) {
      await execFileAsync("unzip", ["-o", "-j", ZIP_PATH, spec.thumb, "-d", itemDir]);
      const extractedThumb = path.join(itemDir, path.basename(spec.thumb));
      const { rename } = await import("node:fs/promises");
      await rename(extractedThumb, thumbDest);
    }

    // Kenney's site doesn't publish per-model dimensions the way Poly Haven's
    // API does — measure the actual mesh bounds ourselves (meters, Y-up:
    // [width, height, depth]) and record them in the same provenance.json
    // shape normalize.mjs already reads for Poly Haven items.
    const doc = await io.read(glbDest);
    const scene = doc.getRoot().listScenes()[0];
    const bounds = getBounds(scene);
    const widthM = bounds.max[0] - bounds.min[0];
    const heightM = bounds.max[1] - bounds.min[1];
    const depthM = bounds.max[2] - bounds.min[2];

    await writeFile(
      path.join(itemDir, "provenance.json"),
      JSON.stringify(
        {
          catalog_id: id,
          source: "Kenney (Furniture Kit)",
          slug: id,
          url: "https://kenney.nl/assets/furniture-kit",
          name: spec.label,
          authors: { Kenney: "All" },
          spdx: "CC0-1.0",
          license_url: "http://creativecommons.org/publicdomain/zero/1.0/",
          dimensions_mm: [widthM * 1000, depthM * 1000, heightM * 1000],
        },
        null,
        2,
      ),
    );

    console.log(`[kenney] ok: ${id}`);
  }

  console.log("\nAll Kenney assets extracted.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
