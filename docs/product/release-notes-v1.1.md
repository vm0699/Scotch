# Scotch v1.1 Release Notes

**Release date:** 2026-06-24  
**Track:** beta · local-first  
**Previous version:** v1.0-beta (Phases 0–28)

---

## What's new in v1.1

### MEP Production Layer Studio (Phase 29)
- Plumbing, electrical, lighting, and split-AC points generated from room types automatically.
- Wet-area wet-zone analysis with advisory routing (conceptual, not engineering-certified).
- Layer toggle overlay on the 2D canvas (Arch / Plumbing / Electrical / Lighting / AC / Dims).
- Prompt commands: "add plumbing and electrical", "move sink point", "add two sockets in bedroom".
- Named-layer SVG/DXF exports: `P-PIPE`, `P-FIXTURE`, `E-LIGHT`, `E-SWITCH`, `E-SOCKET`, `M-AC`.
- User override points preserved on plan regeneration.

### Detail Drawing Studio (Phase 30)
- Structured detail templates: toilet, kitchen, door/window, wall-section, tile-layout, plumbing, electrical.
- Detail drawings stored as geometry primitives (lines/arcs/text/dims) — editable and exportable.
- Stale-status detection: detail marked stale when linked source object changes.
- Prompt: "generate toilet detail for bath-1", "create wall section at this wall".
- Detail SVG/DXF exports; detail sheet bundle.

### Material / Tile / BOQ / Cost Studio (Phase 31)
- Room finish editor: floor tile, wall finish, paint, ceiling per room.
- Quantity engine: tile count (+wastage), skirting length, paint area, fixture counts — all traceable to source objects.
- Manual editable rate table (INR / sqft basis); missing-rate warnings surfaced prominently.
- BOQ CSV, JSON, PDF summary exports.
- Prompt: "calculate tile quantity", "set tile rate to 80 per sqft", "export BOQ".

### Tamil Nadu Advisory Pack (Phase 32)
- Setback, FSI/FAR, parking, ventilation, stair, rainwater-harvesting advisories above existing NBC.
- Every rule carries source metadata, confidence label, and `needs_professional_verification` flag.
- Missing-input prompts: road width, site dimensions, location all explicitly requested before computing.
- Layered above NBC (NBC checks unchanged).

### Architect-Twin Personalization (Phase 33)
- Local user preference profile: units, default location, drawing style, room-size preferences, material bias.
- Per-project client brief: family size, lifestyle, budget, style, Vastu, parking, special needs.
- Generation fuses prompt + brief + profile: same prompt → different output by brief.
- Design reasoning panel: which profile/brief values influenced the output.

### Client Change Management (Phase 34)
- Client change request sidecar: request text, status, priority, cost/drawing/MEP/BOQ impact.
- Affected-item engine: computes impact across rooms, walls, dims, MEP, BOQ, compliance, details, exports.
- Change Inbox UI: approve/apply, reject, restore/revert, before/after summary.
- Prompt: "client asked to add attached toilet", "show impact of this change".
- Exports marked stale after design change.

### 2D-to-3D Production (Phase 35)
- 3D viewer maps walls/floors/openings/stairs/furniture/kitchen counters/sanitary fixtures from validated model.
- Interior 3D blocks: bed, sofa, dining, wardrobe, kitchen counter, WC, basin, shower, AC unit.
- Material mapping: `material_plan` → 3D colors + Blender export materials.
- Context-aware render prompt generator: includes material, style, budget, location/climate, camera preset.

### Prompt-First Toolchain (Phase 36)
- All production tools reachable from the chat prompt panel without touching the parameter editor.
- Tool-call badges show exactly which tool ran, what changed, and affected items.
- Undo/revert links inline in chat.
- Full demo flow: generate → MEP → detail → tiles → TN advisory → export → client change → affected items — all prompt-driven.

### Cloud / Auth Seam (Phase 37)
- Local twin profile persists across sessions.
- Google OAuth flow documented and env-var-ready (not wired in local mode).
- Account panel: profile display, sign-in-ready placeholder, cloud-mode indicator.

### External MCP Expansion (Phase 38)
- Scotch tools exposed as an MCP server for Claude Desktop / Cursor / external agents.
- Every external call: auth, validate, version, return warnings — deterministic fallback preserved.
- Revit + Rhino sync bridge docs updated for production-grade round-trip.

### Reference / Scan-to-Plan (Phase 39)
- Upload image or PDF reference (hand sketch, site photo, existing plan scan).
- 2-point scale calibration: mark two known points → compute px/ft.
- Reference overlay on 2D plan canvas: opacity control, lock/unlock, blend mode.
- Extraction roadmap documented (wall detection, OCR, vector-PDF, AI image-to-plan — future).

### Feasibility / Yield Analysis (Phase 40)
- Site feasibility metrics: site area, usable footprint, coverage %, buildable area, FSI, parking estimate.
- Development option comparison: compact / balanced / spacious / rental-friendly.
- Missing-input warnings; assumptions displayed.
- Prompt: "maximize built-up area", "make rental-friendly option", "compare 2BHK vs 3BHK".

### Review & QA Workflows (Phase 41)
- QA checklist: 10 automated checks (dims reviewed, rooms inside site, openings scheduled, MEP/details/BOQ reviewed, TN advisories addressed, exports regenerated).
- Completion % bar with color coding (≥80% green, ≥50% amber, <50% red).
- Issue tracker: create, resolve, delete review comments attached to any project object.
- Review report export (text/JSON).

### Release Hardening (Phase 42)
- 5 demo fixture projects: 2BHK TN House, 3BHK Villa, Studio Apartment, Small Cafe, Duplex House.
- Fixtures generate live via `GET /fixtures/{id}` — always current, no stale project files.
- Feedback button: Bug report / Feature request / General feedback stored locally.
- Version badge in dashboard footer: Scotch v1.1 beta · local.

---

## Test suite

- Backend: **1,170 pytest tests**, 0 failures.
- Frontend: TypeScript strict-clean (`tsc --noEmit` zero errors).

---

## Upgrade notes

No migration needed. All new fields on `ArchitectureProject` default to empty — existing saved projects load without modification.
