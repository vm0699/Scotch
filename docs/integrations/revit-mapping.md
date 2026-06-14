# Scotch → Revit Mapping Guide

This document covers exactly how Scotch `ArchitectureProject` entities map to Revit elements when the **Scotch Revit Add-in** runs an import.

---

## 1. Coordinate System

| Scotch | Revit |
|--------|-------|
| X — west → east (plan) | X — same direction |
| Y — north → south (plan, 0 = entrance/top) | Y — same direction |
| Z — not used (2D plan) | Z — elevation in decimal feet |
| Units: **feet** (default) or **meters** | Internal: decimal feet (all Revit 2022+ DB API) |

`CoordinateConverter` converts at the boundary:

```csharp
_scale = units == "meters" ? 3.28084 : 1.0;
public double Ft(double scotchValue) => scotchValue * _scale;
```

All geometry written to Revit is always in decimal feet, regardless of the Scotch project unit.

---

## 2. Element Creation Order

Revit has strict hosting and dependency rules. Elements are created in this order inside a single `Transaction`:

| Step | Scotch source | Revit element | Notes |
|------|--------------|---------------|-------|
| 1 | `building.floors` | `Level` | One per floor; Ground Floor at Z=0 |
| 2 | — (find-or-create) | `WallType` ("Scotch Wall 6\"") | Duplicates first basic wall type |
| 3 | — (find-or-create) | `FloorType` ("Scotch Floor 6\"") | Duplicates first floor type |
| 4 | `rooms[].x/y/width/depth` | `Wall` | 4 walls per room bbox; shared segments deduplicated |
| 5 | `rooms[].x/y/width/depth` | `Floor` | One slab per room from CurveLoop |
| 6 | `rooms[].x/y/width/depth` | `Room` | Placed at centroid UV on its level |
| 7 | `doors[]` | `FamilyInstance` (door) | Hosted on resolved wall from WallResolver |
| 8 | `windows[]` | `FamilyInstance` (window) | Same as doors; sill at +2.5 ft above floor |

---

## 3. Scotch Entity → Revit Parameter Mapping

### 3.1 Project

| Scotch field | Revit equivalent |
|---|---|
| `project.name` | Used in Transaction name |
| `project.units` | Used by `CoordinateConverter._scale` |
| `project.building.floor_height` | Level spacing (Z = i × floorHeight) |
| `project.building.floors` | Number of Levels created |

### 3.2 Rooms

| Scotch field | Revit |
|---|---|
| `room.id` | `Room` shared parameter `ScotchId` |
| `room.name` | `Room.Name` |
| `room.type` | Not mapped (Scotch type → Revit has no equivalent built-in) |
| `room.x`, `room.y` | Room bbox origin → `UV centroid` for placement |
| `room.width`, `room.depth` | Room bbox dimensions → floor CurveLoop |
| `room.level` | Index into `levelMap` → `Level` |

Room centroid formula:
```csharp
UV centroid = new UV(Ft(room.X + room.Width / 2), Ft(room.Y + room.Depth / 2));
```

### 3.3 Walls

Walls are synthesized from each room's 4 sides — Scotch does not store explicit wall segments as primary input (it has an optional `walls[]` array which the Ruby and Python scripts use; the Revit add-in derives them from room bboxes for maximum compatibility).

| Scotch side | Wall endpoints (in plan feet) |
|---|---|
| `north` | `(x, y) → (x+w, y)` |
| `south` | `(x, y+d) → (x+w, y+d)` |
| `west` | `(x, y) → (x, y+d)` |
| `east` | `(x+w, y) → (x+w, y+d)` |

**Deduplication**: shared wall between adjacent rooms is identified by a canonical segment key:
```csharp
// Ordered so A→B and B→A produce the same key
string key = $"{minPt.X:F4},{minPt.Y:F4};{maxPt.X:F4},{maxPt.Y:F4}";
```
The second room that matches the key reuses the existing `ElementId` rather than creating a duplicate wall.

### 3.4 Doors

| Scotch field | Revit |
|---|---|
| `door.room_id` | Used to look up host room bbox |
| `door.wall` | `north/south/east/west` → which room wall hosts the door |
| `door.offset` | Distance from room corner to left edge of door (plan ft) |
| `door.width` | Used to find `FamilySymbol` by size (±0.5 ft tolerance) |

Insert point:
```
centre = door.offset + door.width / 2
north wall: (room.x + centre, room.y, elevation)
south wall: (room.x + centre, room.y + room.depth, elevation)
west wall:  (room.x, room.y + centre, elevation)
east wall:  (room.x + room.width, room.y + centre, elevation)
```

### 3.5 Windows

Same as doors but:
- Uses `OST_Windows` category for `FamilyFinder`
- Sill height = `elevation + 2.5 ft` (hardcoded default; adjust via Revit type parameter after import)

---

## 4. Wall Deduplication — Detail

```
Room A bbox:  x=0, y=0, w=15, d=12  → east wall: (15,0)→(15,12)
Room B bbox:  x=15, y=0, w=12, d=12 → west wall: (15,0)→(15,12)  ← same segment!
```

After Room A creates the east wall, the segment key `"15.0000,0.0000;15.0000,12.0000"` is stored in `segmentIndex`. When Room B's west wall is processed, the key matches — `RegisterShared(roomB.Id, "west", existingId)` is called so the door/window resolver can still find it.

---

## 5. FamilyFinder — Size Matching

`FamilyFinder` tries the following built-in parameters in order to read door/window width:

1. `BuiltInParameter.DOOR_WIDTH`
2. `BuiltInParameter.CASEWORK_WIDTH`
3. `BuiltInParameter.FURNITURE_WIDTH`
4. `BuiltInParameter.GENERIC_WIDTH`
5. Shared/type parameter named `"Width"`

If the best match is within ±0.5 ft (6 inches) of the requested width it is chosen; otherwise the first available active symbol is used as a fallback. If no symbols at all are loaded the door/window is skipped and counted in `ImportResult.Skipped`.

---

## 6. ScotchId Shared Parameter (Round-Trip)

To support sync back from Revit, the add-in writes the Scotch `room.id` to a Revit shared parameter named `ScotchId` on each `Room` element.

### Setup Instructions

1. In Revit, open **Manage → Shared Parameters**.
2. Create a new shared parameter file (or open an existing one).
3. Create a group `Scotch` and add a `Text` parameter named `ScotchId`.
4. In **Manage → Project Parameters**, bind `ScotchId` to the **Rooms** category (instance parameter).

If the parameter is not loaded, `SetScotchId()` is a silent no-op — the import still runs, but `SyncCommand` will generate a `revit-{elementId}` placeholder ID instead of the original Scotch ID.

---

## 7. SyncCommand — Revit → Scotch Data Flow

The `SyncCommand` reads placed Revit rooms and PATCHes the Scotch backend:

```
FilteredElementCollector → Room[]
  └─ ScotchId shared param → Scotch room.id (or placeholder)
  └─ BoundingBoxXYZ       → x, y, width, depth (converted back to Scotch units)
  └─ Level index           → room.level
  └─ Room.Name             → room.name
  └─ NormalizeRoomType()   → room.type (name-based heuristic)

→ PATCH /projects/{id}  { rooms: [...] }
```

**What syncs back**: room names, positions, dimensions, floor assignment.  
**What does not sync**: walls (derived from rooms on re-import), doors, windows, materials.

For a full round-trip after geometry changes, re-export from Scotch and re-import.

---

## 8. Build & Installation

```
# Prerequisites
Visual Studio 2022 (or dotnet build)
Revit 2024 installed at C:\Program Files\Autodesk\Revit 2024\

# Build
dotnet build plugins/revit/ScotchRevit.csproj -c Release

# Install
copy ScotchRevit.dll    %APPDATA%\Autodesk\Revit\Addins\2024\
copy ScotchRevit.addin  %APPDATA%\Autodesk\Revit\Addins\2024\
```

`REVIT_PATH` env var overrides the default Revit install location for the `RevitAPI.dll` reference.

---

## 9. Known Limitations

| Limitation | Workaround |
|---|---|
| Walls are 6" generic — no wall type variety | Duplicate `Scotch Wall 6"` type and adjust compound structure post-import |
| Window sill height is hardcoded at 2.5 ft | Adjust via Revit instance parameter after import |
| Room type is not mapped to a Revit parameter | Use `room.name` to identify type; map manually if needed |
| Multi-floor projects require all levels to exist before rooms | The add-in creates them automatically; do not pre-create levels with the same names |
| Doors/windows skipped if no family symbols loaded | Load a door/window family from the Revit library before importing |
| Sync back is rooms-only | For full geometry round-trip, edit in Scotch and re-import |
