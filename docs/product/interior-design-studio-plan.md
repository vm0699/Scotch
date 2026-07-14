# Scotch — Interior Design Studio Plan (Phase 43)

**Status:** ✅ Implemented (Stages 43.1–43.24) · **Owner:** product + eng · **Prepared:** 2026-07-13
**Shipped:** see [docs/integrations/interior-design.md](../integrations/interior-design.md) for the
as-built system (this document is the original plan/research — kept for context).
**Focus of this document:** interior design *only*. Everything here hangs off the existing
`ArchitectureProject` single source of truth. No new source of truth is introduced.

> **North-star for this phase:** a user opens an existing Scotch floor plan, clicks **one room**,
> types *"warm modern bedroom, oak floor"*, and gets a furnished, editable, photoreal-ish room in
> 2D **and** 3D — using **real open-source furniture models**, editable on canvas, exportable — with
> a deterministic no-AI fallback that always works. We make **one room type (bedroom) 100%
> production-grade** before expanding to living / kitchen / bath.

---

## 1. Why this document exists

The founder's directive: prioritize **interior design AI** as the next implementation, end-to-end,
production-grade for one thing first, then expand. Reference product: **[Planner 5D](https://planner5d.com/)**.
Hard constraints from the founder:

1. Understand how Planner 5D builds interiors and copy the winning pattern.
2. **Reuse open-source libraries / engines / datasets wherever possible** — do **not** hand-build
   furniture, textures, or a rendering engine.
3. Evaluate **PlayCanvas** for 3D viewing; the bar is "perfection and accuracy."
4. Integrate into the **existing** pipeline: pick one room from the floor plan → design its interior →
   move to the next.
5. Ship **one** neat, 100%-working, production-grade vertical slice; expand after.

This plan satisfies all five and slots into the phase-based operating model in
[roadmap.md](roadmap.md) (existing phases run 0–42; this is **Phase 43**).

---

## 2. How Planner 5D builds interiors (the pattern we copy)

Distilled from Planner 5D's product surface and the founder's feature dump (§9 below):

- **Room-first, two synchronized modes.** 2D = walls/doors/windows/measurements + furniture
  footprints. 3D = the same objects as meshes, decorated with materials. The user constantly flips
  between them; **one object model backs both views.** → *Scotch already has this shape:
  `FurnitureItem` carries a 2D footprint (x/y/width/depth/rotation) and a 3D height; the SVG renderer
  and the R3F renderer both read it.*
- **The catalog is the product.** ~8,000–10,000 items. Each catalog entry is **not just a mesh** — it
  is **metadata + 3D mesh + 2D plan symbol + material slots + snap behavior** (floor / wall-mounted /
  ceiling / tabletop). The editor manipulates the lightweight footprint; the heavy mesh follows.
- **AI is a proposal layer on top, never the source of truth.** Planner 5D's "Smart Wizard / Automatic
  Room Generator," "AI Design Generator," and "AI Studio" all emit into the *same editable project*.
  The user can always drag-fix the result. → *This is exactly Scotch's core invariant: AI proposes →
  validator checks → user edits, with a deterministic fallback that needs no AI key.*
- **Rendering is layered:** a fast live WebGL editor (simple baked lighting) for editing, plus a
  slower cloud photoreal render for presentation. → *Scotch mirrors this: live R3F for editing +
  the existing Phase 17/35 render-ready export pipeline for hero images.*

**The one-sentence lesson:** *catalog item = metadata + glTF mesh + 2D symbol + material slots; one
shared object model behind 2D and 3D; AI is a proposal layer.* Scotch's architecture is already this —
the work is filling in real assets, real 3D materials, an AI layout proposer, and room-focused editing.

Sources: [Planner 5D](https://planner5d.com/) · [Room planner](https://planner5d.com/use/room-planner-tool) ·
[FAQ](https://planner5d.com/blog/planner5d-frequently-asked-questions/) ·
[ToolChase review](https://toolchase.com/tool/planner-5d/) ·
[Home Stratosphere review](https://www.homestratosphere.com/planner-5d-software-review/)

---

## 3. Where Scotch already is (codebase audit)

This phase is an **extension, not a rebuild**. What exists today:

| Capability | Where | Status vs. interior needs |
|---|---|---|
| `FurnitureItem` model (footprint + rotation + 3D height, per room) | `apps/web/src/features/project/types.ts`; backend `core/models/project.py` | ✅ Base shape correct — needs `catalog_id`, material overrides, finer rotation |
| Deterministic furniture placement (wall-affinity, clearance, overlap, dining-chair snapping) | `services/api/app/core/architecture/furniture_placer.py` | ✅ Solid no-AI fallback — extend, don't replace |
| Per-room-type furniture templates (bedroom, living, kitchen, bath, study, dining…) | `services/api/app/core/architecture/furniture_defaults.py` | ✅ Reuse — add `catalog_id` per spec |
| 2D architectural furniture symbols | `apps/web/src/features/plan/floor-plan-svg.tsx` (`FurnitureSymbol`) | ✅ Keep — extend symbol set |
| 3D furniture as plain boxes | `apps/web/src/features/massing/massing-data.ts` (`mat:"furniture"`) | 🔶 Upgrade to real GLB meshes |
| R3F 3D viewer (OrbitControls, sun/shadows, camera presets, GLTF export) | `apps/web/src/features/massing/massing-viewer.tsx` | ✅ Extend with room-focus camera, GLB loading, HDRI, PBR |
| Per-room finishes (floor/wall/ceiling material + tile spec) | `RoomFinish` / `MaterialPlan` (Phase 31) | ✅ **Reuse to drive 3D floor/wall textures** — big unlock |
| Material PBR hints (base_color, roughness, metallic) | `core/architecture/materials.py`; `Material` model | ✅ Reuse for material slots |
| AI provider abstraction + schema repair + deterministic fallback | `services/api/app/core/ai/provider.py`, `factory.py` | ✅ Reuse for AI layout proposer |
| Shared validator (generation/edit/export) | `services/api/app/core/validation/` | ✅ Extend with interior rules (door-swing collision) |
| Generate/regenerate/versioning/exports pipeline | `api/routes/generate.py`, `versions.py`, `exports.py` | ✅ Interior plugs into the same flow |
| Blender automation + render-ready pipeline | Phase 17 / Phase 35 | ✅ Reuse for asset normalization + hero renders |

**Conclusion:** we are not starting from zero. We are (1) attaching a **real asset catalog** to a model
that already has furniture slots, (2) upgrading 3D from boxes to meshes with PBR + HDRI, (3) adding an
**AI layout proposer** behind the existing provider, and (4) building **room-focused editing UX**.

---

## 4. Build-vs-reuse: open-source engines, libraries & datasets

Founder directive is explicit: **reuse, don't build.** Decisions below, each with rationale.

### 4.1 3D rendering engine — **keep React Three Fiber (Three.js). Do NOT switch to PlayCanvas.**

Researched thoroughly. PlayCanvas ([engine](https://github.com/playcanvas/react) is MIT;
[@playcanvas/react](https://www.npmjs.com/package/@playcanvas/react) is real and capable, with a
[`<Gltf/>`](https://developer.playcanvas.com/user-manual/playcanvas-react/api/gltf/) component and an
excellent [model-viewer](https://github.com/playcanvas/model-viewer)). **Verdict: not worth switching.**

- Scotch's entire 3D layer (`massing-viewer.tsx`, `massing-data.ts`, GLTF export, camera presets, sun
  study) is R3F. Switching means a rewrite and running two 3D paradigms during migration.
- PlayCanvas's differentiators (game runtime, mobile texture compression, the **proprietary cloud
  Editor**) don't serve an in-app React design tool. R3F is designed to live *inside* an existing React
  app; PlayCanvas wants you to build *inside its* ecosystem.
- **"Perfection and accuracy" comes from asset quality, not engine choice.** Both are WebGL; visual
  parity is reachable in either. The realism levers are: real PBR GLB models + a Poly Haven interior
  **HDRI** via drei `<Environment>` + ambientCG **PBR textures** on floor/walls + ACES tone mapping +
  soft contact shadows + optional SSAO. All available in the R3F/drei ecosystem today.
- **Escape hatch:** if we ever want a standalone ultra-fidelity viewer or a WebGPU path, PlayCanvas's
  `model-viewer` can be embedded on an isolated page **without touching the main stack**. We keep the
  option; we don't take the migration cost now.

Sources: [PlayCanvas vs R3F](https://stackshare.io/stackups/playcanvas-vs-react-three-fiber) ·
[Three.js vs Babylon vs PlayCanvas](https://www.utsubo.com/blog/threejs-vs-babylonjs-vs-playcanvas-comparison) ·
[R3F vs Three.js 2026](https://www.creativedevjobs.com/blog/react-three-fiber-vs-threejs) ·
[pmndrs/react-three-fiber](https://github.com/pmndrs/react-three-fiber)

### 4.2 Furniture meshes — **curate CC0 glTF; never hand-model, never hot-link**

| Source | Content | License | Format |
|---|---|---|---|
| [Poly Haven — furniture](https://polyhaven.com/models/furniture) | High-quality PBR furniture (beds, sofas, chairs, tables, lamps) | **CC0** ([license](https://polyhaven.com/license)) | glTF/GLB + LODs |
| Kenney furniture kit ([awesome-cc0](https://github.com/madjin/awesome-cc0)) | Clean low-poly furniture — great for fast/mobile LOD | **CC0** | glTF/OBJ |
| Quaternius | Low/mid-poly furniture packs | **CC0** | glTF |
| [Sweet Home 3D libraries](https://www.sweethome3d.com/import-models/) | ~1,500 models; **BlendSwap-CC0 pack (175)** is unrestricted | CC0 (that pack) + CC-BY/FAL packs | OBJ → convert to GLB |

- Vendor everything: **curate a local catalog** (start ~15 bedroom items; grow to ~60–80), stored in
  the repo/served by FastAPI. **No runtime hot-linking** to third-party hosts.
- Prefer **CC0** to avoid attribution burden. If a CC-BY item is used, record attribution in a
  committed `CATALOG_LICENSES.md` and surface it in an in-app credits panel.
- **Explicitly excluded** (license risk): **3D-FRONT / 3D-FUTURE** (Alibaba; research-only — use only
  as layout *reference*, never ship its assets), and bulk **Sketchfab/Objaverse** (per-item mixed
  licenses).

### 4.3 Materials & lighting — **CC0 PBR + HDRI**

- **[ambientCG](https://github.com/madjin/awesome-cc0)** — 1,500+ CC0 PBR materials (wood floor, tile,
  marble, plaster, fabric). Drives `RoomFinish` floor/wall/ceiling in 3D.
- **Poly Haven textures + HDRIs** (CC0) — interior lighting environments for `<Environment>`.

### 4.4 Asset normalization pipeline — **[gltf-transform](https://gltf-transform.dev/) (Node CLI/SDK)**

Raw CC0 assets vary wildly in scale/orientation/size. Normalize **once, at curation time**, into a
consistent shippable form:

- Uniform scale (meters), origin at **floor-center**, consistent up-axis, Draco/Meshopt compression,
  texture resize/atlas, generate a low-poly LOD.
- gltf-transform is scriptable and CI-friendly. **Blender headless** (already integrated in Phase 17)
  is the fallback for meshes needing manual cleanup. Output: `{slug}.glb` + a thumbnail.

### 4.5 AI furniture layout — **reuse existing provider; pattern from the research, no heavy dep**

Academic auto-layout systems ([ATISS, LayoutGPT, Holodeck, InstructScene](https://arxiv.org/pdf/2506.07570),
[OptiScene](https://openreview.net/forum?id=ZnrM5RGrgR)) have **all converged on Scotch's exact
architecture**: an LLM proposes a layout as structured JSON over a **fixed catalog**, then a
rule/constraint pass fixes collisions & clearances. None ship as a production library. So we **do not
adopt a framework** — we replicate the proven pattern with what we already have:

1. **Deterministic (exists):** `furniture_placer.py` wall-affinity engine = the no-AI fallback.
2. **AI proposer (add):** `provider.py` sends room geometry + door/window positions + **catalog
   manifest** + style prompt to Claude; gets back placements `{catalog_id, x, y, rotation, material}`;
   schema-repaired.
3. **Validator (extend):** bounds, item-overlap, **door-swing collision**, window blocking, walkway
   clearance — extending the shared validator.

### 4.6 Interaction/UX reference codebases — **mine for patterns, don't adopt wholesale**

[blueprint3d-modern](https://github.com/charmlinn/blueprint3d-modern) (TS rewrite),
[blueprint-js](https://github.com/aalavandhaann/blueprint-js),
[react-planner](https://github.com/cvdlab/react-planner),
[arcada](https://github.com/mehanix/arcada) (React+Pixi),
[threejs-3d-room-designer](https://github.com/CodeHole7/threejs-3d-room-designer).
They solve wall-snapping, drag constraints, and catalog UX — **read their source for the hard
interaction problems**, but build on our `ArchitectureProject` model (theirs would fight our single
source of truth). For in-scene drag/rotate we use **drei `TransformControls` / pivot controls**.

### 4.7 Reuse summary

| Need | Reused open source | We build |
|---|---|---|
| 3D engine | Three.js + R3F + drei (existing) | Room-focus camera, GLB loader/cache, PBR/HDRI wiring |
| Furniture meshes | Poly Haven / Kenney / Quaternius / SH3D CC0 | Curation + `catalog.json` manifest |
| Materials/lighting | ambientCG + Poly Haven (CC0) | `RoomFinish`→texture mapping |
| Asset prep | gltf-transform (+ Blender fallback) | One normalization script |
| AI layout | existing `provider.py` + Claude | Prompt/schema + validator rules |
| Editing UX | drei TransformControls; blueprint3d/react-planner as reference | Room editor panel + on-canvas popover |
| 2D symbols | existing `FurnitureSymbol` | Extended symbol set |

---

## 5. Target architecture additions

All additive. Backend Pydantic and frontend TS stay mirrored (core invariant).

### 5.1 Data model changes

**Extend `FurnitureItem`** (both `types.ts` and backend `project.py`):
```
catalog_id?: string            // → catalog entry (mesh + symbol + slots). null = legacy block
material_overrides?: {slot: string -> material_ref}   // recolor/retexture per slot
z?: number                     // height off floor (wall-mounted/tabletop); default 0
rotation stays 0|90|180|270 for v1  // free-angle deferred to a later stage
```

**New: catalog (static, versioned, served by backend — not per-project):**
```
CatalogItem {
  id, slug, label, category,        // "bed" | "sofa" | "table" | "lamp" | ...
  style_tags: string[],             // "modern","scandinavian","rustic",...
  footprint_w, footprint_d,         // feet, canonical (rotation 0)
  height,                           // feet
  mesh_url, thumbnail_url,          // vendored GLB + preview
  symbol_id,                        // maps to a 2D FurnitureSymbol
  snap: "floor"|"wall"|"ceiling"|"tabletop",
  material_slots: [{slot, default_material_ref, editable}],
  license: {source, spdx, attribution?}   // provenance, always recorded
}
```

**New per-room interior status** (small, on `Room` or a parallel map):
```
RoomInterior { room_id, status: "empty"|"designed"|"stale", style?, seed?, last_generated_at }
```
`stale` flips true when the room is resized/moved after furnishing (reuses the existing
stale-tracking pattern from MEP/BOQ/details).

`RoomFinish` (already exists) gains no new fields — we **wire it into 3D** (floor/wall/ceiling
material → ambientCG texture) which it doesn't drive today.

### 5.2 Rendering additions (R3F)

- **GLB loader + cache** (drei `useGLTF` + Draco); when `catalog_id` is set render the mesh, else fall
  back to the current box (graceful, progressive).
- **Room-focus camera:** "enter room" framing derived from room bounds (reuse `cameras.py` logic).
- **PBR floor/walls** from `RoomFinish` via ambientCG textures; **`<Environment>` HDRI**; ACES tone
  mapping; **contact shadows**; optional SSAO for depth.
- Existing sun-study/shadow system stays.

### 5.3 AI layout proposer (backend)

New `core/architecture/interior_designer.py`: builds the prompt (room geometry, openings, catalog
manifest filtered by room type + style), calls `provider.py`, schema-repairs, and hands off to the
placer/validator. Deterministic `furniture_placer.py` remains the fallback and the hybrid seed.

### 5.4 API surface (new routes under existing FastAPI app)

```
GET  /catalog                          # list/browse catalog (filter by category/style/room type)
GET  /catalog/{id}                     # single item + mesh/thumbnail URLs
POST /projects/{id}/rooms/{rid}/interior/generate   # {mode, style, prompt} → furnished room
POST /projects/{id}/rooms/{rid}/interior/edit       # add/move/rotate/swap/delete/recolor item
GET  /projects/{id}/rooms/{rid}/interior            # current interior + status + warnings
```
Static meshes/textures served from a vendored `assets/catalog/` dir (FastAPI static mount).

---

## 6. The phased plan — Phase 43: Interior Design Studio

Operating model per [CLAUDE.md](../../CLAUDE.md): each **stage** is fully implemented and additive —
no new architecture past Stage 43.5, only catalog + template work. As-built detail lives in
[docs/integrations/interior-design.md](../integrations/interior-design.md); this section tracks
per-stage status against the original plan.

### Stage 43.1 — Catalog foundation *(bedroom slice)* — ✅ Shipped
- 15 CC0 bedroom assets curated from Poly Haven, normalized via `@gltf-transform` (recentered,
  floor-aligned, welded) — `tools/catalog-pipeline/`.
- `CatalogItem` model (backend + TS), `catalog.json` manifest, `GET /catalog`/`GET /catalog/{id}`,
  static serving at `/catalog-assets`, `CATALOG_LICENSES.md`.
- **Verified:** 13 pytest tests including live GLB-byte validation over HTTP.

### Stage 43.2 — Room-focused 3D with real meshes — ✅ Shipped
- `CatalogFurnitureLayer` — GLB loader/cache, **runtime-measured** bounding box (not just trusted
  metadata) scaled to the catalog's real footprint; box fallback preserved for un-linked items.
- PBR floor/wall materials (ambientCG) wired into the existing `RoomFinish` → `MaterialId` mapping; CC0
  interior HDRI; "Enter Room" camera.
- **Note:** a real caught-and-fixed bug here — unstable object/array references fed into `useTexture`
  stalled the R3F Suspense boundary indefinitely; fixed via proper memoization.

### Stage 43.3 — Generation (deterministic + AI) — ✅ Shipped
- `furniture_defaults.get_template()` resolves every catalog-linked spec's real width/depth/height —
  applies to **every** caller (whole-project generation too, not just the interior endpoint), so 2D
  clearance math and the 3D mesh always agree.
- `interior_designer.py`: deterministic path is **self-healing** (drops any item that would block a
  door swing, with a warning — the placer itself is door-unaware); AI path calls Anthropic over the
  fixed catalog, schema-repaired, falls back to deterministic on any failure.
- `interior_validator.py`: bounds, overlap, door-swing collision (hard errors), window-blocking
  (advisory). `POST/GET /projects/{id}/rooms/{room_id}/interior/generate`.

### Stage 43.4 — Room-focused editing UX — ✅ Shipped (structured controls, not freehand drag)
- Click-to-select synced across 2D plan ↔ 3D highlight (`FurnitureSelectionOutline`) ↔ right panel.
- `POST …/interior/edit` — move/rotate/delete/swap/add, each re-validated before persisting.
- **Real bug caught & fixed:** an edit that only touched item A was being rejected because item B (from
  an earlier, non-self-healing generation) already had an unrelated violation. Fixed by only rejecting
  edits that introduce a **new** error — a room with one bad item never becomes permanently un-editable.
- `RoomInterior` stale-tracking wired into `regenerate.py` (resize → stale; room removed → entry dropped).
- **Scope call:** editing ships as rotate/swap/delete/add buttons + dropdowns, not mouse-drag. Every
  result is still fully click-fixable; freehand drag-with-snap is deferred.

### Stage 43.5 — Polish, exports & docs — ✅ Shipped
- DXF `A-FURN` layer (`dxf_exporter.py`); GLB export is automatic (furniture is real scene geometry,
  `GLTFExporter` already walks the whole graph).
- **3D rendering depth** (explicit founder request — "complete, detailed, and complex"): PCSS soft
  shadows, `N8AO` ambient occlusion, bloom, physically-based `<Sky>` synced to the sun-study
  azimuth/altitude, physical glass (transmission/IOR/clearcoat) replacing flat alpha, a CAD-style
  reference grid, corrected color-space/`envMapIntensity` on furniture materials, DPR scaling.
- Credits link; README/roadmap updated; `docs/integrations/interior-design.md` written.

### Stage 43.6 — Living room (generalization proof) — ✅ Shipped
3 new CC0 items (sofa, coffee table, media console) + 5 reused from the bedroom set (armchair, side
table, bookshelf, plant — the catalog isn't room-scoped). `living`/`seating` templates catalog-backed.

### Stage 43.7 — Kitchen — ✅ Shipped
`cooktop_stove` linked. Counters **deliberately** stay unlinked — they already render from a parametric
L-counter sized to the room (`massing-data.ts`), so a fixed catalog mesh would double-render.
Refrigerator has no CC0 source anywhere checked — box fallback, documented, not silently dropped.

### Stage 43.8 — Foyer *(redirected from bathroom)* — ✅ Shipped
Poly Haven has no WC/basin/shower/bathtub CC0 models — checked directly via their API, not assumed.
Redirected this slot to foyer (`console_table_classic`); shoe rack has no match, box fallback.
**Bathroom stays an open, documented gap** — not swept under the rug.

### Stage 43.9 — Dining room — ✅ Shipped
Dining table + dining chair (all 6 chair slots) + media console reused as sideboard.
`_chair_boxes_around_table` made catalog-aware — the real chair mesh isn't square (1.42×1.89 ft); fixed
to use the larger dimension for the validated slot so the mesh never overhangs it.

### Stage 43.10 — Study/office — ✅ Shipped
Metal office desk + school chair (as office chair) + reused bookshelf.

### Stage 43.11 — Master bedroom full catalog wiring — ✅ Shipped
King bed frame catalog-linked; wardrobe and both nightstands reused from the bedroom catalog. Dressing
table left on the box fallback (no CC0 source found).

### Stage 43.12 — Balcony/outdoor — ✅ Shipped
Plastic outdoor chair; reused the small side table as an outdoor table (Poly Haven's only dedicated
outdoor table is a 7×10 ft picnic table — too large for a balcony).

### Stage 43.13 — Storage/utility — ✅ Shipped
Reused the bookshelf mesh as shelving — cheapest room in the catalog, same mesh in a different context.

### Stage 43.14 — Bathroom fixtures via alternate CC0 source — ✅ Shipped
Poly Haven ships zero bathroom fixtures or a kitchen sink (confirmed directly via their API, not
assumed). Added **Kenney's Furniture Kit** as a second CC0 source (`download-kenney.mjs`) — one zip,
no per-asset API, so bounds are measured at extraction time instead of trusted from metadata. Toilet,
bathroom sink, bathtub, and kitchen sink now catalog-linked; "shower" renders the bathtub mesh (no
dedicated shower-stall model found — an honest approximation, not a mislabel).

### Stage 43.15 — Remaining gap assets — Investigated, gaps documented
Searched for CC0 refrigerator/dressing table/shoe rack models beyond Poly Haven and Kenney. A
Quaternius Google Drive folder was identified as a possible source via their official site's download
button, but pulling from it was declined — an agent-guessed external link has no confirmed provenance,
unlike Poly Haven/Kenney's verified API/zip channels. These three items stay on the box fallback;
revisiting needs an explicit go-ahead on a specific alternate source.

### Stage 43.16 — Material recolor — ✅ Shipped
`material_slots[].editable` flipped to `true` across the catalog. Recolor is a `Material` entry (reusing
the same model walls/floors already use) with `base_color` set to the picked hex, referenced from
`FurnitureItem.material_overrides[slot]`; a deterministic id from the color itself (`furniture-tint-{hex}`)
means re-picking the same color reuses one entry instead of accumulating duplicates. Rendered as a
multiplicative tint over the item's baked diffuse texture (`meshStandardMaterial.color`), not a
per-region texture swap. The Interior Design panel shows a native color swatch only for items with an
editable slot.

### Stage 43.17 — Freehand drag-with-snap on 2D canvas — ✅ Shipped
`FurnitureSymbol` in `floor-plan-svg.tsx` is now pointer-draggable: client coordinates are converted to
plan-space feet via the SVG's own `getScreenCTM()` (correct under CSS zoom automatically), snapped to a
0.25 ft grid while dragging, and committed through the same `interior/edit` `move` action as any other
edit — so a drag that would push the item outside the room or into a door swing is rejected by the
existing validator, same as a panel edit would be. A plain click (no drag distance) still selects.

### Stage 43.18 — Asset compression: geometry (Meshopt) — ✅ Shipped
`normalize.mjs` now Meshopt-compresses geometry (`meshopt({encoder: MeshoptEncoder, level: "high"})`,
`EXT_meshopt_compression`) as a transform before writing each GLB. No frontend change was needed —
drei's `useGLTF()` already defaults `useMeshopt=true` (and `useDraco=true`), wiring a `MeshoptDecoder`
into three.js's `GLTFLoader` automatically.

### Stage 43.19 — Asset compression: textures (WebP) — ✅ Shipped
Textures turned out to dominate payload far more than geometry — added `textureCompress({encoder:
sharp, targetFormat: "webp", quality: 82})` ahead of the Meshopt pass. Combined, the 30-item catalog's
total payload went from **36.4 MB to 9.2 MB (~75% smaller)**. Again no frontend change: three-stdlib's
`GLTFLoader` (which drei's `useGLTF` wraps) has a built-in `EXT_texture_webp` extension, no plugin
registration needed. Verified by round-tripping every compressed GLB through `gltf-transform`'s reader
with `MeshoptDecoder` registered — all 30 decode to valid, non-empty meshes with finite bounds and
confirm `image/webp` on every texture.

### Stage 43.20 — Office furniture template + a real placer bug fix — ✅ Shipped
The deterministic generator has produced `type="office"` rooms since the café/office building-kind
shipped (`floorplan_generator.py`'s `_office_fallback_program`), but Phase 43 never gave it a furniture
template — it rendered as an empty shell. Added one, reusing `desk_office_metal`/`office_chair_school`
(already in the catalog from `study`) as repeating desk+chair pairs, gated by room area, plus a meeting
table and bookshelf for larger rooms.

Building this surfaced a real, pre-existing bug: any room with a chair placed on the **same wall** as a
desk (e.g. `study`'s `office_chair`) had its chair silently dropped — both items' candidate boxes start
flush at the same wall position, so the chair's box always overlaps the desk's and the placer's
documented "skip with no warning" behavior (§3, item 7) ate it invisibly. Confirmed empirically: a bare
`study` room's placer output had a desk and two bookshelves, but no chair. Fixed by adding a
`wall_offset: float = 0.0` field to `FurnitureSpec` (shifts the item further from its wall into the room)
and using it in `furniture_placer.py`'s `_candidate()`; set to the desk's real depth + gap (3.4 ft) on
`study`'s and `office`'s chair specs. Verified across all 19 room types at a generous 25×20 ft size with
an independent overlap check — zero overlaps, and `study`'s chair now actually appears.

### Stage 43.21 — Café furniture templates + Add-room dropdown gap — ✅ Shipped
`cafe_seating` and `cafe_counter` (the other two `type=` values the café building-kind produces that
had no template — its kitchen/storage/restroom rooms already reuse `kitchen`/`storage`/`bathroom`
types, which were covered) now have templates. `cafe_seating` reuses the dining table/chair catalog
items — the chair-around-table placement logic keys off `spec.type == "dining_table"` and a
`chair_*` type set, not the room type, so a café bistro table is placed exactly like a dining table, just
sized for 2 chairs instead of 6. `cafe_counter` reuses `console_table_classic` (foyer's console) as a
service counter — a long low table is a reasonable stand-in.

Separately: the 2D "Add room" dropdown (`program-grid.tsx`) only listed 9 of the 19 room types the
furniture/compliance pipeline already understands — `master_bedroom`, `seating`, `kitchenette`,
`foyer`, and `restroom` all had full catalog/template support but couldn't actually be created through
the UI. Added all 5.

### Stage 43.22 — Bulk "furnish all rooms" action — ✅ Shipped
`POST /projects/{id}/interior/generate-all` runs the same per-room generator across every room in the
project in one action — the same "one thing 100% working, then expand" pattern applied to the *action*
itself, not just room-type coverage. Skips rooms that already have furniture unless `overwrite=true`
(safe to call on a partially-furnished project without clobbering manual edits); rooms with no matching
template (corridor, stair, parking) come back as `"empty_template"`, not an error. Each room is
persisted and re-validated exactly like the single-room endpoint — `_persist`'s "other rooms'
furniture" is recomputed from the just-updated project on every iteration, so an earlier room in the
loop can't get wiped by a later one's save. Surfaced in the Interior Design panel as a "Furnish all
rooms" card in the no-room-selected empty state, with the same mode/style controls as the per-room
generator plus an "regenerate already-furnished rooms too" checkbox.

### Stage 43.23 — Self-audit: add-room whitelist, master bedroom reachability, bed clearance — ✅ Shipped
A background research pass across the rest of the codebase (BOQ, compliance, exports, room-type lists)
surfaced real regressions and a long-standing latent bug that Stage 43.21's own dropdown fix had exposed:

- **Add-room whitelist gap.** Stage 43.21 added `seating` and `foyer` to the frontend "Add room" dropdown
  but never checked the backend — `regenerate.py`'s `VALID_ADD_ROOM_TYPES` didn't include either, so
  picking them threw `ChangeError: Unknown room type`. Fixed by adding both to `_TYPE_ID_PREFIX`,
  `_ROOM_ZONE`, `_SIZE_KEY`, and `_default_room_name`'s label dict, plus new `defaults.py` size entries.
- **`master_bedroom` was never a real type.** The floor plan generator always stores `type="bedroom"` for
  the master bedroom too (it's a *naming* convention — the first bedroom added is auto-named "Master
  Bedroom" — not a distinct `room.type`). That meant the `master_bedroom` furniture template (Stage
  43.11 — king bed, dressing table) was **unreachable**: no room anywhere in the system ever actually
  carried that literal type string. Fixed with a new `effective_room_type(room_id, room_type, room_name)`
  helper in `furniture_defaults.py` that redirects to the `master_bedroom` template when a `"bedroom"`
  room is identifiably the master (id `"bed-master"` or "master" in the name); wired into both
  `furniture_placer.place_furniture_in_room` and `interior_designer._resolved_template`. Removed the
  now-understood-to-be-wrong `master_bedroom` entry from the Add-room dropdown — it isn't a separate
  addable type, adding a first "Bedroom" already produces one.
- **Beds silently vanishing in compressed rooms — a real, previously-hidden bug.** Making
  `master_bedroom` reachable immediately surfaced it: the king bed (catalog depth 6.69 ft) plus its 3.5 ft
  declared clearance needs ~10.3 ft of room depth, but depth-compressed sites (common on smaller plots)
  can produce master bedrooms as shallow as 8.4 ft — the clearance check failed and the **bed was
  silently dropped entirely**, the worst possible outcome for a priority-1 item. Confirmed the *regular*
  `bedroom` template's bed had the exact same latent bug (same real depth, same 3.5 ft clearance) — it's
  been possible since Stage 43.1, just never surfaced because nobody happened to test a small enough
  bedroom. Fixed at the root: `furniture_placer.py`'s clearance check no longer hard-rejects a candidate
  just because the *ideal* clearance doesn't fit — it degrades to whatever's actually available, down to
  a `MIN_ACCEPTABLE_CLEARANCE` (0.3 ft) floor, and only rejects below that floor. This is a strictly
  monotonic improvement (identical placement for every case that already passed; previously-dropped items
  now place with reduced-but-nonzero clearance). Verified across depths from 12 ft down to 6.5 ft: the
  bed now places correctly through 8.4 ft (previously failing) and correctly still fails below ~7 ft
  (genuinely too small, not a bug).
- Also fixed `study`'s `office_chair`, which had the identical same-wall-as-desk overlap bug from Stage
  43.20's `wall_offset` fix applied retroactively — it had been silently missing its chair since it shipped.

### Stage 43.24 — Self-audit: compliance coverage, café/office restroom typing, export colors — ✅ Shipped
Continuing the same audit:

- **Compliance rule coverage.** `rules.py`'s minimum-area and ventilation checks silently skipped every
  room type added since Stage 43.14 (`office`, `cafe_seating`, `cafe_counter`, `kitchenette`, `foyer`,
  `seating`, `restroom`) — not incorrect, just incomplete: a café/office project got zero compliance
  feedback. Added `restroom` to the minimum-area table using the WC-only NBC figure (12.9 ft² / 1.2 m²)
  that was already cited in this file's own docstring but never wired to an actual rule. Added `office`,
  `cafe_seating`, and `seating` to the habitable-room (ventilation) set — they're continuously
  human-occupied exactly like `study`/`dining` already there. Deliberately did **not** invent minimum-area
  figures for the remaining commercial/utility types — NBC Part 4 Section 5 (the cited source) only
  specifies residential dwelling-unit areas, and presenting a fabricated number as if it were code-backed
  would violate the same principle the TN advisory's "placeholder regulation values" disclaimer protects.
- **Café/office restrooms were typed `"bathroom"`, not `"restroom"`.** `_cafe_program` and
  `_office_fallback_program` both built their restroom room with `type="bathroom"` even though the
  correctly-distinct `restroom` furniture template (WC + basin, no shower/tub — Stage 43.14) and
  `_SIZE_KEY` entry (`"restroom"`) already existed. The bug: a café or office's public restroom got a
  full **bathtub/shower** in its furniture layout, and (after the compliance fix above) would have been
  checked against the larger combined-bath minimum instead of the correct smaller one. Fixed both call
  sites to `type="restroom"`; also extended the door-width (2.5 ft) and window-width (1.5 ft, privacy-
  sized) rules that already special-cased `"bathroom"` to cover `"restroom"` too, for the same reason.
- **Export material colors.** `sketchup_exporter.py`/`blender_exporter.py`'s room-colour maps (both have a
  neutral default fallback, so this was cosmetic, not broken) didn't have entries for `kitchenette`,
  `restroom`, `office`, `cafe_seating`, `cafe_counter` — added, each reusing its functional counterpart's
  tone (kitchenette≈kitchen, restroom≈bathroom, office≈study, cafe_seating≈living, cafe_counter≈kitchen).

**30 total catalog items**, 16 catalog-backed room types (bedroom, master_bedroom, living, seating,
kitchen, kitchenette, dining, study, foyer, balcony, storage, bathroom, restroom, office, cafe_seating,
cafe_counter) across two CC0 sources (Poly Haven, Kenney), plus a bulk "furnish all rooms" action.

> **Bedroom first** because it has the strongest, most legible placement conventions (bed centered on a
> wall, nightstands flanking, wardrobe clearance) — the easiest room to make *feel* perfect, which is
> the whole point of the "one thing 100% working" mandate.

---

## 7. Definition of "100% working" (the bedroom slice)

- Type a prompt → get a furnished bedroom with **real** furniture in 2D symbols + 3D meshes.
- Works **with and without** an AI key (deterministic fallback proven by tests).
- Every item is **selectable and editable** on canvas and in the panel (move/rotate/swap/recolor/delete),
  with live clearance feedback; door swings never collide.
- Floor/wall materials render from `RoomFinish`; lighting via HDRI; looks studio-grade, not a demo.
- Exports: DXF furniture layer + GLB with meshes + one hero render.
- All assets are **CC0 (or attributed CC-BY)**, vendored, license-manifested.
- State lives entirely in `ArchitectureProject`; versioned; survives reload.

---

## 8. What's needed from you (externals, manual setup, decisions)

Most of this phase is self-contained — the asset sources are **CC0 with no signup, no paywall, no API**,
and the AI layout layer reuses the provider you already have. But a few things genuinely need you. Each
item below is tagged **[Blocking]** (a stage can't start/finish without it) or **[Non-blocking]** (I can
proceed with a sensible default and you confirm later), and pinned to the stage where it first bites.

### 8.1 Accounts & API keys
- **AI provider key (Anthropic / OpenAI-compatible)** — *[Non-blocking, Stage 43.3].* Needed only for the
  **AI** layout proposer. The deterministic engine works with **no key** (core invariant), so 43.1/43.2
  aren't blocked. If you already set `SCOTCH_*` AI env vars for earlier phases, nothing new is needed —
  just confirm the key is valid and which provider to use for interiors.
- **Asset sources (Poly Haven, ambientCG, Kenney, Quaternius, Sweet Home 3D):** **nothing needed** — all
  CC0, downloadable without accounts. I vendor them into the repo.

### 8.2 One-time decisions I need from you *(these are taste/policy/infra calls only you can make)*
- **License policy** — *[Blocking, Stage 43.1].* Confirm: **CC0-only**, or **CC0 + CC-BY-with-attribution
  allowed?** CC0-only is safest (zero attribution burden); allowing CC-BY roughly doubles available
  furniture but requires a credits panel. My default recommendation: **CC0-only for v1.**
- **Commercial-use intent** — *[Blocking, Stage 43.1].* Confirm Scotch is (or will be) a **commercial**
  product. It affects nothing for CC0, but locks the "no research-only assets (3D-FRONT/Objaverse)" rule.
- **Asset storage strategy** — *[Blocking, Stage 43.1].* Vendored GLBs add binary weight (~10–40 MB for the
  bedroom set, more as we expand). Pick one:
  1. **Commit to the repo** (simplest; fine at bedroom scale) — *my default for the slice*,
  2. **Git LFS** (keeps repo light; needs LFS enabled on your Git host),
  3. **Object storage / CDN** (e.g., an S3-compatible bucket on your Render setup) — best at full-catalog
     scale but needs an account + bucket from you.
  I recommend **#1 for the bedroom slice, migrate to #3 before large expansion.**
- **Production asset hosting on Render** — *[Non-blocking, Stage 43.5].* In dev, FastAPI serves the assets
  statically. For your Render deployment, confirm whether static-from-FastAPI is acceptable or you want a
  bucket/CDN. Only matters when we ship the slice; I'll flag it again at 43.5.
- **Style presets to support** — *[Non-blocking, Stage 43.3/43.5].* I'll default to **modern /
  scandinavian / rustic**. Tell me if you want different/more (e.g., Indian contemporary, minimalist).
- **Realism vs. performance target** — *[Non-blocking, Stage 43.2].* Default: **desktop-first, studio-grade
  live view.** If mobile/low-end must be first-class, I'll bias toward low-poly LODs and lighter lighting.

### 8.3 Local tooling (dev environment)
- **Node + gltf-transform** — I add it as a dev dependency; no action from you unless your machine blocks
  global installs. *[Non-blocking].*
- **Blender** — used only as a **fallback** for meshes needing manual cleanup. Phase 17 already integrated
  Blender, so it's presumably installed; if not, only needed for the occasional messy asset. *[Non-blocking].*

### 8.4 Review / sign-off checkpoints *(your eyes, not your setup)*
- **Curated bedroom set approval** — *[Blocking, end of 43.1].* I'll present ~15 candidate items with
  thumbnails; you approve/swap on taste before we wire them in.
- **First rendered bedroom sign-off** — *[Blocking, end of 43.2].* A visual "does this look studio-grade?"
  call — the whole point of the "one thing 100% working" mandate is that *you* judge it good.
- **Per-stage Stage-Completion confirmation** — *[Blocking, every stage].* Already part of the operating
  model: I stop after each stage and ask before continuing.

### 8.5 Optional / helpful (not required)
- **Reference interiors you like** (Pinterest/screenshots/brand examples) — helps me match taste faster on
  curation and style presets. Purely accelerant.
- **A specific first room type** — I've defaulted to **bedroom**; say the word if you'd rather start with
  living room or kitchen (bedroom remains my recommendation for legible placement rules).

> **Bottom line:** to *start* I only need three things — (1) license policy (CC0-only?), (2) asset storage
> choice (repo commit for the slice?), and (3) confirm bedroom-first. Everything else can ride on defaults
> and be adjusted at its stage. The AI key is only needed once we reach generation (43.3).

---

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Asset license contamination | CC0-first; committed `CATALOG_LICENSES.md`; exclude 3D-FRONT/Objaverse; credits panel for CC-BY |
| GLB payload / perf on web | gltf-transform Draco/Meshopt + LODs + lazy load; box fallback until mesh ready; cap live catalog size |
| AI layout produces overlaps/blocked doors | Validator is authoritative; deterministic seed in hybrid; AI output always repaired |
| Scope creep into full Planner 5D | This phase = **interior only, bedroom first**; §9 marks most Planner 5D features Deferred/Out |
| Model/frontend drift | Extend Pydantic + TS together every stage (core invariant) |
| Two 3D stacks | Explicitly reject PlayCanvas migration; keep single R3F stack |

---

## 10. Planner 5D feature map → Scotch scope

The founder's 40-category dump, triaged. **In = this phase (43).** **Later = future interior stages.**
**Out = different phase / not interior.** Reuse noted where relevant.

| # | Planner 5D area | Scope | Notes / reuse |
|---|---|---|---|
| 2 | AI floor-plan recognition | Later | Already partially covered by Phase 39 (scan-to-plan); interior reads its output |
| 3 | 2D design mode | **In** | Extends existing SVG plan + `FurnitureSymbol` |
| 4 | 3D design mode | **In** | R3F room-focus + meshes (43.2) |
| 5 | Furniture/object catalog | **In** | CC0 catalog (43.1); grows over expansion |
| 6 | Object customization (move/rotate/resize/dup/delete) | **In** | Editing UX (43.4); resize/free-angle later |
| 7 | Materials/colors/finishes | **In** | `RoomFinish` + ambientCG + material slots |
| 8 | Smart Wizard / auto room generator | **In** | Deterministic + AI generate (43.3) |
| 9 | AI Design Generator (photo→redesign) | Later | Needs image input; after bedroom slice |
| 10 | Automated furniture arrangement | **In** | Core of 43.3 |
| 11 | AI Studio (text→concept, mood boards, restyle) | Later | Text→layout is In (43.3); mood boards/restyle later |
| 12 | Photorealistic rendering | **In (reuse)** | Phase 17/35 render pipeline for hero image (43.5) |
| 13 | 360°/immersive | Later | R3F can do orbit now; panorama export later |
| 14–15 | AR / VR / visionOS | Out | Not interior-core; WebXR possible far future |
| 16 | 3D model import (obj/fbx/blend) | Later | gltf-transform already handles ingest; expose as user import later |
| 17 | 3D from photos | Out | Third-party/heavy ML; not now |
| 18 | CAD export | **In (reuse)** | Existing DXF/exports + furniture layer (43.5) |
| 19–20 | Budgeting / specs / price estimator | **In (reuse)** | **Existing BOQ/Cost engine (Phase 31)** — interiors feed it; Scotch advantage over Planner 5D |
| 21 | Mood boards | Later | |
| 22 | Project mgmt | Have | Existing projects/versioning |
| 23 | Collaboration/sharing | Have/Later | Phase 41 collaboration exists |
| 24–28 | Designer profiles / marketplace / school / battles | Out | Community/business, not interior-core |
| 29 | AI assistant (Bernard) | Have | Phase 24 in-app chat can cover this |
| 30 | Room-specific tools (bedroom/living/kitchen/bath…) | **In→expand** | Bedroom now; others in 43.6+ |
| 31 | Commercial-space design | Later | Same engine, new templates |
| 32 | Outdoor/landscape | Out (this phase) | Balcony template exists; full landscape later |
| 33 | Architecture/blueprint tools | Have | Core product already |
| 34 | Home repair estimator | Later | Overlaps BOQ |
| 35 | Furniture shopping | Out | Commerce integration, far future |
| 36–37 | Multi-platform / browser | Have | Web app already |
| 38–40 | Enterprise / configurator / education | Out | Business track, not interior-core |

**Scotch's edge over Planner 5D:** interiors here **feed the existing BOQ/Cost/MEP/working-drawing
engines** — furnishing a room updates its bill of quantities and cost, and exports to professional CAD.
Planner 5D is consumer-decor; Scotch stays *prompt-to-production* even for interiors.

---

## 11. What's next

Stages 43.1–43.22 are shipped (§6) — 30 catalog items across 16 room types (residential + the
café/office commercial building-kinds the generator already produced but Phase 43 hadn't caught up to
yet), two CC0 sources, material recolor, freehand drag, Meshopt+WebP asset compression, and a bulk
"furnish all rooms" action. Remaining open thread:

- **Refrigerator, dressing table, shoe rack** — the three items left on the box fallback. No suitable
  CC0 model found in Poly Haven or Kenney's Furniture Kit (checked directly, not assumed). A Quaternius
  Google Drive folder was identified as a possible source but declined as unverified provenance (Stage
  43.15) — revisiting needs an explicit go-ahead on a specific alternate source.
- **Retail/hospitality room types** — unlike office/café, these have no existing room-type or
  building-kind support anywhere in the generator (`floorplan_generator.py`, compliance rules, the
  "Add room" dropdown) — adding them would mean inventing a new building category, a product-scope call
  rather than a furniture-catalog one. Deliberately not attempted without that decision.
