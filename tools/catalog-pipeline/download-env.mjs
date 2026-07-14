// Downloads the interior HDRI (Poly Haven, CC0) and PBR floor/wall material
// sets (ambientCG, CC0) used by the R3F room viewer. Vendors them under
// services/api/app/assets/catalog/{env,materials}/ and appends license
// entries to CATALOG_LICENSES.md. Re-run is safe (skips existing files).
import { mkdir, writeFile, readFile, readdir, rename, appendFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_ROOT = path.join(__dirname, "..", "..", "services", "api", "app", "assets", "catalog");
const RAW_DIR = path.join(__dirname, "raw-env");

// Node's native fetch (undici) reliably fails to connect to ambientcg.com on
// this host (IPv4/IPv6 resolution quirk) even though curl reaches it fine —
// shell out to curl for every request here instead of using fetch(). -L is
// required: ambientcg.com/get?file=... 302s to the actual CDN object.
async function downloadFile(url, destPath) {
  if (existsSync(destPath)) return;
  await mkdir(path.dirname(destPath), { recursive: true });
  await execFileAsync("curl", ["-sSL", "--max-time", "60", "-o", destPath, url]);
}

async function fetchJson(url) {
  const { stdout } = await execFileAsync("curl", ["-sSL", "--max-time", "30", url], {
    maxBuffer: 1024 * 1024 * 16,
  });
  return JSON.parse(stdout);
}

async function downloadHdri(cfg) {
  console.log(`\n[hdri] ${cfg.slug}`);
  const files = await fetchJson(`https://api.polyhaven.com/files/${cfg.slug}`);
  const entry = files.hdri?.[cfg.res]?.hdr;
  if (!entry) throw new Error(`${cfg.slug}: no .hdr at ${cfg.res}`);

  const outDir = path.join(OUT_ROOT, "env");
  await mkdir(outDir, { recursive: true });
  const outPath = path.join(outDir, `${cfg.key}_${cfg.res}.hdr`);
  await downloadFile(entry.url, outPath);
  console.log(`  ok: env/${cfg.key}_${cfg.res}.hdr`);
  return { ...cfg, shipped_file: `${cfg.key}_${cfg.res}.hdr` };
}

async function downloadMaterial(mat) {
  console.log(`\n[material] ${mat.key} (ambientCG: ${mat.assetId})`);
  const info = await fetchJson(
    `https://ambientcg.com/api/v2/full_json?type=Material&limit=1&id=${mat.assetId}&include=downloadData`,
  );
  const asset = info.foundAssets?.[0];
  if (!asset) throw new Error(`ambientCG asset not found: ${mat.assetId}`);

  const zipEntry = asset.downloadFolders?.default?.downloadFiletypeCategories?.zip?.downloads?.find(
    (d) => d.attribute === `${mat.res}-JPG`,
  );
  if (!zipEntry) throw new Error(`${mat.assetId}: no ${mat.res}-JPG zip`);

  const rawItemDir = path.join(RAW_DIR, mat.key);
  await mkdir(rawItemDir, { recursive: true });
  const zipPath = path.join(rawItemDir, zipEntry.fileName);
  await downloadFile(zipEntry.fullDownloadPath, zipPath);

  // Unzip (git-bash ships `unzip`; -o overwrite, -q quiet)
  await execFileAsync("unzip", ["-o", "-q", zipPath, "-d", rawItemDir]);

  const entries = await readdir(rawItemDir);
  const find = (suffix) => entries.find((f) => f.toLowerCase().includes(suffix.toLowerCase()) && /\.(jpg|jpeg|png)$/i.test(f));

  const colorFile = find("_Color") || find("_Albedo") || find("_Diffuse");
  const normalFile = find("_NormalGL") || find("_Normal");
  const roughFile = find("_Roughness");

  if (!colorFile) throw new Error(`${mat.assetId}: no color/albedo map found among ${entries.join(", ")}`);

  const outDir = path.join(OUT_ROOT, "materials", mat.key);
  await mkdir(outDir, { recursive: true });

  const shipped = {};
  if (colorFile) {
    await rename(path.join(rawItemDir, colorFile), path.join(outDir, "color.jpg"));
    shipped.color = "color.jpg";
  }
  if (normalFile) {
    await rename(path.join(rawItemDir, normalFile), path.join(outDir, "normal.jpg"));
    shipped.normal = "normal.jpg";
  }
  if (roughFile) {
    await rename(path.join(rawItemDir, roughFile), path.join(outDir, "roughness.jpg"));
    shipped.roughness = "roughness.jpg";
  }

  console.log(`  ok: materials/${mat.key}/ (${Object.keys(shipped).join(", ")})`);
  return {
    key: mat.key,
    label: mat.label,
    repeat_ft: mat.repeat_ft,
    maps: shipped,
    license: {
      source: "ambientCG",
      asset_id: mat.assetId,
      spdx: "CC0-1.0",
      source_url: `https://ambientcg.com/a/${mat.assetId}`,
    },
  };
}

async function main() {
  const sources = JSON.parse(await readFile(path.join(__dirname, "env-sources.json"), "utf-8"));

  const hdri = await downloadHdri(sources.hdri);
  const materials = [];
  for (const mat of sources.materials) {
    materials.push(await downloadMaterial(mat));
  }

  const manifest = {
    version: 1,
    generated_at: new Date().toISOString(),
    hdri: {
      key: hdri.key,
      label: hdri.label,
      url: `/catalog-assets/env/${hdri.shipped_file}`,
      license: { source: hdri.source, spdx: hdri.spdx, source_url: hdri.source_url },
    },
    materials: materials.map((m) => ({
      key: m.key,
      label: m.label,
      repeat_ft: m.repeat_ft,
      color_url: m.maps.color ? `/catalog-assets/materials/${m.key}/${m.maps.color}` : null,
      normal_url: m.maps.normal ? `/catalog-assets/materials/${m.key}/${m.maps.normal}` : null,
      roughness_url: m.maps.roughness ? `/catalog-assets/materials/${m.key}/${m.maps.roughness}` : null,
      license: m.license,
    })),
  };

  await writeFile(path.join(OUT_ROOT, "env-materials.json"), JSON.stringify(manifest, null, 2));

  const licenseLines = [
    "",
    "## Environment / Material Licenses (Stage 43.2)",
    "",
    "HDRI and PBR floor/wall textures — all **CC0**.",
    "",
    "| Key | Name | Source | License |",
    "|---|---|---|---|",
    `| \`env/${hdri.key}\` | ${hdri.label} | [Poly Haven](${hdri.source_url}) | ${hdri.spdx} |`,
    ...materials.map((m) => `| \`materials/${m.key}\` | ${m.label} | [ambientCG](${m.license.source_url}) | ${m.license.spdx} |`),
    "",
  ].join("\n");

  await appendFile(path.join(OUT_ROOT, "CATALOG_LICENSES.md"), licenseLines);

  console.log(`\nWrote ${path.join(OUT_ROOT, "env-materials.json")}`);
  console.log("Appended environment/material licenses to CATALOG_LICENSES.md");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
