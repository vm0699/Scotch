# Scan-to-Plan Extraction Roadmap

**Phase 39 first pass:** upload + manual scale calibration + SVG overlay. This document captures
the full extraction path for when AI/CV capabilities are added (Phase 39.5 roadmap, future arc).

---

## What ships in Phase 39 (done)

| Capability | Status |
|---|---|
| Upload image/PDF reference file per project | ✅ |
| Store binary + metadata sidecar | ✅ |
| Manual scale calibration (2-point + known distance) | ✅ |
| Coordinate transform: pixel ↔ project-space feet | ✅ |
| Opacity-controlled SVG overlay on 2D plan | ✅ |
| Lock/unlock and trace mode UI | ✅ |
| ExtractedEntity model (ready for AI output) | ✅ |
| REST API: upload / list / get / calibrate / delete | ✅ |

---

## Extraction pipeline (future arc)

### Stage A — Vector PDF extraction

**Goal:** parse PDF architectural plans exported from AutoCAD, SketchUp, Revit.

**Approach:**
1. Use `pdfminer.six` or `pypdf` to extract vector paths, polylines, and text blocks from the PDF.
2. Group paths by color/layer — walls are typically thick black polylines, text is room labels.
3. Match extracted polylines against the `ReferenceAsset` calibration scale to get real-world coords.
4. Emit `ExtractedEntity` records: `entity_type="wall"`, `entity_type="label"`, `entity_type="dimension"`.

**Libraries:** `pdfminer.six`, `pypdf`, `shapely` for geometry cleanup.

**Known issues:**
- Rasterized PDFs (scanned, not vector) yield no extractable paths → fall through to raster path.
- Layer names vary by CAD software; heuristic grouping is fragile on complex plans.
- Requires calibration to convert PDF internal units (pt) to project feet.

---

### Stage B — Raster / scanned plan wall detection

**Goal:** detect wall lines from a scanned floor plan or hand sketch.

**Approach (OpenCV-based, no AI key needed):**
1. Convert image to grayscale + threshold → binary.
2. `cv2.HoughLinesP` or morphological thinning to detect line segments.
3. Cluster collinear segments → candidate wall lines.
4. Filter by length (min wall = 2 ft in calibrated coords).
5. Emit `ExtractedEntity(entity_type="wall", geometry={x1, y1, x2, y2})`.

**Libraries:** `opencv-python-headless`, `numpy`.

**Known issues:**
- Hand sketches: variable line quality, furniture shadows, annotations all become false walls.
- Needs post-processing to close gaps, deduplicate, and merge collinear segments.
- Heavy reliance on good calibration — a 5 % scale error compounds badly for large plans.

**Accuracy:** expect 60–75 % wall coverage on clean scans; 30–50 % on photos of hand sketches.
Always needs human review (`needs_review=True`, `confidence` output alongside each entity).

---

### Stage C — OCR room labels and dimensions

**Goal:** read room names (BEDROOM, KITCHEN) and dimension annotations from the plan.

**Approach:**
1. Use `pytesseract` (Tesseract OCR) on the image or on cropped text regions from the PDF.
2. Map detected text positions to calibrated project coords.
3. Classify: if near a bounding box → `entity_type="label"`; if near a line with arrows → `entity_type="dimension"`.
4. Emit `ExtractedEntity(entity_type="label", label="Kitchen", geometry={cx, cy})`.

**Libraries:** `pytesseract`, `Pillow`.

**Known issues:**
- Architectural fonts (condensed, rotated text) have lower OCR accuracy.
- Dimension annotations in architectural plans often use non-standard syntax (e.g. `3'6"`, `1050mm`).
- Post-processing needs: unit normalisation (mm → ft if calibrated in ft), rotation correction.

---

### Stage D — AI image-to-plan (Magicplan-style)

**Goal:** fully automated room polygon + wall + opening extraction using a CV/AI model.

**Approach:**
1. Use a trained semantic segmentation model (e.g. CubiCasa5K, Residential Floor Plan Detection)
   to classify each pixel as: wall / room / door / window / stair / furniture / void.
2. Post-process the segmentation mask into polygon room boundaries.
3. Detect openings (doors/windows) from the door-symbol mask.
4. Map everything through scale calibration to project feet.
5. Offer a "confirm extraction" step where the architect reviews + adjusts before importing.

**Model options:**
- **CubiCasa5K** (Apache 2.0): trained on 5000 Finnish floor plan images; good for residential.
- **Custom fine-tuned SegFormer/DeepLab**: requires GPU + training data labelled in Scotch's coordinate system.
- **OpenAI Vision / Claude (multimodal)**: send image to model, ask for JSON room list with approximate dimensions. Cheapest to deploy, but accuracy varies.

**Libraries:** `torch`, `torchvision`, `huggingface_hub`, `transformers` (for SegFormer).

**Infrastructure:**
- GPU inference endpoint (Modal, RunPod, or self-hosted) OR cloud vision API key.
- Model weights bundled or downloaded on first use (CubiCasa5K is ~200 MB).
- Async job queue for large PDFs (multiple pages); notify via webhook or polling.

**Accuracy target:** 80 %+ room coverage on clean residential plans (CubiCasa5K benchmark).

---

## Import → ArchitectureProject flow

Once entities are extracted and reviewed, an import step merges them into the live project:

```
ExtractedEntity (wall) → ArchitectureProject.walls[]
ExtractedEntity (room) → ArchitectureProject.rooms[] (with inferred type from label)
ExtractedEntity (opening) → ArchitectureProject.doors[] / .windows[]
ExtractedEntity (stair) → ArchitectureProject.stairs[]
```

Invariants:
- Run `validate_project()` after import — reject invalid geometry.
- All imported rooms flagged with `source: "reference_import"` warning.
- Version snapshot created before import (so the architect can revert).
- Imported entities linked back via `ExtractedEntity.linked_project_object_id`.

---

## External data / dependencies needed

| Need | Source | Blocking? |
|---|---|---|
| OpenCV | `opencv-python-headless` (pip) | No — dev dep, add when needed |
| Tesseract | System package + `pytesseract` | No — optional |
| CubiCasa5K weights | HuggingFace Hub (Apache 2.0) | No — download on demand |
| GPU endpoint | Modal / RunPod / self-host | No — only for Stage D |
| Anthropic multimodal | `ANTHROPIC_API_KEY` | No — optional |

**Net: nothing external blocks Phase 39's first pass.** The extraction pipeline here is a future
enhancement — documented so the path is clear and no decisions are baked in prematurely.

---

## Privacy note

Reference images may contain client site photos, existing plan drawings, or proprietary CAD files.
They are stored locally (`references/files/` under the project directory) and never sent to any
external service unless the user explicitly triggers an AI-assisted extraction with a cloud key.
The `mime_type` check at upload rejects executables; all paths are sanitized before writing.
