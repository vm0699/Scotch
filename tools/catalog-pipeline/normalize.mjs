// Normalizes each raw downloaded asset into a shippable GLB:
//   - recenters X/Z to the bounding-box center, shifts Y so the object's
//     lowest point sits exactly at floor level (y=0) — so R3F can place it
//     at [roomX, roomBaseY, roomZ] with no per-item fudge factors.
//   - welds duplicate vertices and prunes unused data to shrink the file.
//   - Meshopt-compresses geometry (EXT_meshopt_compression) — three.js's
//     GLTFLoader decodes it transparently, and drei's useGLTF() already
//     wires a MeshoptDecoder by default, so no runtime code changes needed.
//   - Re-encodes baked textures as WebP (EXT_texture_webp) — natively
//     supported by three.js's GLTFLoader with no plugin, so this needs no
//     runtime code changes either.
//   - writes services/api/app/assets/catalog/models/{id}.glb + a vendored
//     thumbnail + catalog.json (the manifest the backend CatalogItem API reads).
import { mkdir, writeFile, readFile, copyFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { NodeIO, getBounds } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { weld, dedup, prune, meshopt, textureCompress } from "@gltf-transform/functions";
import { MeshoptEncoder } from "meshoptimizer";
import sharp from "sharp";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RAW_DIR = path.join(__dirname, "raw");
const OUT_ROOT = path.join(__dirname, "..", "..", "services", "api", "app", "assets", "catalog");
const OUT_MODELS = path.join(OUT_ROOT, "models");
const OUT_THUMBS = path.join(OUT_ROOT, "thumbnails");

const MM_TO_FT = 1 / 304.8;

function findGltf(itemDir, fsEntries) {
  // Poly Haven items ship as .gltf (+ separate .bin/textures); Kenney items
  // ship as a single packed .glb — gltf-transform's NodeIO reads either.
  const gltf = fsEntries.find((f) => f.endsWith(".gltf") || f.endsWith(".glb"));
  if (!gltf) throw new Error(`no .gltf/.glb in ${itemDir}`);
  return path.join(itemDir, gltf);
}

async function normalizeOne(item, io) {
  const itemDir = path.join(RAW_DIR, item.id);
  const { readdir } = await import("node:fs/promises");
  const entries = await readdir(itemDir);
  const gltfPath = findGltf(itemDir, entries);

  const doc = await io.read(gltfPath);

  // Clean up geometry before measuring bounds.
  await doc.transform(weld(), dedup(), prune());

  const scene = doc.getRoot().listScenes()[0];
  const bounds = getBounds(scene);
  const [minX, minY, minZ] = bounds.min;
  const [maxX, maxY, maxZ] = bounds.max;

  const offset = [-(minX + maxX) / 2, -minY, -(minZ + maxZ) / 2];

  for (const node of scene.listChildren()) {
    const [tx, ty, tz] = node.getTranslation();
    node.setTranslation([tx + offset[0], ty + offset[1], tz + offset[2]]);
  }

  // Re-measure to report the final footprint actually shipped (sanity check
  // against the Poly Haven metadata dimensions used in catalog.json).
  const finalBounds = getBounds(scene);
  const shippedSize = {
    w_ft: (finalBounds.max[0] - finalBounds.min[0]) * (1 / 0.3048),
    d_ft: (finalBounds.max[2] - finalBounds.min[2]) * (1 / 0.3048),
    h_ft: (finalBounds.max[1] - finalBounds.min[1]) * (1 / 0.3048),
  };

  // Compress last, after bounds/measurement/repositioning above (which need
  // exact, unquantized positions). Textures first (independent of geometry),
  // then Meshopt geometry compression.
  await doc.transform(
    textureCompress({ encoder: sharp, targetFormat: "webp", quality: 82 }),
    meshopt({ encoder: MeshoptEncoder, level: "high" }),
  );

  await mkdir(OUT_MODELS, { recursive: true });
  const outPath = path.join(OUT_MODELS, `${item.id}.glb`);
  await io.write(outPath, doc);

  await mkdir(OUT_THUMBS, { recursive: true });
  await copyFile(path.join(itemDir, "thumbnail_source.png"), path.join(OUT_THUMBS, `${item.id}.png`));

  const provenance = JSON.parse(await readFile(path.join(itemDir, "provenance.json"), "utf-8"));
  const { size: compressedBytes } = await stat(outPath);

  return { shippedSize, provenance, compressedBytes };
}

async function main() {
  const sources = JSON.parse(await readFile(path.join(__dirname, "sources.json"), "utf-8"));
  await MeshoptEncoder.ready;
  const io = new NodeIO()
    .registerExtensions(ALL_EXTENSIONS)
    .registerDependencies({ "meshopt.encoder": MeshoptEncoder });

  const catalogItems = [];
  const licenseEntries = [];
  let totalCompressedBytes = 0;

  for (const item of sources.items) {
    console.log(`[normalize] ${item.id}`);
    const { shippedSize, provenance, compressedBytes } = await normalizeOne(item, io);
    totalCompressedBytes += compressedBytes;

    // Poly Haven metadata dimension order is [width_mm, depth_mm, height_mm].
    const [wmm, dmm, hmm] = provenance.dimensions_mm;

    catalogItems.push({
      id: item.id,
      slug: item.slug,
      label: item.label,
      category: item.category,
      style_tags: item.style_tags,
      footprint_w: Number((wmm * MM_TO_FT).toFixed(2)),
      footprint_d: Number((dmm * MM_TO_FT).toFixed(2)),
      height: Number((hmm * MM_TO_FT).toFixed(2)),
      mesh_url: `/catalog-assets/models/${item.id}.glb`,
      thumbnail_url: `/catalog-assets/thumbnails/${item.id}.png`,
      symbol_id: item.symbol_id,
      snap: item.snap,
      material_slots: item.material_slots,
      license: {
        source: provenance.source,
        spdx: provenance.spdx,
        source_url: provenance.url,
        attribution: null,
      },
    });

    licenseEntries.push({
      catalog_id: item.id,
      name: provenance.name,
      author: Object.keys(provenance.authors ?? {}).join(", ") || "Poly Haven",
      source_url: provenance.url,
      spdx: provenance.spdx,
      shipped_footprint_ft: shippedSize,
    });
  }

  const manifest = {
    version: 1,
    room_type: sources.room_type,
    generated_at: new Date().toISOString(),
    items: catalogItems,
  };

  await writeFile(path.join(OUT_ROOT, "catalog.json"), JSON.stringify(manifest, null, 2));

  const licenseLines = [
    "# Catalog Asset Licenses",
    "",
    "All furniture meshes in `services/api/app/assets/catalog/` are sourced from",
    "[Poly Haven](https://polyhaven.com/), licensed **CC0 1.0** (public domain —",
    "no attribution legally required; author credited below as courtesy).",
    "See https://polyhaven.com/license for the full license text.",
    "",
    "Assets were normalized (recentered, floor-aligned, welded/deduped) by",
    "`tools/catalog-pipeline/normalize.mjs` — geometry and textures are otherwise unmodified.",
    "",
    "| Catalog ID | Name | Author | Source | License |",
    "|---|---|---|---|---|",
    ...licenseEntries.map(
      (e) => `| \`${e.catalog_id}\` | ${e.name} | ${e.author} | [Poly Haven](${e.source_url}) | ${e.spdx} |`,
    ),
    "",
  ].join("\n");

  await writeFile(path.join(OUT_ROOT, "CATALOG_LICENSES.md"), licenseLines);

  console.log(`\nWrote ${catalogItems.length} items to ${path.join(OUT_ROOT, "catalog.json")}`);
  console.log(`Wrote ${path.join(OUT_ROOT, "CATALOG_LICENSES.md")}`);
  console.log(
    `WebP+Meshopt-compressed model payload: ${(totalCompressedBytes / 1024).toFixed(1)} KB across ${catalogItems.length} GLBs`,
  );
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
