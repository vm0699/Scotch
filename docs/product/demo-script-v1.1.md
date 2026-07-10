# Scotch — Demo Script v1.1 (Prompt-to-Production)

**Duration:** ~12–15 minutes
**Format:** Live walkthrough or recorded screen share
**Audience:** Architects, architecture students, small studios, potential pilot users / partners
**Theme:** *Prompt-to-production* — type plain English, get editable working-drawing outputs
(dimensions, furniture, MEP, details, BOQ, Tamil Nadu advisories), then manage client changes and
push to 3D / render / professional tools.

> **Status (2026-06-23):** Phases 29–36 complete. Prompts 1–20 all run deterministically with no API
> key. The chat panel's full toolchain (15 tools, keyword-intent router, tool-call badges) shipped in
> Phase 36. Phases 37–42 (cloud/auth, MCP expansion, scan-to-plan, feasibility, review, release
> hardening) remain. The v1.0-beta demo ([demo-script.md](demo-script.md)) covers everything through
> Phase 27 (generation, editing, 3D, exports, intelligence, history).

**Fallback (offline / no AI key):** every step works deterministically. With no `ANTHROPIC_API_KEY`,
prompts route through the keyword intent parser — phrase commands plainly (the script already does).
If the backend is offline, the workspace shows a pre-rendered sample for UI-only demoing. If WebGL
fails, stay in the 2D working-drawing view (which is the point of the demo anyway).

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
2. Open http://localhost:3000 in a clean browser window.
3. Optional: set `ANTHROPIC_API_KEY` in `.env` for smoother natural-language prompting (not required).
4. Pre-create a project named **"TN Demo"** from the dashboard so saves are visible.

---

## The litmus prompt (the whole pitch in one line)

> *"Create a 2BHK villa in Tamil Nadu on a 30x50 ft east-facing plot. Make it budget friendly, include
> parking, furniture, plumbing, electrical, lighting, AC points, working drawing dimensions, tile
> quantity, toilet detail, kitchen detail, and check Tamil Nadu advisories."*

The demo unpacks this into discrete, visible, editable steps.

---

## Script (20 steps)

### 1. Open Scotch
- Land on http://localhost:3000 → **Dashboard**. Point out templates + backend-online indicator.

### 2. Create a 2BHK Tamil Nadu project
- **New Project** → name "TN Demo" → open the workspace.

### 3. Enter / prompt the client brief *(Phase 33)*
- In the brief panel (or via prompt): *budget-friendly, family of 4, east-facing 30×50 ft site,
  parking, good ventilation.*
- > *"Output adapts to the brief — a budget family build is not the same as a premium studio."*

### 4. Generate the working drawing
- Prompt: *"Create a 2BHK villa in Tamil Nadu on a 30×50 ft east-facing plot, budget friendly, with
  parking."*
- Plan renders with real-scale dimensions *(Phase 29.0)*, double-line walls, room labels + areas.

### 5. Show dimensions, furniture, doors/windows, schedule
- Toggle dimension layers *(29.0)*; show furniture blocks; open the door/window schedule.

### 6. Prompt: add MEP layers *(Phase 29)*
- *"Add plumbing, electrical, lighting, and AC layers."*
- Tool-call badges show `generate_mep` ×4.

### 7. Show MEP Studio + editable 2D service layers *(Phase 29)*
- Switch to **MEP Studio**. Toggle plumbing/electrical/lighting/AC. Click a sink point → properties.
- > *"It places services like an architect — plumbing in wet areas, AC on the right wall — and flags
  > what needs review."* Show confidence / needs_review badges.
- Prompt: *"shift AC to the opposite wall"* → point moves; override preserved.

### 8. Prompt: generate details *(Phase 30)*
- *"Generate toilet detail and kitchen detail."*

### 9. Show Detail Studio *(Phase 30)*
- Open **Detail Studio**. Show the dimensioned toilet detail linked to `bath-1`. Note the stale flag
  appears if the bathroom changes later.

### 10. Prompt: calculate materials & cost *(Phase 31)*
- *"Calculate tiles and main material cost."*

### 11. Show BOQ Studio with editable rates *(Phase 31)*
- Open **BOQ Studio**. Show tile quantity (with wastage), category totals.
- Prompt: *"change tile size to 600×600"* and *"set tile rate to 80 per sqft"* → quantities + cost update.
- Point out missing-rate warnings + assumptions list.

### 12. Prompt: check Tamil Nadu advisories *(Phase 32)*
- *"Check Tamil Nadu advisories."*

### 13. Show source-backed advisory panel *(Phase 32)*
- Show per-rule advisory result, **source + version date + confidence**, missing-input prompts, and the
  **"needs professional verification"** flag. NBC checks still present.

### 14. Prompt: client change *(Phase 34)*
- *"Client wants attached toilet added to the bedroom."*

### 15. Show affected items *(Phase 34)*
- Affected list: **plan, MEP, BOQ, details, exports**. Each impact is explicit before applying.

### 16. Apply change + create version *(Phase 34)*
- Apply → a new version snapshot is created automatically; exports flagged stale.

### 17. Show before/after summary *(Phase 34)*
- Open the change record → before/after summary + revision metadata. Mention one-click revert.

### 18. Export production outputs *(Phases 29–31)*
- Export **SVG · DXF · PDF sheet · CSV BOQ · JSON**. Show clean named layers (`P-PIPE`, `E-LIGHT`,
  `M-AC`, dimension + furniture layers).

### 19. Open 3D preview / render prompt *(Phase 35)*
- Switch to 3D — walls/stairs/furniture/fixtures derived from the *same* validated 2D model.
- Show the **context-aware render prompt** (material/style/budget/location/camera) → render (or massing
  capture fallback). *"3D and renders come from your 2D work — not a random image."*

### 20. Show export / plugin path
- Point to SketchUp / Revit / Rhino / Blender export + round-trip sync. *"Scotch is the validated model
  under your toolchain — every tool is a client of it."*

---

## Closing line

> *"You typed a brief in plain English and walked out with dimensioned working drawings, MEP layers,
> details, a BOQ, Tamil Nadu advisories, a tracked client change, and render-ready 3D — all editable,
> all from one source of truth. That's prompt-to-production."*

---

## Demo checklist

- [ ] Backend online (green indicator); `GET /health` ok.
- [ ] "TN Demo" project pre-created.
- [ ] Dimension/MEP/furniture layer toggles working.
- [ ] At least one detail generated and visible.
- [ ] BOQ recomputes live on a rate/size change.
- [ ] TN advisory shows a source + verification flag.
- [ ] Client change lists affected items + creates a version.
- [ ] Exports download with named layers.
- [ ] 3D/render prompt embeds project context.
- [ ] Fallbacks rehearsed (no key → keyword prompts; offline → sample; no WebGL → 2D).
