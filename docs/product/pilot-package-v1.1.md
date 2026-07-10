# Scotch v1.1 Pilot Package

**For:** Beta architects / design students  
**Date:** 2026-06-24  
**Track:** Local-first beta

This guide is everything a pilot user needs: setup, the core demo flow, how to give feedback, and known gotchas.

---

## 1. Prerequisites

| Requirement | Version |
|---|---|
| Node.js | 18+ |
| Python | 3.11+ |
| Git | any recent |
| OS | macOS / Windows 11 / Ubuntu 22+ |

Optional (AI-enhanced prompts): `ANTHROPIC_API_KEY` in `.env`.

---

## 2. Setup (5 minutes)

```bash
# 1. Clone
git clone https://github.com/your-org/scotch.git
cd scotch

# 2. Copy env
cp .env.example .env
# Edit .env — add ANTHROPIC_API_KEY if you have one (optional)

# 3. Backend
cd services/api
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Frontend (new terminal)
cd apps/web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

Health check: `GET http://localhost:8000/health` → `{"app":"scotch","status":"ok"}`.

---

## 3. Core demo flow (20 steps, ~15 minutes)

This is the primary demo. Every step works offline (no API key needed).

### Generate a 2BHK Tamil Nadu house

**Step 1.** Open the dashboard → click **New Project**.

**Step 2.** In the prompt panel, type:
```
2BHK house, 30x50 ft, east facing, Tamil Nadu, family of 4, budget-friendly
```
Click **Generate**.

**Step 3.** The 2D floor plan appears. Observe:
- Double-line walls, door swings, window symbols.
- Room labels with areas (sqft).
- North arrow. Dimension lines.

**Step 4.** Click a room in the plan → it highlights in the right panel → edit its name or dimensions inline.

**Step 5.** Switch to the **3D** tab — massing with openings, interior furniture blocks, material zones.

---

### Add MEP layers

**Step 6.** In the chat panel, type:
```
add plumbing and electrical layers
```
The MEP overlay appears on the 2D plan. Toggle layers: Plumbing / Electrical / Lighting / AC.

**Step 7.** Click a plumbing point → inspect its room link and confidence in the properties panel.

**Step 8.** Type:
```
add two sockets in the master bedroom
```
Two socket points appear. Confidence label shows "user override — preserved on regen."

---

### Generate a toilet detail

**Step 9.** Type:
```
generate toilet detail for bath-1
```
The Detail Studio tab opens — a dimensioned toilet layout linked to bath-1.

**Step 10.** Edit a dimension value inline → detail updates, version created.

---

### Set tile and BOQ

**Step 11.** Open the **BOQ** tab. Room finish editor shows floor tile / wall / paint per room.

**Step 12.** Type:
```
set living room floor tile to 600x600, rate 90 per sqft
```
Tile quantity and cost update immediately.

**Step 13.** Click **Export BOQ** → downloads a CSV with quantities, rates, amounts, and source object IDs.

---

### Check Tamil Nadu compliance

**Step 14.** Open the **Compliance** tab. TN Advisory Pack shows:
- Setback advisory (road width prompt if missing).
- FSI/FAR advisory.
- Parking advisory.
- Each rule: source metadata + confidence + `Needs professional verification`.

**Step 15.** Type:
```
check Tamil Nadu setback for road width 20 ft
```
Advisory result updates with specific setback requirement.

---

### Client change request

**Step 16.** Type:
```
client asked to add an attached toilet to the master bedroom
```
A change request appears in the **Change Inbox** — status: Pending.

**Step 17.** Click **Apply** → change applied, version created. The **Affected Items** panel lists:
plan (room added), MEP (plumbing point added), BOQ (tile area recalculated), exports (marked stale).

---

### Feasibility

**Step 18.** Open the **Feasibility** panel in the right sidebar.
Metrics: site area, usable footprint, coverage %, buildable area, FSI, parking estimate.
Development options: compact / balanced / spacious.

---

### Export

**Step 19.** Open the **Exports** tab. Choose:
- **SVG** (full-color, all layers).
- **DXF** (named layers for AutoCAD).
- **SketchUp JSON** (import with the `.rbz` plugin).

Click **Download**.

---

### Review & QA

**Step 20.** Open **Review & QA** in the right panel.
- **QA Checklist**: 10 automated checks — completion % bar.
- **Issues**: add a review comment ("Verify staircase width with structural").
- Click **Download** → review report text file.

---

## 4. Load a demo fixture

On the dashboard, the **Templates** section shows 5 built-in fixtures:

| Fixture | Description |
|---|---|
| 2BHK TN House | Standard Tamil Nadu 30×50 family home |
| 3BHK Villa | Larger plot, modern style |
| Studio Apartment | Compact urban unit |
| Small Cafe | Commercial layout, open plan |
| Duplex House | Two-floor split-level |

Click any fixture → generates a complete project instantly. Good for showing the platform without typing a prompt.

---

## 5. Keyboard shortcuts

| Action | Shortcut |
|---|---|
| Generate | `Ctrl+Enter` (in prompt box) |
| Toggle north arrow | `N` (on canvas) |
| Toggle dimensions | `D` (on canvas) |
| Toggle furniture | `F` (on canvas) |
| Open chat | `Ctrl+/` |
| Submit feedback | `Ctrl+Enter` (in feedback dialog) |

---

## 6. Giving feedback

Click the **Feedback** button at the bottom of the left sidebar on the dashboard.

Choose:
- **Bug report** — describe what happened and what you expected.
- **Feature request** — describe the workflow you want.
- **General feedback** — anything else.

Feedback is stored locally (`localStorage["scotch_feedback"]`). To export all feedback entries:
```js
// In browser DevTools console:
JSON.parse(localStorage.getItem("scotch_feedback") || "[]")
```
Copy and paste into an email or issue report.

---

## 7. Known limitations (summary)

Full list: [known-limitations-v1.1.md](known-limitations-v1.1.md)

- MEP is conceptual / advisory — not engineering-certified.
- TN compliance is advisory — must be reviewed by a licensed architect.
- BOQ rates are manual — enter your own for any client-facing estimate.
- No structural engineering, no clash detection.
- Local-first only — no cloud backup or multi-device sync in this beta.
- Extraction from reference scans is manual (upload + scale + overlay only).

---

## 8. Filing a bug

Use the in-app feedback button, or open an issue at:  
`https://github.com/your-org/scotch/issues`

Include:
1. Prompt you typed.
2. What you expected.
3. What happened (screenshot or export if relevant).
4. Browser console errors (if UI bug).
5. `GET http://localhost:8000/health` response.

---

## 9. Contacts

Primary contact: [writetovignesh.m@gmail.com](mailto:writetovignesh.m@gmail.com)
