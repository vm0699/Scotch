# Scotch — Documentation Index

Scotch is an AI-native architecture design platform: text-to-design for architecture.  
**Status: v1.0-beta — Phases 0–20 complete.**

## Product

| Document | Purpose |
|----------|---------|
| [product/roadmap.md](product/roadmap.md) | **Live status tracker** — Phases 0–20 with stage-level detail |
| [product/brief.md](product/brief.md) | Full product brief: vision, pipeline, tool targets |
| [product/prd.md](product/prd.md) | Locked MVP requirements (Phase 0 output) |
| [product/questionnaire.md](product/questionnaire.md) | Phase 0 Q&A — decisions of record |
| [product/implementation-plan-phases-15-20.md](product/implementation-plan-phases-15-20.md) | Detailed stage build plan for Phases 15–20 |
| [product/qa-checklist.md](product/qa-checklist.md) | Full QA flow checklist — all features |
| [product/demo-script.md](product/demo-script.md) | 8-minute live demo script |
| [product/version-compare-strategy.md](product/version-compare-strategy.md) | Version diff model + future compare UI |

## Architecture

| Document | Purpose |
|----------|---------|
| [architecture/auth-strategy.md](architecture/auth-strategy.md) | Google OAuth / JWT plan, `get_current_user_id()` seam |
| [architecture/database-strategy.md](architecture/database-strategy.md) | Postgres/Mongo trade-off, schema design |
| [architecture/cloud-storage-strategy.md](architecture/cloud-storage-strategy.md) | S3 / Supabase object layout |
| [architecture/cloud-api-readiness.md](architecture/cloud-api-readiness.md) | 16-route audit, pagination, ownership model |

## Integrations

| Document | Covers |
|----------|--------|
| [integrations/sketchup-workflow.md](integrations/sketchup-workflow.md) | One-shot `.rb` export + `.rbz` extension install + use |
| [integrations/revit-addin-strategy.md](integrations/revit-addin-strategy.md) | C# add-in architecture, manifest, External Command |
| [integrations/revit-mapping.md](integrations/revit-mapping.md) | Field-level mapping, wall dedup, FamilyFinder |
| [integrations/rhino-strategy.md](integrations/rhino-strategy.md) | RhinoPython script structure, unit conversion |
| [integrations/rhino-grasshopper-strategy.md](integrations/rhino-grasshopper-strategy.md) | GH parameter strategy, Scotch Sync cluster, plugins |
| [integrations/rendering-workflows.md](integrations/rendering-workflows.md) | Blender, Lumion, D5, Enscape, V-Ray workflows |
| [integrations/presentation-sheets-strategy.md](integrations/presentation-sheets-strategy.md) | Illustrator SVG, InDesign, PDF/X-1a |

## Phase Status

| Phase | Name | Status |
|-------|------|--------|
| 0 | Product Understanding & Plan Lock | ✅ Done |
| 1 | Local Working Skeleton MVP | ✅ Done |
| 2 | CADAM-Like UI Shell MVP | ✅ Done |
| 3 | Universal Architecture Data Model MVP | ✅ Done |
| 4 | Local Project Storage MVP | ✅ Done |
| 5 | Deterministic Text-to-Floorplan MVP | ✅ Done |
| 6 | Editable Parameters & Regeneration MVP | ✅ Done |
| 7 | Export MVP | ✅ Done |
| 8 | 3D Massing MVP | ✅ Done |
| 9 | AI Provider Integration MVP | ✅ Done |
| 10 | Design Options MVP | ✅ Done |
| 11 | Software Export Adapters MVP | ✅ Done |
| 12 | Presentation Sheet MVP | ✅ Done |
| 13 | Architecture Intelligence MVP | ✅ Done |
| 14 | Revit Plugin MVP | ✅ Done |
| 15 | SketchUp Plugin MVP | ✅ Done |
| 16 | Rhino / Grasshopper MVP | ✅ Done |
| 17 | Rendering Workflow MVP | ✅ Done |
| 18 | Cloud & Account MVP (preparation) | ✅ Done |
| 19 | Versioning & History MVP | ✅ Done |
| 20 | Product Completion & QA MVP | ✅ Done |
