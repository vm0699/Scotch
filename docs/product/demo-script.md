# Scotch — Demo Script (Phase 20.6)

**Duration:** ~8 minutes  
**Format:** Live walkthrough or recorded screen share  
**Audience:** Architects, architecture students, potential investors / partners  
**Fallback:** If the backend is offline, the workspace shows a pre-rendered sample — still usable for UI demo.

---

## Setup (before demo)

1. Start both servers:
   ```powershell
   # Terminal 1
   cd services/api
   .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000

   # Terminal 2
   cd apps/web
   npm run dev
   ```
2. Open http://localhost:3000 in a clean browser window (close other tabs).
3. Optionally set `ANTHROPIC_API_KEY` in `.env` for the AI mode segment.
4. Pre-create a project named "Demo" from the dashboard so saves are visible.

---

## Script

### 1. Landing → Dashboard (30 s)

> *"Scotch is a text-to-design platform for architecture — you describe a building, we generate an editable floor plan in seconds."*

- Show http://localhost:3000 landing page.
- Click **Dashboard** in the top bar.
- Point out: six starter templates (2BHK Apartment, 3BHK Villa, Studio, Cafe, Office, Duplex).
- Point out: "New Project" button and backend status indicator (green = API online).

---

### 2. New Project (30 s)

- Click **New Project**.
- Name it `"2BHK Client Brief"`.
- Click **Create** → workspace opens.

---

### 3. Text-to-Plan Generation (1 min)

> *"The left panel is the brief. Type a natural-language description of any building."*

- Clear the prompt and type:
  ```
  Design a 2BHK apartment on a 30×50 ft east-facing site with living room, open kitchen, 2 bedrooms (one master with attached bath), common bathroom, balcony, and covered parking.
  ```
- Press **Generate Design** (or Ctrl+Enter).
- After ~1–2 s: the 2D floor plan renders.
- Point out: room labels with areas, dimension lines, door swings, window symbols, north arrow.

> *"No AI key needed — the deterministic engine runs fully locally. With an API key you unlock AI mode for richer layouts."*

---

### 4. CADAM-Style Editing (1.5 min)

> *"This isn't a static image — every element is editable, just like in CADAM."*

**On-canvas edit:**
- Click the **Living Room** on the plan → inline popover appears near the click.
- Change width from `14` → `16` ft → **Apply**.
- Plan redraws with the new width and door/window positions updated.

**Panel edit:**
- In the right **Design Data** panel, scroll to **Parameters**.
- Change **Floor height** from `10` → `12` ft.
- Click **Apply** → 3D will reflect new height.

> *"Every edit is validated, saved to the project, and versioned automatically."*

---

### 5. Design Options (45 s)

- Click **"or compare compact · balanced · spacious options"** below the Generate button.
- Three option cards appear with mini floor plans, scores, and built areas.
- Click **Apply** on **Spacious** → active plan updates.
- Close the options panel.

---

### 6. 3D Massing (45 s)

- Click the **3D Massing** tab in the center panel.
- The 3D viewer loads: walls extruded to floor height, roof slab, door glass insets.
- Drag to orbit. Scroll to zoom.
- Open the camera preset dropdown → select **Exterior quarter view** → camera jumps.

---

### 7. Exports (1 min)

> *"Scotch exports directly into every professional tool architects use."*

In the **Exports** section of the right panel:

| Export | What to show |
|--------|-------------|
| **DXF** | Downloads `floor_plan.dxf` — point out "open in AutoCAD" |
| **SVG** | Downloads `floor_plan.svg` — "Illustrator layers preserved" |
| **SketchUp (.rb)** | "Run in SketchUp Scripting console — hollow rooms, materials" |
| **Blender (.py)** | "Lights, cameras, EEVEE preset, render-ready" |
| **Rhino (.py)** | "RhinoPython — BooleanDifference walls, Grasshopper-ready" |
| **Sheet SVG** | "A3 presentation board with title block and schedule" |

---

### 8. Architecture Intelligence (30 s)

- Scroll to **Intelligence** in the right panel.
- Point out: Site area, Built-up area, Carpet area, Coverage %, Efficiency %.
- Point out: Spatial quality checks (any warnings in amber/red).
- Toggle **Vastu Shastra** → Vastu suggestions appear.

---

### 9. Version History + Restore (45 s)

- Scroll to **History** in the right panel.
- Show the version entries generated during the demo:
  - "Generate — 6 rooms, 1180 ft²" (colour badge: violet)
  - "Regenerate — 6 rooms, 1240 ft²" (blue — the living room resize)
- Click **Restore** on the first version → button arms (rose).
- Click **Confirm** → plan reverts to the original layout.
- A new "restore" entry appears at the top of the history.

> *"History is append-only — you never lose a version."*

---

### 10. Integration Roadmap (30 s)

> *"Scotch already speaks every major architecture tool."*

Show the docs folder or verbally reference:

- **AutoCAD / CAD** — DXF with layers, hatches, dimension strings.
- **SketchUp** — installable `.rbz` extension; one-click JSON import.
- **Rhino / Grasshopper** — RhinoPython export; GH parameter strategy.
- **Blender** — full scene automation (lights, cameras, EEVEE preset).
- **Revit** — C# add-in with JSON import + round-trip sync.
- **Lumion / D5 / Enscape / V-Ray** — documented per-engine workflows.
- **Illustrator / InDesign** — A3 sheet SVG with named layers; PDF export.

---

## Fallback notes

| Issue | Fallback |
|-------|---------|
| Backend offline | Workspace shows built-in 2BHK sample; UI fully demoable |
| Generation slow | Switch to Deterministic mode (<1 s) |
| Export error | Show the file in `services/api/app/data/…/exports/` directly |
| 3D viewer WebGL error | Keep demo on 2D tab; mention R3F + Three.js stack |
| Version history empty | Generate → edit params → show 2 entries |

---

## Key talking points

- **No AI key required** — deterministic engine runs fully locally.
- **Validated model** — every generation passes the schema validator before rendering.
- **Local-first, cloud-ready** — all storage goes through a `ProjectStore` ABC; a cloud backend is a drop-in.
- **Professional exports** — every major format, not a PDF dump.
- **Version history** — architecture has iteration; Scotch tracks every change.
- **Plugin ecosystem** — SketchUp extension, Revit C# add-in, Rhino/GH strategy all shipped.
