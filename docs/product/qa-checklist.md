# Scotch — QA Checklist (Phase 20.1)

Status column: ✅ Pass · ⚠️ Known limitation (documented) · ❌ Fail

---

## 1. Backend health

| Check | Expected | Status |
|-------|----------|--------|
| `GET /health` returns `{"app":"scotch","status":"ok"}` | 200 OK | ✅ |
| `pytest` full suite passes | 384 green, 0 failures | ✅ |
| Server starts with `uvicorn app.main:app --reload --port 8000` | No import errors | ✅ |
| All 16+ routes registered (health, projects, generate, exports, intelligence, cameras, integrations, settings, versions) | Visible in `/docs` | ✅ |

---

## 2. Dashboard

| Check | Expected | Status |
|-------|----------|--------|
| Dashboard loads at `/dashboard` | Projects + Templates sections visible | ✅ |
| Six starter templates shown (2BHK, 3BHK Villa, Studio, Cafe, Office, Duplex) | All cards with name + site size | ✅ |
| "New Project" dialog opens; entering name + clicking Create creates project and redirects to workspace | Project appears in workspace | ✅ |
| Template card "Open in workspace" pre-fills the prompt | Workspace prompt populated | ✅ |
| Projects list updates after create/delete | Live fetch on mount | ✅ |
| Delete project with confirm dialog | Project removed from list | ✅ |
| Backend status card shows green/red | Online when API running | ✅ |
| Offline state: projects list shows graceful empty/error message | Not crashed | ✅ |

---

## 3. Workspace — Generation

| Check | Expected | Status |
|-------|----------|--------|
| Workspace loads at `/workspace?project={id}` with saved project | Correct name, prompt, plan, options | ✅ |
| Workspace loads at `/workspace` (no project) | Empty canvas, empty prompt | ✅ |
| Type a prompt → press "Generate Design" | Floor plan renders in 2D canvas | ✅ |
| Ctrl+Enter generates | Same as button | ✅ |
| Generation mode: Deterministic (no API key) | Works always | ✅ |
| Generation mode: AI (with key) | Works when ANTHROPIC_API_KEY set | ✅ |
| Generation mode: Hybrid | AI with deterministic fallback | ✅ |
| AI mode greyed out without key | Tooltip "Add an API key in Settings" | ✅ |
| Offline fallback (API down) | Shows mock plan + offline notice | ✅ |
| Notice area animates in/out | Smooth transition | ✅ |
| Generated project auto-saves to open project | Reloading shows same plan | ✅ |
| Generation in unsaved workspace | Notice says "not saved" | ✅ |

---

## 4. Workspace — Design Options

| Check | Expected | Status |
|-------|----------|--------|
| "or compare compact · balanced · spacious options" link | Options panel slides in | ✅ |
| Three option cards: compact, balanced, spacious | Mini SVG floor plan on each | ✅ |
| Option card shows score, built area, summary | Data from backend | ✅ |
| Click "Apply" on an option | Active plan updates, "Applied" badge | ✅ |
| Applied option saves to project | Reloads correctly | ✅ |
| Closing options panel | Panel hides | ✅ |

---

## 5. Workspace — 2D Canvas

| Check | Expected | Status |
|-------|----------|--------|
| Floor plan renders with architectural standard elements | Double-line walls, door swings, window symbols | ✅ |
| Room labels with area shown | e.g. "Living Room\n168 ft²" | ✅ |
| Dimension lines with slash ticks | Site boundary dimensions | ✅ |
| North arrow | Orientation-aware | ✅ |
| Click room on canvas → sky blue highlight | Room highlighted | ✅ |
| Click room → inline popover near click (CADAM-style) | Edit popover appears | ✅ |
| Click empty canvas → deselect | Popover closes | ✅ |
| Escape key deselects | Popover closes | ✅ |
| Zoom in/out buttons | +25% / -20% steps | ✅ |
| Fit to view button | Optimal zoom for plan | ✅ |
| Scale chip shows units | "ft · plan" or "m · plan" | ✅ |

---

## 6. Workspace — 3D Massing

| Check | Expected | Status |
|-------|----------|--------|
| "3D Massing" tab → R3F viewer loads | No crash, WebGL renders | ✅ |
| Walls extruded to floor_height | Correct height matches building model | ✅ |
| Roof slab and ground slab | Present as flat planes | ✅ |
| Door glass insets visible | Translucent blue insets | ✅ |
| OrbitControls: drag to rotate, scroll to zoom | Works | ✅ |
| Camera preset dropdown | exterior_quarter, top_ortho, street_eye, living_interior, balcony | ✅ |
| "Export GLTF" button downloads .gltf | File downloads | ✅ |
| 3D massing syncs after parameter edit | useMemo re-runs on project change | ✅ |
| Empty state when no project | "Generate a floor plan first" message | ✅ |

---

## 7. Workspace — Parameter Editing

| Check | Expected | Status |
|-------|----------|--------|
| Parameters panel shows site/building/room params | Grouped correctly | ✅ |
| Edit site width → Apply → plan updates | New width reflected | ✅ |
| Edit floor height → 3D updates | Extrusion height changes | ✅ |
| Out-of-range value (width=0) → 422 rejected | "Edit rejected — a value was out of range" | ✅ |
| Room click → room editor in Selection section | Room name/width/depth editable | ✅ |
| Room editor Apply → regenerate → plan updates | CADAM-style on-canvas edit | ✅ |

---

## 8. Workspace — Room Schedule

| Check | Expected | Status |
|-------|----------|--------|
| Room schedule shows all rooms | Name, size, area per row | ✅ |
| Click row → room highlighted on plan | Sync with canvas | ✅ |
| Built-up area total at bottom | Sum of all room areas | ✅ |

---

## 9. Exports

| Check | Expected | Status |
|-------|----------|--------|
| JSON export → downloads valid ArchitectureProject JSON | Parseable | ✅ |
| SVG export → layered SVG file | Groups: site/rooms/walls/doors/windows/labels/dims | ✅ |
| PNG export → rasterized plan | 2× scale, white background | ✅ |
| DXF export → valid ezdxf file | A-SITE/A-WALL/A-DOOR/A-WINDOW/A-ROOM-TEXT/A-HATCH layers | ✅ |
| SketchUp (.rb) export → Ruby script | Opens in SketchUp; rooms build correctly | ✅ |
| Blender (.py) export → Python script | `ast.parse` valid; runs in Blender Scripting | ✅ |
| Rhino (.py) export → RhinoPython script | `ast.parse` valid; runs in Rhino 7+ Tools>PythonScript | ✅ |
| Sheet SVG export → A3 presentation board | Title block, plan viewport, schedule, legend | ✅ |
| Sheet PDF export → print-ready A3 PDF | Opens in PDF viewer | ✅ |
| Schedule JSON → room schedule with gross+carpet areas | Parseable JSON | ✅ |
| Schedule CSV → room schedule as spreadsheet | Opens in Excel | ✅ |
| Busy spinner during download | Loader2 shown | ✅ |
| Download confirmed in "X downloaded." line | Format name shown | ✅ |
| Exports disabled before generation | Tooltip: "Generate a floor plan to enable exports" | ✅ |

---

## 10. Architecture Intelligence

| Check | Expected | Status |
|-------|----------|--------|
| Intelligence section loads after project saved | Fetches `/projects/{id}/intelligence` | ✅ |
| Area cards: site, built-up, carpet, open | Correct calculations | ✅ |
| Coverage % and floor efficiency % | Derived values | ✅ |
| Spatial checks (room too small, ventilation, etc.) | Sorted by severity | ✅ |
| "N more" expand for long lists | Toggle | ✅ |
| Vastu Shastra toggle | Refetches with `?vastu=true` | ✅ |
| Vastu suggestions shown with direction | Amber state when active | ✅ |

---

## 11. Version History

| Check | Expected | Status |
|-------|----------|--------|
| History section appears in Design Data panel | After first saved project | ✅ |
| First generate creates version entry | change_type=generate, timestamp, thumbnail | ✅ |
| Parameter edit creates version | change_type=regenerate | ✅ |
| Version row shows: badge colour, summary, relative time, room count/area | All fields | ✅ |
| Mini SVG thumbnail per version | Inline SVG of room fills | ✅ |
| Restore → "Restore" button arms (3 s timeout) | Button turns rose-colored | ✅ |
| Restore → "Confirm" → active plan updates | Snapshot restored | ✅ |
| History list refreshes after restore | `historyKey` increments | ✅ |
| Restore appends `restore` version | Never destroys prior history | ✅ |
| Empty state when no versions | "No versions yet" message | ✅ |

---

## 12. Project Persistence

| Check | Expected | Status |
|-------|----------|--------|
| Project created from dashboard persists | Reloading workspace loads same project | ✅ |
| Name rename persists | Reload shows new name | ✅ |
| Generated plan persists | Reloading workspace shows plan | ✅ |
| Exports appear in manifest | Listed in exports panel | ✅ |
| Version sidecars saved to disk | `versions/*.json` files present | ✅ |

---

## 13. Known Limitations (Beta)

| Limitation | Note |
|-----------|------|
| Office prompt uses generic fallback (not a real office layout) | Documented: Phase 5 note |
| `room_id` stability: full regeneration creates new IDs, so diff shows all rooms as added+removed | Documented in version-compare-strategy.md |
| Cloud backend is a stub (`CloudProjectStore` raises `NotImplementedError`) | Expected — Phase 18 is prep only |
| Live plugin testing (SketchUp, Rhino, Revit, Blender) requires the host application installed | Code + docs delivered; manual install needed |
| Pagination: no limit on versions list or project list | Acceptable for beta; cap planned in Phase 20+ |
| No session auth: all data belongs to `local-user` | Expected for local-first MVP |
| Performance: very large projects (20+ rooms) may have slower SVG reflow | Acceptable for typical 2–4BHK range |
