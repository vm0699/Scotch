# Catalog Pipeline (Phase 43)

Build tool — not part of the runtime app. Downloads CC0 furniture from
[Poly Haven](https://polyhaven.com/) (primary) and
[Kenney's Furniture Kit](https://kenney.nl/assets/furniture-kit) (bathroom/
kitchen fixtures Poly Haven doesn't have), PBR floor/wall materials
(ambientCG), and an interior HDRI (Poly Haven); normalizes and vendors
everything into `services/api/app/assets/catalog/`, which FastAPI serves
statically and `services/api/app/core/catalog/` reads.

## Run

```
npm install
npm run build         # download (Poly Haven + Kenney) + normalize -> catalog.json + GLBs
npm run download-env  # download + vendor HDRI + PBR materials -> env-materials.json
```

`build` (download → download-kenney → normalize) and `download-env` must run
in that order — `normalize.mjs` rewrites `CATALOG_LICENSES.md` from scratch;
`download-env.mjs` appends to it.

## Adding a new furniture item

1. Check Poly Haven first (`download.mjs`'s `/info`/`/files` API — has real
   dimensions per asset). If nothing fits, check Kenney's Furniture Kit zip
   (`download-kenney.mjs`'s `KENNEY_ITEMS` map — dimensions are measured from
   the mesh directly since Kenney doesn't publish them).
2. Add an entry to `sources.json`: Poly Haven asset slug + target metadata
   (category, style_tags, snap, symbol_id); add `"source": "kenney"` if it's
   a Kenney item (routes it away from the Poly Haven downloader). For a new
   Kenney item, also add it to `download-kenney.mjs`'s `KENNEY_ITEMS` map
   (path inside the zip for the `.glb` and an isometric thumbnail).
3. `npm run download && npm run download-kenney && npm run normalize`.
4. Confirm the new GLB is floor-aligned/centered (`normalize.mjs` does this
   automatically) and add a matching case to the frontend's `FurnitureSymbol`
   (`apps/web/src/features/plan/floor-plan-svg.tsx`) if it needs a distinct
   2D plan symbol.

## Adding a new PBR material (floor/wall)

Add an entry to `env-sources.json` (`materials[]`) with an ambientCG asset ID,
then `npm run download-env`. The `key` must match a `MaterialId` in
`apps/web/src/features/massing/massing-data.ts` for the viewer to pick it up.
