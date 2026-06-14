# SketchUp Workflow — Scotch Integration Guide

Import Scotch architecture designs into SketchUp as fully editable, grouped,
tagged 3D models. Two paths are available: a one-shot Ruby script (zero install)
and a loadable extension (recommended for repeated use).

---

## Option A — One-Shot Ruby Script (zero install)

1. **Export** the floor plan from Scotch:
   - Open your project in the Workspace.
   - In the right panel → Exports → **3D Software** → click **SketchUp (.rb)**.
   - Save `floor_plan.rb` to your desktop.

2. **Run in SketchUp:**
   - Open SketchUp (2021 or later).
   - Go to **Extensions › Ruby Console**.
   - Drag-and-drop `floor_plan.rb` onto the console, or paste its contents and
     press **Enter**.
   - A success messagebox confirms the import.

3. **What you get:**
   - Ground slab, hollow room walls, door/window voids, roof slab.
   - Materials by room type (living, kitchen, bedroom, bathroom…).
   - Tags: `S-SITE`, `S-ROOMS`, `S-ROOF`, `S-LABELS`, `S-OPENINGS`.
   - Room groups named `<Room Name> [room_id]` in the Outliner.
   - 3D text labels at each room centroid (toggle via `S-LABELS` tag).
   - Camera reset to isometric view.

---

## Option B — Scotch Importer Extension (recommended)

The extension adds a persistent menu item and toolbar button; no Ruby Console
needed after the initial install.

### Install

1. **Download the extension** from Scotch:
   - `GET http://localhost:8000/integrations/sketchup/extension`
   - Save the file as `scotch_importer.rbz`.
   
   Or use the Scotch API directly:
   ```
   curl http://localhost:8000/integrations/sketchup/extension \
        -o scotch_importer.rbz
   ```

2. **Install in SketchUp:**
   - Open SketchUp (2021+).
   - Go to **Window › Extension Manager**.
   - Click **Install Extension**.
   - Select `scotch_importer.rbz`.
   - Restart SketchUp when prompted.
   - Enable **Scotch Importer** in the Extension Manager if not auto-enabled.

   **Manual install (alternative):** copy `scotch_importer.rb` and the
   `scotch/` folder to your SketchUp Plugins directory:
   - macOS: `~/Library/Application Support/SketchUp <version>/SketchUp/Plugins/`
   - Windows: `%APPDATA%\SketchUp\SketchUp <version>\SketchUp\Plugins\`

### Import a design

1. **Export** a `project.json` from Scotch (Exports → **JSON**).
2. In SketchUp, go to **Extensions › Scotch › Import Design…**
   — or click the **Scotch** toolbar button.
3. In the file picker, select your `project.json`.
4. The extension validates the file, builds the 3D model, and shows a
   success dialog.

### What the extension builds

| Element | Tag | Details |
|---|---|---|
| Ground slab | `S-SITE` | Scotch_Ground material, 0.5 ft thick |
| Room walls | `S-ROOMS` | Hollow washer technique, per-type materials |
| Door voids | `S-OPENINGS` | Full-height, cut through wall |
| Window voids | `S-OPENINGS` | Sill 2.5 ft, height 4 ft, glass material |
| Room labels | `S-LABELS` | 3D text at room centroid, name + area |
| Roof slab | `S-ROOF` | Scotch_Roof material, 0.5 ft thick |

Room groups are named `<Room Name> [room_id]` in the Outliner for easy
identification and selection.

---

## Editing after import

- **Tags panel** (View › Tags): toggle `S-ROOF` to hide the roof and work on
  interiors; toggle `S-LABELS` to show/hide room text.
- **Outliner** (Window › Outliner): find rooms by id or name; double-click a
  group to enter edit mode.
- **Push/Pull tool**: adjust wall heights, slab thickness, or room volumes.
- **Paint Bucket**: reassign materials; Scotch materials are pre-loaded.
- **Move tool**: reposition room groups (useful for split-level schemes).
- **Extensions › Solid Inspector²** (recommended plugin): fix any non-manifold
  geometry introduced by opening voids.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `require 'json'` error | Update Ruby (SketchUp 2019+ ships with json gem). |
| "Missing required keys" messagebox | Re-export a fresh `project.json` from Scotch. |
| Door voids not cut cleanly | Run Solid Inspector²; or manually pushpull the opening face. |
| Labels overlap on small rooms | Toggle `S-LABELS` off; use the Outliner for room IDs instead. |
| Extension not visible in menu | Window › Extension Manager → ensure Scotch Importer is checked. |
| Wrong units in SketchUp | The script sets feet automatically; if units look wrong, go to Window › Model Info › Units and set to Architectural. |

---

## Version matrix

| Scotch | SketchUp | Ruby API | Status |
|---|---|---|---|
| Phase 15.1+ | 2021 + | SketchUp Ruby API 2.0 | ✅ Supported |
| Phase 11.2  | 2019 + | SketchUp Ruby API 2.0 | ✅ One-shot script only |
| Phase 11.2  | 2018 – | Older Ruby API | ⚠️ Tags are called Layers; rename `scotch_tag` calls |

---

## Future sync (roadmap note)

A live-sync workflow (Scotch → SketchUp ↔ round-trip edits) is planned for a
post-Phase 20 release. The current extension is one-directional (Scotch → SU).
The `room_id` embedded in each group name is the hook for future round-trip
identification.

*Generated by Scotch — Phase 15.5*
