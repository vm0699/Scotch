# Scotch v1.1 — Known Limitations

**Track:** beta · local-first  
**Date:** 2026-06-24

This document lists the intentional constraints and advisory boundaries of the v1.1 release. Each item states the limitation, its reason, and the future path.

---

## Architecture / Structural

**No structural engineering.** Scotch generates architectural layouts and spatial relationships. Beam spans, column sizing, load paths, foundation design, and RC detailing are not computed. Output is a design intent model — a structural consultant must validate before construction.

**Stairs are advisory.** Stair geometry (riser/tread/width) uses standard residential defaults. No code-compliant headroom clearance, handrail detailing, or egress calculations are verified. Requires architect/engineer review.

**Multi-storey alignment is approximate.** Columns and walls are not automatically aligned across floors. The architect must verify structural grid alignment in the parameter editor.

---

## MEP

**MEP is conceptual, not engineering-certified.** Plumbing point placement, pipe routing, and electrical circuit layout are advisory — derived from room-type heuristics and template defaults. No pipe sizing, load calculation, circuit amperage, or code compliance is computed. Every MEP output carries `needs_review: true`.

**Wet-area grouping is advisory only.** The plumbing engine notes when toilets and kitchens are far apart, but never forces room moves. The architect decides.

**No structural/MEP coordination.** Beam locations and MEP routes are not cross-checked for clashes. Clash detection is a future feature.

---

## Tamil Nadu Compliance

**TN advisory, not certified.** All Tamil Nadu rule checks are advisory, derived from the TN Combined Development & Building Rules and internal interpretation. Outputs are flagged `needs_professional_verification: true`. Do not submit approval drawings based solely on Scotch advisory output — consult a licensed architect or DTCP-registered professional.

**Rule sources are ingestion-ready placeholders where official docs were not available.** Rule logic is authored deterministically from publicly available summaries; some clauses may differ from the current gazette. Source metadata fields are ready for official doc ingestion when made available.

**Location granularity is limited.** Panchayat vs. Corporation zone-specific rules (e.g., Chennai Corporation vs. CMDA vs. rural Panchayat) are not yet differentiated. Scotch applies the most common residential interpretation.

---

## BOQ / Cost

**Rates are manual only — no live market pricing.** The rate table is pre-seeded with indicative defaults (INR, Tamil Nadu residential basis, mid-2026). Actual material and labour rates vary by location, contractor, and market. Enter your own rates for any cost estimate intended for a client.

**Quantities are approximate.** Tile wastage uses a fixed 10% default. Cut-tile patterns, grout, adhesive, and other on-site variables are not modelled.

**No structural / civil cost.** Foundation, RCC, steel, and civil works are out of scope in v1.1.

---

## 3D & Rendering

**3D viewer is massing-first, not photo-realistic.** The R3F viewer shows volumes, openings, and basic material zones. It is a design-review aid, not a render.

**Render prompt generation requires an external AI image service.** `RENDER_API_URL` must point to a Stable-Diffusion-compatible endpoint. Without it, the renderer falls back to a massing screenshot.

**Furniture and interior blocks are simple bounding boxes.** No brand-accurate models; no furniture clearance or egress path analysis.

---

## Exports & Plugins

**DXF export targets AutoCAD 2013 (AC1027).** Verified with ezdxf. Complex polylines or very large rooms may render differently in older CAD versions.

**SketchUp plugin requires SketchUp 2021+.** The `.rbz` extension uses the SketchUp Ruby API 2.x. Tested on SketchUp Pro 2022.

**Revit plugin targets Revit 2022–2024.** Revit API version compatibility is not guaranteed for versions outside this range.

**Rhino plugin targets Rhino 7+.** Rhino 6 may work but is untested.

**PDF sheets are A3 landscape at 1:100.** Custom scale / paper size selection is not yet in the UI (can be set via API parameter).

---

## Scan-to-Plan / References

**Extraction is not automated in v1.1.** Upload + scale calibration + opacity overlay is the full feature. Wall detection, OCR label extraction, and AI image-to-plan are documented in the extraction roadmap but not implemented.

**Reference images are stored locally only.** Cloud sync for references requires the cloud/auth upgrade (planned).

---

## Cloud / Multi-user

**Local-first only in v1.1.** All projects, profiles, and references are stored in `services/api/app/data/`. No cloud backup, no multi-device sync, no team collaboration. Google OAuth flow is documented and env-var-ready but not wired.

**Single user only.** The local user ID is fixed at `local-user`. Multiple accounts on the same machine are not supported.

---

## AI / Deterministic

**Deterministic fallback always works.** If `ANTHROPIC_API_KEY` is not set, all generation, MEP, detail, BOQ, and chat commands use rule-based deterministic logic. AI is an optional enhancer layer.

**AI schema repair may miss edge cases.** The AI provider wrapper retries with schema repair on invalid JSON, but complex or contradictory prompts may fall through to the deterministic fallback without an error surface.

---

## Performance

**SVG rendering slows above ~20 rooms.** The 2D floor-plan SVG is DOM-based. Very large plans (30+ rooms, dense MEP overlays, dimension layers) may lag in the browser. A canvas/WebGL renderer is on the roadmap.

**BOQ recomputation is synchronous.** For very large material plans, BOQ recalculation blocks the response briefly. Background job queue is planned.

---

## Professional Responsibility

Scotch is a design-assistance tool. All outputs — spatial layouts, MEP placements, BOQ quantities, compliance advisories, feasibility metrics — require review and sign-off by a licensed architect or engineer before use in construction, approval submissions, or client contracts. The platform does not replace professional judgment.
