# Interior Design Studio (Phase 43)

How Scotch furnishes a room: real CC0 furniture, a deterministic no-AI-key
placer, an optional AI layout proposer, and room-focused 2D/3D editing — all
built on the existing `ArchitectureProject` model. See
[docs/product/interior-design-studio-plan.md](../product/interior-design-studio-plan.md)
for the original plan and research; this doc covers the shipped system.

## Data model

- **`FurnitureItem`** (`core/models/project.py`) — existing Phase 26 model,
  extended with `catalog_id` (links a real GLB), `material_overrides` (recolor
  — `{slot: material_id}`, resolved against `project.materials`; a tint
  multiplies over the item's baked diffuse texture, see Frontend below), and
  `z` (height off floor for wall/ceiling/tabletop items).
- **`CatalogItem`** (`core/models/catalog.py`) — one vendored furniture asset:
  footprint, height, mesh/thumbnail URLs, snap type, style tags, license.
  Static, versioned, project-independent — not stored per-project.
- **`RoomInterior`** (`core/models/project.py`) — per-room furnishing status
  (`empty | designed | stale`), style, generation mode, warnings. Flips to
  `stale` when its room is resized; dropped when its room is removed
  (`core/architecture/regenerate.py`).

## Asset pipeline

`tools/catalog-pipeline/` (Node, not part of the runtime app) downloads CC0
assets, normalizes GLBs (recenter X/Z, floor-align Y, weld/dedupe), then
compresses both textures and geometry — WebP textures (`EXT_texture_webp` via
`gltf-transform`'s `textureCompress({encoder: sharp})`) and Meshopt geometry
(`EXT_meshopt_compression` via `meshopt()`) — before vendoring everything into
`services/api/app/assets/catalog/` (served statically at `/catalog-assets`,
committed to the repo). Together these cut the 30-item catalog's payload from
36.4 MB to 9.2 MB (~75%); textures dominated the original size far more than
geometry did. Both formats are natively supported by three-stdlib's
`GLTFLoader` (which drei's `useGLTF()` wraps) — `EXT_texture_webp` has a
built-in extension handler, and `useGLTF()` already defaults `useMeshopt=true`
— so no runtime code changes were needed for either. Two sources feed it:

- **[Poly Haven](https://polyhaven.com/)** (`download.mjs`) — primary source
  for furniture, PBR materials (via ambientCG), and the interior HDRI. Has a
  clean per-asset API (`/info`, `/files`) with real-world dimensions.
- **[Kenney's Furniture Kit](https://kenney.nl/assets/furniture-kit)**
  (`download-kenney.mjs`) — Poly Haven has **no** bathroom fixtures (WC,
  basin, bathtub) or kitchen sink at all (confirmed directly via their API,
  not assumed) — Kenney's kit has them, same CC0 terms. Ships as one zip with
  packed `.glb` files per item (no per-asset API), so `download-kenney.mjs`
  extracts named files and measures their real bounds itself (Poly Haven
  publishes dimensions; Kenney doesn't) before handing off to the same
  `normalize.mjs` used for everything else.

An item's `sources.json` entry only needs `"source": "kenney"` to route it to
the Kenney extractor instead of Poly Haven's API — everything downstream
(normalize, catalog.json, licensing) is source-agnostic. See
[tools/catalog-pipeline/README.md](../../tools/catalog-pipeline/README.md) for
how to add new items. Licenses are recorded in
`services/api/app/assets/catalog/CATALOG_LICENSES.md` — linked from the
Interior Design panel.

## Generation — `core/architecture/interior_designer.py`

Two paths, always landing in the same `FurnitureItem[]` shape:

1. **Deterministic** — `furniture_placer.py`'s existing wall-affinity engine,
   with each `FurnitureSpec`'s width/depth/height resolved from its real
   `CatalogItem` (`furniture_defaults.get_template()`), so the 2D clearance
   math and the 3D mesh always agree on size. This is door-unaware by design
   (the placer only knows the room's own geometry) — `interior_designer.py`
   self-heals by dropping any item that would block a door swing, with a
   warning, so the deterministic path always returns a validator-clean room.
   A second item sharing a wall with an already-placed one (e.g. a chair in
   front of a desk) needs `FurnitureSpec.wall_offset` set — without it, both
   candidate boxes start flush at the same wall position and the second is
   silently rejected as overlapping (Stage 43.20 found this had been
   silently dropping `study`'s chair since it shipped). The clearance check
   itself degrades gracefully rather than hard-rejecting (Stage 43.23) — a
   fixed clearance requirement was silently dropping beds entirely in
   depth-compressed rooms; it now accepts whatever space is actually
   available down to a small floor instead of the item's declared ideal.
   `furniture_defaults.effective_room_type()` also resolves which template a
   room actually uses — a `"bedroom"` room is redirected to the
   `master_bedroom` template (king bed, dressing table) when it's the
   generator's own `bed-master` or named "Master...", since the generator
   never stores a literal `type="master_bedroom"` anywhere (that template
   was unreachable dead code from Stage 43.11 until this fix).
2. **AI** — sends room geometry + door/window positions + a catalog subset to
   the configured Anthropic model; the model returns placements as JSON over
   that fixed catalog (the same pattern published auto-layout research —
   LayoutGPT / Holodeck / OptiScene — converges on). Any failure (no key, bad
   JSON, failed validation) falls back to the deterministic path with a
   warning — the core "AI proposes, deterministic always works" invariant.

## Validation — `core/validation/interior_validator.py`

`validate_room_furniture()` checks bounds, item-item overlap, and door-swing
collision (hard errors) plus window-blocking (advisory warning). Shared by
generation and editing. Edits only reject on a **new** violation the edit
itself introduces — a room that already carries an unrelated pre-existing
issue (e.g. furnished via the whole-project `/generate/from-prompt` flow,
which is also now catalog-aware but doesn't run the self-healing pass) never
becomes permanently un-editable.

## API — `api/routes/interior.py`

```
GET  /catalog                                        # browse/filter (category, style)
GET  /catalog/{id}
POST /projects/{id}/rooms/{room_id}/interior/generate  # {mode, style, prompt}
GET  /projects/{id}/rooms/{room_id}/interior
POST /projects/{id}/rooms/{room_id}/interior/edit       # move | rotate | delete | swap | add | recolor
POST /projects/{id}/interior/generate-all               # {mode, style, overwrite} — every room in one call
```

## Frontend

- **3D** — `features/massing/catalog-furniture.tsx` renders real GLB meshes
  (measured at runtime, scaled to the catalog's true footprint — not just
  trusted from metadata); `massing-viewer.tsx` adds PBR floor/wall materials,
  a CC0 HDRI, physically-based sky tied to the sun-study panel, PCSS soft
  shadows, N8AO ambient occlusion, bloom, physical glass (transmission/IOR),
  a CAD-style reference grid, and an "Enter Room" camera.
- **2D** — `features/plan/floor-plan-svg.tsx`'s `FurnitureSymbol` is
  click-selectable with a highlight outline, synced with the 3D view and the
  right panel, and **freehand-draggable** — pointer events converted to
  plan-space feet via the SVG's own `getScreenCTM()` (so it's robust to
  CSS zoom), snapped to a 0.25 ft grid while dragging, committed via the same
  `interior/edit` `move` action as any other edit (so it's re-validated —
  bounds/overlap/door-swing — and rejected with the room's existing error
  surface if the drop point is invalid). A plain click (no drag distance)
  still selects, matching the panel's click-to-select.
- **Panel** — `components/workspace/interior-studio.tsx`: generate (mode +
  style), per-item rotate/swap/**recolor**/delete, credits link. Recolor
  shows a native color swatch only for items with an `editable` material
  slot; position is edited by dragging on the 2D canvas rather than a panel
  control, since drag is the more natural interaction for placement.

## Exports

- **GLB** — automatic. Catalog furniture renders as real `THREE.Group`
  objects in the scene; `GLTFExporter` (Stage 8.6) walks the whole scene
  graph, so furniture is included with no extra code.
- **DXF** — `core/exports/dxf_exporter.py` draws each `FurnitureItem`'s
  footprint on the `A-FURN` layer (respects `project.show_furniture`).
- **SketchUp / Blender** exporters already read `FurnitureItem` (Phase 26) —
  unaffected by the Phase 43 model additions.

## Expansion (Stage 43.6+)

Bedroom is the 100%-working slice. Stages 43.6–43.21 proved the pattern
generalizes across an entire typical house **and** the café/office
commercial building-kinds the generator already supported before Phase 43
existed — **30 catalog items total**, catalog-backed templates for
`bedroom`, `master_bedroom`, `living`, `seating`, `kitchen`, `kitchenette`,
`dining`, `study`, `foyer`, `balcony`, `storage`, `bathroom`, `restroom`,
`office`, `cafe_seating`, and `cafe_counter`:

| Room | New CC0 items | Reused items | Notes |
|---|---|---|---|
| Living room | sofa, modern coffee table, media console | armchair, side table, bookshelf, plant | — |
| Kitchen | electric stove (cooktop), kitchen sink unit | — | Counters intentionally **not** catalog-linked — they already render from a parametric L-counter (`massing-data.ts`'s `_buildKitchenCounters`, sized to the room); a fixed-size catalog mesh would double-render. Refrigerator has no CC0 source — box fallback. |
| Dining | dining table, dining chair | media console (as sideboard) | Chair-around-table placement (`_chair_boxes_around_table`) made catalog-aware — real (non-square) chair footprint resolved to a conservative square slot using its larger dimension, so the mesh never overhangs its validated box. |
| Study | metal office desk, school chair (as office chair) | bookshelf | — |
| Foyer | classic console table | — | Shoe rack has no CC0 source — box fallback. |
| Master bedroom | king bed frame | wardrobe, nightstands (both) | Dressing table has no CC0 source — box fallback. |
| Balcony | plastic outdoor chair | side table (as outdoor table) | Poly Haven's only outdoor table is a 7×10 ft picnic table — doesn't fit a balcony; reused a small side table instead. |
| Storage | — | bookshelf (as shelving) | Cheapest room — same mesh, different room context. |
| **Bathroom / restroom** | toilet, bathroom sink, bathtub (**Kenney**, not Poly Haven) | — | Poly Haven has no bathroom fixtures at all. "Shower" renders the bathtub mesh — no dedicated shower-stall CC0 model found either; a bath/shower combo is a common real fixture, an honest approximation not a mislabel. `restroom` (WC + basin, no shower) is the distinct smaller template a café/office's public restroom actually uses — Stage 43.24 fixed the generator, which had been typing that room `"bathroom"` and giving it a bathtub it shouldn't have. |
| Office | — | desk + chair (from study), bookshelf, dining table (as meeting table) | The café/office building-kind produced `type="office"` rooms since before Phase 43; had no furniture until Stage 43.20. Repeating desk+chair pairs gated by room area — up to 3 workstations, a meeting table, and a bookshelf for larger open-plan rooms. |
| Café seating | — | dining table + chairs (as bistro table), potted plant | Reuses the dining chair-around-table placement logic directly — a café table is placed exactly like a dining table, sized for 2 chairs instead of 6. |
| Café counter | — | console table (as service counter) | A long low table is a reasonable stand-in for a service/reception counter; no dedicated counter CC0 asset sourced. |

**Remaining honest gaps** (no suitable CC0 model found anywhere checked):
refrigerator, dressing table, shoe rack. These stay on the box fallback —
`catalog_id` is optional by design for exactly this case. Retail and
hospitality room types were deliberately **not** added — unlike office/café,
the generator has no existing building-kind or room type for them anywhere
(floor plan generation, compliance rules, the "Add room" dropdown); adding
them would mean inventing a new building category, a product-scope decision
rather than a furniture-catalog one.

Same recipe for any further room type or to fill a gap once a source turns up:

1. Curate CC0 items in `tools/catalog-pipeline/sources.json` (add
   `"source": "kenney"` if it's not a Poly Haven asset).
2. `npm run build && npm run download-env` in `tools/catalog-pipeline/`.
3. Add matching `FurnitureSpec` entries with `catalog_id` to the room's
   template in `core/architecture/furniture_defaults.py`.
4. Add a 2D `FurnitureSymbol` case in `floor-plan-svg.tsx` for any new item
   `type` that doesn't already have one (most common types — sofa, armchair,
   coffee table, TV unit, bookshelf, side table, plant, ottoman, WC, basin,
   shower, sink — already do).

No new architecture required — catalog resolution, the deterministic
placer, the AI proposer, validation, and the R3F/2D rendering all already
generalize across room types and asset sources.
