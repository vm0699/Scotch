# Scotch — Service Architecture & External Dependencies

> The founder's "service architecture accuracy" question, answered: *what is genuinely external (data,
> APIs, services) — beyond development effort — and what ships deterministically inside the repo.*
>
> **Headline:** nothing external is **blocking**. The only real external *content* dependency is the
> Tamil Nadu regulation source material (handled via ingestion-ready placeholders + verification flags).
> AI keys (intent/reasoning) and render-image keys (photoreal renders) are **optional enhancers** —
> deterministic fallback always works. Everything else is in-repo deterministic templates or dev
> libraries already in the project.

Companion: [phase-28-founder-requirements-map.md](../product/phase-28-founder-requirements-map.md) ·
[roadmap-phase-28-plus.md](../product/roadmap-phase-28-plus.md).

---

## Architecture principle

Scotch is **deterministic-first**. Every production module (MEP, details, BOQ, compliance, reasoning)
has a deterministic engine driven by in-repo JSON templates and rule logic that runs with **no network,
no API key, no external service**. External services only *enhance* — better natural-language intent,
nicer reasoning prose, photoreal renders. If an external service is absent or fails, the deterministic
path produces a valid, validated `ArchitectureProject`.

This means: a developer can clone, run, and exercise the entire v1.1 demo offline. External procurement
is about *quality and reach*, never *basic function*.

---

## Dependency inventory

### 1. AI provider (LLM) — **optional enhancer**
- **Used for:** advanced prompt understanding, schema repair, design reasoning, detail adaptation,
  client-facing explanations, the agentic chat loop.
- **External?** Yes — a hosted LLM API. **Optional.**
- **What's needed:** `ANTHROPIC_API_KEY` (Claude Sonnet/Opus) **or** an OpenAI-compatible endpoint +
  key. Already abstracted behind `services/api/app/core/ai/provider.py` and the chat route's
  `_run_anthropic_loop` / `_run_deterministic_fallback` split.
- **Fallback:** keyword-based deterministic intent parsing + rule-based generation (already in place).
- **Blocking?** **No.**
- **Cost note:** per-token API cost only when a key is set and AI/hybrid mode is chosen.

### 2. Tamil Nadu regulations — **the one real external content dependency**
- **Used for:** source-backed TN advisories, rule Q&A, missing-input prompts (Phase 32).
- **External?** Yes — but it's **content (documents), not an API.**
- **What's needed:** Tamil Nadu Combined Development & Building Rules (TNCDBR) + amendments, as PDF/text,
  plus per-rule metadata: source name, source URL/path, version date, confidence. Optionally local
  authority (CMDA / DTCP / local body) byelaw PDFs.
- **Fallback / first pass:** ship an **ingestion-ready structure** (`data/regulations/tamil_nadu/
  {sources,rules,amendments}.json`) with **placeholder rule values + real metadata fields**, and flag
  every output `needs_professional_verification`. When the founder provides the actual documents, real
  values replace placeholders without code changes.
- **Blocking?** **No** — placeholders + advisory framing keep the feature usable and honest.
- **Action for founder:** provide TNCDBR + amendment PDFs/links if available (see open question 1).

### 3. MEP templates — **in-repo, no external service**
- **Used for:** plumbing/electrical/lighting/AC symbol defs, fixture assumptions, placement templates,
  conceptual route logic (Phase 29).
- **External?** No. Authored as JSON under `services/api/app/data/mep_templates/`.
- **What's needed:** internal authoring only; mark conceptual / `needs_review`. Expert review is a
  later optional enhancement.
- **Blocking?** **No.**

### 4. Detail templates — **in-repo, no external service**
- **Used for:** toilet/kitchen/door-window/wall-section/plumbing/electrical/tile-layout detail
  generation (Phase 30).
- **External?** No. JSON under `services/api/app/data/detail_templates/` with geometry primitives,
  annotation/dimension rules, source notes, confidence, `needs_review`.
- **What's needed:** internal authoring; expert-reviewed construction-ready details are a later option.
- **Blocking?** **No.**

### 5. Material & rate data — **in-repo + manual, no live vendor API**
- **Used for:** tile quantities, material estimates, BOQ/cost (Phase 31).
- **External?** Not in first pass. Manual editable rates; default categories; editable tile sizes.
- **What's needed:** default category list in-repo; **manual rate entry** by the user; CSV import is a
  documented placeholder. Live vendor pricing/stock/quotation is explicitly **future-ready, not first
  pass**.
- **Blocking?** **No.**
- **Locale assumption:** INR (₹), per-sqft rates, feet-first with metric toggle (open question 2).

### 6. Export libraries — **dev dependencies already present**
- **Used for:** SVG, DXF, PDF, CSV, IFC, GLTF/OBJ, plugin sync.
- **External?** Build-time Python/JS packages, **already in the project**: `ezdxf` (DXF), `reportlab`
  (PDF), `Pillow` (PNG), `ifcopenshell` (IFC); SVG/CSV/JSON are hand-written; GLTF via three.js
  `GLTFExporter`.
- **What's needed:** **reuse before adding** any new dependency. New formats (mep_svg, detail_pdf,
  boq_csv) extend existing exporters.
- **Blocking?** **No.**

### 7. Auth / cloud services — **external later, local-first now**
- **Used for:** architect-twin memory across devices, multi-user, hosted storage (Phases 37+).
- **External?** Later — Google OAuth, a database (Postgres), object storage (S3/Supabase).
- **What's needed now:** **nothing** — local profile sidecar store + the existing `get_current_user_id`
  seam + `CloudProjectStore` stub. OAuth env vars + flow are *documented* in Phase 37, not wired this arc.
- **Blocking?** **No.**

### 8. Render image AI — **optional enhancer (Phase 35)**
- **Used for:** photoreal exterior/interior renders inside Scotch.
- **External?** Yes — a Stable-Diffusion-compatible img2img endpoint/key. **Optional.**
- **What's needed:** an SD-compatible API key/endpoint for photoreal output.
- **Fallback:** the existing deterministic **massing-capture** path returns the R3F screenshot — never
  a hard failure. Render prompts are still generated with full project context regardless.
- **Blocking?** **No.**

### 9. Scan-to-plan extraction — **external/AI later (Phase 39)**
- **Used for:** turning sketches/PDFs/photos into project references/geometry.
- **External?** Later — wall-detection / OCR / vector-PDF parsing / image-to-plan AI.
- **What's needed now:** **nothing** — first pass is upload + **manual** scale calibration + overlay.
  Extraction is a documented roadmap.
- **Blocking?** **No.**

---

## Summary table

| # | Dependency | External? | Optional? | What's needed | Blocking? | Phase |
|---|---|---|---|---|---|---|
| 1 | AI provider (LLM) | API | Optional | `ANTHROPIC_API_KEY` or OpenAI-compatible key | No | cross-cutting |
| 2 | Tamil Nadu regulations | Content | Needed for real values | TNCDBR + amendments (PDF/text) + source metadata | No (placeholders) | 32 |
| 3 | MEP templates | In-repo | — | internal JSON authoring | No | 29 |
| 4 | Detail templates | In-repo | — | internal JSON authoring | No | 30 |
| 5 | Material & rate data | In-repo + manual | — | manual rates; CSV import later | No | 31 |
| 6 | Export libraries | Dev deps (present) | — | reuse `ezdxf`/`reportlab`/`Pillow`/`ifcopenshell` | No | 29–31 |
| 7 | Auth / cloud | External later | Later | Google OAuth + DB + object storage | No | 37 |
| 8 | Render image AI | API | Optional | SD-compatible img2img key | No | 35 |
| 9 | Scan-to-plan extraction | External/AI later | Later | OCR / vector-PDF / image-to-plan | No | 39 |

---

## Environment variables (documented; none required to run)

| Var | Purpose | Required? | Default behavior if unset |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Claude for AI/hybrid generation + chat | No | Deterministic generation + keyword chat |
| `OPENAI_API_KEY` (or compatible base URL) | OpenAI-compatible provider | No | Same deterministic fallback |
| `SCOTCH_STORAGE_BACKEND` | `local` (default) / cloud | No | `local` filesystem store |
| `SCOTCH_AI_MODE` | `deterministic` / `ai` / `hybrid` | No | `deterministic` |
| `SCOTCH_RENDER_API_KEY` / endpoint (P35) | SD-compatible render | No | Massing-capture fallback |
| Google OAuth client id/secret (P37) | Cloud sign-in | No (later) | Local-user mode |

---

## What this means for the founder

1. **You can build and demo the entire v1.1 prompt-to-production flow offline**, with no API keys and
   no external service contracts. AI keys make prompting smarter; they are not required.
2. **The only thing worth procuring early is the Tamil Nadu rule source material.** Without it, Phase 32
   still ships — as an honest advisory layer with placeholders and "needs professional verification"
   flags. With it, the same structure carries real, citable values.
3. **No new paid services are needed for MEP, details, BOQ, working drawings, exports, or 3D.** Those
   are deterministic templates and libraries already in the repo.
4. **Cloud/auth and render-image AI are deliberately deferred** behind seams that already exist, so they
   slot in later without re-architecture.
