# Presentation Sheets Strategy — Scotch × Adobe Suite

> **Phase 12.5 strategy document.**
> Covers Photoshop board templates, InDesign placement workflow, and PDF package strategy for Scotch presentation exports.

---

## 1. What Scotch exports

| Format | File | Use |
|---|---|---|
| Sheet SVG | `presentation_sheet.svg` | Illustrator, browser, further editing |
| Sheet PDF | `presentation_sheet.pdf` | Print-ready, InDesign placement, sharing |
| Floor plan SVG | `floor_plan.svg` | Illustrator / Photoshop smart object |
| Floor plan PNG | `floor_plan.png` | Photoshop layer, mood boards |
| Floor plan DXF | `floor_plan.dxf` | AutoCAD, Revit base drawing |

---

## 2. Illustrator workflow (Sheet SVG)

### 2.1 Open and layer structure

1. Open `presentation_sheet.svg` in Illustrator (File → Open, or drag into AI).
2. Illustrator maps SVG `<g id="...">` elements to **AI layers**:

| SVG id | AI Layer | Contents |
|---|---|---|
| `sheet-border` | Border | Page border, inner rule |
| `title-block` | Header | Dark header bar, project title, north arrow |
| `plan-viewport` | Plan | Floor plan geometry (rooms, walls, doors, windows, labels, dims) |
| `plan-site` | Plan › Site | Site boundary |
| `plan-rooms` | Plan › Rooms | Room fills + wall outlines |
| `plan-doors` | Plan › Doors | Door leafs + swings |
| `plan-windows` | Plan › Windows | Window symbols |
| `plan-labels` | Plan › Labels | Room names + sizes |
| `plan-dims` | Plan › Dims | Dimension lines |
| `schedule` | Right Panel | Room schedule table |
| `legend` | Right Panel | Room type colour legend |
| `notes` | Right Panel | Concept text + notes |
| `footer` | Footer | Project metadata strip |

### 2.2 Typical edits

- **Change fonts**: select all text in a layer → Character panel → change font.
- **Adjust colours**: select room fills → use Recolour Artwork to change palette.
- **Add logo**: place logo file in Header layer above the project title.
- **Replace plan**: export an updated `floor_plan.svg` → File → Place (embedded) on the Plan layer.
- **Export print PDF**: File → Save As → Adobe PDF → use PDF/X-1a preset for print.

---

## 3. Photoshop workflow (board / mood board)

### 3.1 Board template setup

Recommended canvas: **420mm × 297mm @ 150 ppi** (A3, print resolution).

Layer stack (top to bottom):

```
Group: OVERLAY
  Text: Project title (large display type)
  Text: Architect / firm
Group: PLAN
  Smart Object: floor_plan.png (from Scotch export)
Group: RENDERS / IMAGES
  [Render images, site photos, material swatches]
Group: BACKGROUND
  Fill: #f5f4f0 (warm off-white)
```

### 3.2 Placing the Scotch floor plan

1. Export `floor_plan.png` from Scotch (high-res, 2× scale, ~1200px/ft).
2. In Photoshop: File → Place Embedded → select `floor_plan.png`.
3. Resize to fit the plan viewport on the board.
4. Double-click the Smart Object to edit (scale/crop) without losing quality.
5. Apply a slight drop shadow (Blending Options → Drop Shadow: opacity 15%, distance 4px, blur 8px).

### 3.3 Material swatch overlay

Create a row of material swatches at the bottom of the board:
- Floor material swatch (tile, wood, etc.) with a label
- Wall finish swatch
- Furniture / fabric swatch
Source these from the renderer output or manually.

### 3.4 Render overlay

For photorealistic presentations:
1. Export from Blender (using the Scotch `.py` script → render the scene).
2. Place the render as a Smart Object in the RENDERS group.
3. Scale to 40–50% of the board width.
4. Add a caption below with the render viewpoint label.

---

## 4. InDesign workflow (multi-page document)

### 4.1 Document setup

- New document: A3, landscape, facing pages off.
- Margins: 8mm all sides.
- Bleed: 3mm.

### 4.2 Master page

Master page A ("Sheet"):
- Place `presentation_sheet.pdf` as a placed PDF (File → Place → choose page 1).
- Lock the placed PDF layer so it can't be accidentally moved.
- Add a text frame on the master for the page number (`<#>`).

### 4.3 Page structure

| Page | Content |
|---|---|
| 1 | Cover: project title, hero render, firm logo |
| 2 | Floor plan sheet (`presentation_sheet.pdf` placed) |
| 3 | 3D massing views (Blender renders, arranged in a 2×2 grid) |
| 4 | Material & finish schedule (table from room schedule data) |
| 5 | Site plan / context map |
| 6 | Notes, area statement, design narrative |

### 4.4 Updating the floor plan

When the Scotch design changes:
1. Re-export `presentation_sheet.pdf` from Scotch.
2. In InDesign: Edit → Update All Links — the placed PDF updates in place.
3. Check for text reflow or layout shifts in surrounding frames.

---

## 5. PDF package strategy

### 5.1 Single-sheet PDF

Scotch exports `presentation_sheet.pdf` as a standalone A3 PDF at 96 dpi equivalent. For print:
- Open in Acrobat Pro → Print Production → Output Preview to verify colour space.
- Print as PDF/X-1a for professional printing, or PDF/X-4 for digital proofing.

### 5.2 Multi-sheet PDF package

To assemble a complete submission package (for planning applications, client reviews):
1. Export all Scotch sheets: `presentation_sheet.pdf`, floor plan PDFs per floor.
2. In Acrobat Pro: File → Combine → Merge Files → add all PDFs in order.
3. Add bookmarks: "Floor Plan", "3D Massing", "Room Schedule", "Notes".
4. Set document metadata (File → Properties → Description).
5. Flatten transparency before sending to print.

### 5.3 Automated packaging (Phase 18+)

A future Phase 18 server-side route:

```
POST /projects/{id}/exports/pdf_package
→ returns a ZIP containing:
   floor_plan_sheet.pdf
   floor_plan.dxf
   floor_plan.svg
   floor_plan.png
   massing.gltf
   scotch_project.json
   README.txt
```

This collapses the multi-step export workflow into one click.

---

## 6. Print specifications

| Setting | Value |
|---|---|
| Resolution | 300 dpi for print; 72–96 dpi for screen |
| Colour mode | CMYK for print; RGB for screen/digital |
| Bleed | 3mm (add in Illustrator/InDesign before print) |
| Font embedding | Embed all fonts (PDF export setting) |
| Preferred PDF standard | PDF/X-1a (print), PDF/A-2b (archival) |

---

## 7. Phase roadmap

| Phase | Feature |
|---|---|
| Phase 12 (now) | SVG + PDF sheet export from Scotch |
| Phase 17 | Render-ready Blender automation → produces render images for placement |
| Phase 18 | PDF package endpoint (multi-export in one click) |
| Phase 20 | Final sheet polish: custom logo, firm stamp, revision blocks |
