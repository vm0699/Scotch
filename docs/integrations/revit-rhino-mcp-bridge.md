# Scotch — Revit + Rhino MCP Bridge Expansion

*Phase 38 · Updated 2026-06-22*

This document extends the Phase 14 Revit mapping (`revit-mapping.md`) and Phase 16 Rhino strategy (`rhino-grasshopper-strategy.md`) with the full MCP bridge approach, conflict handling, and validation-result display.

---

## Overview

Both bridges follow the same pattern:

```
Scotch backend ──GET /projects/{id}/sync──► Plugin (Revit/Rhino)
                                              │ user edits geometry
Plugin ──POST /projects/{id}/sync──────────► Scotch backend (validate + merge)
                                              │ returns SyncDiff + warnings
                                              ▼
                                         Scotch MCP (get_sync_contract / push_sync_update)
                                              │ external agents read the merged model
```

The MCP server is an alternative control surface to the REST API — it exposes the same sync logic via `get_sync_contract` and `push_sync_update`.

---

## Sync contract

`GET /projects/{id}/sync` returns a **SyncContract**:

```json
{
  "project_id": "proj-abc",
  "version_ts": "2026-06-22T09:00:00Z",
  "rooms": [
    {
      "id": "bed-master",
      "name": "Master Bedroom",
      "type": "master_bedroom",
      "x": 0, "y": 0,
      "width": 13, "depth": 12,
      "level": 0,
      "flags": {}
    }
  ],
  "walls": [...],
  "openings": [...]
}
```

Plugins call this to seed their local geometry and detect staleness.

---

## Revit MCP bridge

### Pull flow (Scotch → Revit)

```csharp
// In SyncCommand.cs — existing pull
var contract = ScotchClient.GetSyncContract(projectId);
ElementMapper.Import(doc, contract.Rooms, contract.Walls, contract.Openings);
```

**Via MCP** (from an external agent):
```
get_sync_contract("proj-abc")
```
→ returns the SyncContract; agent can then instruct Revit via the Revit API or summarize changes.

### Push flow (Revit → Scotch)

1. `SyncCommand.cs` collects updated room bounding boxes from `FilteredElementCollector`.
2. Converts to `SyncPayload { rooms: [...], source: "revit" }`.
3. `POST /projects/{id}/sync` → backend merges, validates, auto-snapshots.

**Conflict handling:**

| Conflict type | Resolution |
|---|---|
| Room renamed in Revit | `SyncDiff.updated` includes name change; Scotch wins on next pull unless user confirms |
| Room deleted in Revit | Flagged in `SyncDiff.flagged` — not auto-deleted (destructive); user must confirm in Change Inbox |
| Dimension out of range | Validator returns 422; `SyncDiff.conflicts` lists the violation |
| New room added in Revit | `SyncDiff.added`; auto-merged if type can be inferred from name |
| Floor height mismatch | `SyncDiff.flagged`; displayed as warning in Revit result dialog |

**Validation-result display in Revit:**

```csharp
// In SyncCommand.cs — show validation diff
var diff = scotchClient.PushSync(projectId, payload);
var msg = new StringBuilder();
msg.AppendLine($"✓ {diff.Updated.Count} rooms updated");
if (diff.Conflicts.Any())
    msg.AppendLine($"⚠ {diff.Conflicts.Count} conflicts — review in Scotch Change Inbox");
if (diff.Flagged.Any())
    msg.AppendLine($"ℹ {diff.Flagged.Count} items flagged for review");
TaskDialog.Show("Scotch Sync", msg.ToString());
```

---

## Rhino MCP bridge

### Pull flow (Scotch → Rhino)

The existing Rhino export (`/projects/{id}/exports/rhino`) generates a RhinoPython script. For live sync, the `SyncContract` is used instead:

```python
# In Rhino scripting console (RhinoPython)
import urllib.request, json, rhinoscriptsyntax as rs

response = urllib.request.urlopen("http://localhost:8000/projects/proj-abc/sync")
contract = json.loads(response.read())
for room in contract["rooms"]:
    # Create/update Rhino brep from room bounds
    rs.AddBox(compute_corners(room))
    rs.ObjectName(guid, f"Scotch_{room['type']}_{room['id']}")
```

### Push flow (Rhino → Scotch)

```python
# Collect current Rhino rooms and push
import urllib.request, json

rooms_data = []
for obj in rs.AllObjects():
    name = rs.ObjectName(obj)
    if name and name.startswith("Scotch_"):
        bb = rs.BoundingBox(obj)
        rooms_data.append({
            "id": extract_id(name),
            "x": bb[0][0] / SCALE, "y": bb[0][1] / SCALE,
            "width": (bb[1][0] - bb[0][0]) / SCALE,
            "depth": (bb[3][1] - bb[0][1]) / SCALE,
        })

payload = json.dumps({"rooms": rooms_data, "source": "rhino"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/projects/proj-abc/sync",
    data=payload,
    method="POST",
    headers={"Content-Type": "application/json"},
)
result = json.loads(urllib.request.urlopen(req).read())
print(f"Sync: {len(result['updated'])} updated, {len(result['conflicts'])} conflicts")
```

### Conflict handling in Rhino

| Conflict | Rhino display |
|---|---|
| Room below minimum dimension | `print("⚠ Room too small: …")` in console |
| Room outside site boundary | Console warning + object color change to red |
| Unrecognised room type | Scotch infers type from name suffix; falls back to `storage` |
| Version timestamp mismatch | Console prompt: "Scotch has a newer version — pull first?" |

### Validation-result display pattern (Rhino)

```python
diff = result  # from push
lines = [f"Scotch Sync Result"]
lines.append(f"  Added:    {len(diff.get('added', []))} rooms")
lines.append(f"  Updated:  {len(diff.get('updated', []))} rooms")
if diff.get("conflicts"):
    lines.append(f"  CONFLICTS ({len(diff['conflicts'])}):")
    for c in diff["conflicts"]:
        lines.append(f"    - {c['room_id']}: {c['reason']}")
print("\n".join(lines))
```

---

## MCP bridge (via external agents)

An external agent (Claude Desktop, Cursor) can orchestrate the full Revit/Rhino round-trip:

```
1. get_sync_contract("proj-abc")
   → returns current rooms/walls/openings

2. [User / agent modifies geometry in Revit or Rhino]

3. push_sync_update("proj-abc", {
     "rooms": [...updated rooms...],
     "source": "revit"
   })
   → returns SyncDiff + merged project

4. show_affected_items("proj-abc", change_id)
   → shows what drawing/MEP/BOQ items are stale
```

This replaces manual REST calls and enables agent-driven round-trip sync.

---

## Stale-export tracking

After a successful push sync, the backend automatically marks exports stale:

- `revision_meta.exports_stale = true`
- `revision_meta.stale_reason = "Sync from {source}"`

The Change Inbox in the Scotch UI shows this banner, and the Export panel badges exports with "stale — regenerate".

---

## Phase 38 additions to existing plugin code

### Revit (`plugins/revit/Services/ScotchClient.cs`) — additions

```csharp
// New: pull SyncContract via /sync route
public SyncContract GetSyncContract(string projectId) { ... }

// New: display validation diff in Revit task dialog
public static string FormatDiff(SyncDiff diff) { ... }
```

### Rhino (`integrations/rhino/facade_prototype.py`) — additions

```python
# New: push utility function
def push_to_scotch(project_id, rooms_data, source="rhino"):
    """Push updated room bounds to Scotch and return the SyncDiff."""
    ...
```

---

## Grasshopper live-param bridge

See [rhino-grasshopper-strategy.md](rhino-grasshopper-strategy.md) for the full GH data flow. Phase 38 adds:

- `SyncContract` as the GH input source (instead of full ArchitectureProject JSON)
- `push_sync_update` MCP call from GH Python component after parameter changes
- Conflict-result panel component in GH canvas (using GH `Message` balloon)
