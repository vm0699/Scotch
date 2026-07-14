// Downloads raw glTF + textures for each curated item from Poly Haven's public API
// (CC0, no auth required — https://api.polyhaven.com). Run once per new item added
// to sources.json; safe to re-run (skips files already on disk).
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RAW_DIR = path.join(__dirname, "raw");
const RES = "1k";

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function downloadFile(url, destPath) {
  if (existsSync(destPath)) return;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  await mkdir(path.dirname(destPath), { recursive: true });
  await writeFile(destPath, buf);
}

async function main() {
  const sources = JSON.parse(await readFile(path.join(__dirname, "sources.json"), "utf-8"));

  for (const item of sources.items) {
    if (item.source && item.source !== "polyhaven") {
      console.log(`\n[download] ${item.id} — skipped (source: ${item.source}, handled by its own script)`);
      continue;
    }
    const { slug, id } = item;
    console.log(`\n[download] ${id} (Poly Haven: ${slug})`);

    const [info, files] = await Promise.all([
      fetchJson(`https://api.polyhaven.com/info/${slug}`),
      fetchJson(`https://api.polyhaven.com/files/${slug}`),
    ]);

    if (info.type !== 2) throw new Error(`${slug}: expected a model asset (type=2), got type=${info.type}`);

    const gltfEntry = files.gltf?.[RES];
    if (!gltfEntry) throw new Error(`${slug}: no gltf ${RES} files available`);

    const itemDir = path.join(RAW_DIR, id);
    await mkdir(itemDir, { recursive: true });

    // Main .gltf
    await downloadFile(gltfEntry.gltf.url, path.join(itemDir, path.basename(gltfEntry.gltf.url)));

    // Included buffers + textures
    for (const [relPath, entry] of Object.entries(gltfEntry.gltf.include ?? {})) {
      await downloadFile(entry.url, path.join(itemDir, relPath));
    }

    // Thumbnail (vendored, not hot-linked at runtime)
    await downloadFile(info.thumbnail_url, path.join(itemDir, "thumbnail_source.png"));

    // Record provenance for the license manifest
    await writeFile(
      path.join(itemDir, "provenance.json"),
      JSON.stringify(
        {
          catalog_id: id,
          source: "Poly Haven",
          slug,
          url: `https://polyhaven.com/a/${slug}`,
          name: info.name,
          authors: info.authors,
          spdx: "CC0-1.0",
          license_url: "https://polyhaven.com/license",
          dimensions_mm: info.dimensions,
        },
        null,
        2,
      ),
    );

    console.log(`  ok: ${id}`);
  }

  console.log("\nAll assets downloaded.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
