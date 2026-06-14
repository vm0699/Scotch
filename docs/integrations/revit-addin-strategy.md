# Revit Add-in Strategy — Scotch Integration

> **Phase 11.3 / 14 strategy document.**  
> Full implementation lands in Phase 14; this document specifies the architecture so development can start in parallel.

---

## 1. Overview

The Scotch ↔ Revit integration follows a **JSON-import-first** model: Scotch exports its canonical `ArchitectureProject` JSON, and a Revit C# add-in reads it and creates Revit elements. A lightweight **sync** mechanism allows round-trips when Revit geometry is later exported back to Scotch for AI-driven editing.

```
Scotch (export JSON)
        ↓
  scotch_project.json
        ↓
  Revit C# Add-in
  (External Command)
        ↓
  Revit Model (Levels, Walls, Floors, Rooms, Doors, Windows)
```

---

## 2. C# Add-in Architecture

### 2.1 Project structure

```
ScotchRevit/
  ScotchRevit.csproj          # targets Revit API (net48)
  App.cs                      # IExternalApplication — ribbon button
  Commands/
    ImportCommand.cs          # IExternalCommand — import JSON
    SyncCommand.cs            # IExternalCommand — sync changes back to Scotch
  Models/
    ArchitectureProject.cs    # mirrors Scotch JSON schema (System.Text.Json)
    RoomDto.cs
    DoorDto.cs
    WindowDto.cs
    SiteDto.cs
    BuildingDto.cs
  Mapping/
    ElementMapper.cs          # Scotch → Revit element translation
    FamilyFinder.cs           # resolves door/window families by size
  Services/
    ScotchClient.cs           # optional: HTTP client for live Scotch backend
  ScotchRevit.addin           # Revit add-in manifest
```

### 2.2 Add-in manifest (`ScotchRevit.addin`)

```xml
<?xml version="1.0" encoding="utf-8"?>
<RevitAddIns>
  <AddIn Type="Application">
    <Name>Scotch</Name>
    <Assembly>ScotchRevit.dll</Assembly>
    <FullClassName>ScotchRevit.App</FullClassName>
    <ClientId>SCOTCH-0000-0000-0000-000000000001</ClientId>
    <VendorId>SCOTCH</VendorId>
    <VendorDescription>Scotch — AI Architecture Platform</VendorDescription>
  </AddIn>
</RevitAddIns>
```

### 2.3 External Application (`App.cs`)

```csharp
public class App : IExternalApplication
{
    public Result OnStartup(UIControlledApplication app)
    {
        RibbonPanel panel = app.CreateRibbonPanel("Scotch");
        PushButtonData importBtn = new("ImportScotch", "Import\nScotch",
            Assembly.GetExecutingAssembly().Location,
            "ScotchRevit.Commands.ImportCommand");
        importBtn.ToolTip = "Import a Scotch JSON floor plan.";
        panel.AddItem(importBtn);
        return Result.Succeeded;
    }
    public Result OnShutdown(UIControlledApplication app) => Result.Succeeded;
}
```

---

## 3. JSON Import Flow

### 3.1 Trigger

User clicks **Scotch → Import** in the Revit ribbon. A file-picker dialog opens; user selects `scotch_project.json` (exported from Scotch via *Exports → JSON*).

### 3.2 Deserialization

```csharp
using System.Text.Json;
var json = File.ReadAllText(filePath);
var project = JsonSerializer.Deserialize<ArchitectureProject>(json,
    new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
```

`ArchitectureProject.cs` mirrors the Scotch Pydantic schema exactly (same field names, same nesting):

| Scotch field | Revit DTO |
|---|---|
| `site.width` / `site.depth` | `SiteDto.Width` / `SiteDto.Depth` |
| `building.floor_height` | `BuildingDto.FloorHeight` |
| `building.floors` | `BuildingDto.Floors` |
| `rooms[].x,y,width,depth` | `RoomDto.X,Y,Width,Depth` |
| `doors[].room_id, wall, offset, width` | `DoorDto.*` |
| `windows[].room_id, wall, offset, width` | `WindowDto.*` |

### 3.3 Unit conversion

Scotch units are **feet** by default. Revit internal units are **decimal feet** (Revit 2022+) or **feet-inches** depending on API version. Convert:

```csharp
private static double ToRevitFt(double scotchFt, string units) =>
    units == "meters" ? scotchFt * 3.28084 : scotchFt;
```

---

## 4. Element Creation Plan

Elements are created in dependency order: Levels → Floors → Walls → Rooms → Doors → Windows.

### 4.1 Levels

```csharp
// One level per floor
for (int i = 0; i < project.Building.Floors; i++)
{
    double elevation = i * floorHeight;
    Level level = Level.Create(doc, elevation);
    level.Name = $"Level {i + 1}";
}
```

### 4.2 Floor slabs

Each room gets a floor element at its level:

```csharp
var outline = new CurveLoop();
outline.Append(Line.CreateBound(new XYZ(room.X, room.Y, 0), new XYZ(room.X + room.Width, room.Y, 0)));
// ... all 4 edges
FloorType floorType = FindOrCreateFloorType(doc, "Scotch Floor 6\"");
Floor floor = Floor.Create(doc, new List<CurveLoop> { outline }, floorType.Id, level.Id);
```

### 4.3 Walls

Each room has 4 wall segments (north, south, east, west). Shared walls between adjacent rooms are de-duplicated (snap within WALL_T tolerance):

```csharp
var wallLine = Line.CreateBound(p1, p2);
WallType wallType = FindOrCreateWallType(doc, "Scotch Wall 6\"");
Wall wall = Wall.Create(doc, wallLine, wallType.Id, level.Id, floorHeight, 0, false, false);
```

De-duplication: build a `HashSet<string>` of wall segment hashes (`"x1,y1→x2,y2"` normalized to canonical direction) and skip duplicates.

### 4.4 Rooms

```csharp
// Place a Room at the room centroid, bounded by the walls
UV centroid = new UV(room.X + room.Width / 2, room.Y + room.Depth / 2);
Room revitRoom = doc.Create.NewRoom(level, centroid);
revitRoom.Name = room.Name;
// Set "Area" parameter — Revit computes it from bounding walls
```

### 4.5 Doors and Windows

Use **FamilyFinder** to locate a door/window family by approximate size:

```csharp
FamilySymbol doorType = FamilyFinder.FindDoor(doc, door.Width);
if (doorType == null) doorType = FamilyFinder.LoadDefaultDoor(doc);
// Place on the host wall at offset
Wall hostWall = WallResolver.FindWall(doc, room, door.Wall, walls);
FamilyInstance doorInst = doc.Create.NewFamilyInstance(insertPt, doorType, hostWall, level, StructuralType.NonStructural);
```

**FamilyFinder priority:**
1. Search loaded families by `FamilyName` containing "door" (case-insensitive).
2. Filter by `FamilySymbol` width parameter closest to `door.width`.
3. If none found, load `M_Door-Single-Flush.rfa` from Revit's `Metric Library`.

### 4.6 Element summary

| Scotch entity | Revit element | API class |
|---|---|---|
| Site boundary | Site shape / scope box | `SiteSubRegion` or scope box |
| Room | `Room` | `doc.Create.NewRoom` |
| Wall (per room edge) | `Wall` (basic wall) | `Wall.Create` |
| Floor (room interior) | `Floor` | `Floor.Create` |
| Door | `FamilyInstance` (door category) | `doc.Create.NewFamilyInstance` |
| Window | `FamilyInstance` (window category) | `doc.Create.NewFamilyInstance` |
| Roof | `RoofBase` (flat roof) | `FootPrintRoof` |

---

## 5. Sync Strategy (Scotch ↔ Revit Round-trip)

### 5.1 Scotch → Revit (import, covered above)

### 5.2 Revit → Scotch (export)

A second `SyncCommand` reads modified Revit geometry and POSTs an updated `ArchitectureProject` JSON to the Scotch backend (`PATCH /projects/{id}`):

```csharp
// Collect room geometry from Revit
var rooms = new FilteredElementCollector(doc)
    .OfCategory(BuiltInCategory.OST_Rooms)
    .Cast<Room>()
    .Select(r => new RoomDto
    {
        Name  = r.Name,
        Width = r.get_Parameter(BuiltInParameter.ROOM_WIDTH).AsDouble(),
        Depth = r.get_Parameter(BuiltInParameter.ROOM_DEPTH).AsDouble(),
        // ... location from BoundingBox
    });

var updated = BuildArchitectureProject(rooms, walls, doors, windows);
await ScotchClient.PatchProject(projectId, updated);
```

### 5.3 Conflict resolution

| Conflict | Resolution |
|---|---|
| Room renamed in Revit | Scotch name overwritten on next push |
| Room resized in Revit | New `width`/`depth` used; re-runs validation |
| Room added in Revit (no Scotch id) | Assigned a new UUID; treated as new room |
| Room deleted in Revit | Flagged as warning; user confirms removal |

### 5.4 ID persistence

Revit stores the Scotch `room.id` in a **shared parameter** (`ScotchId`, GUID string type) attached to every imported Room element. This makes round-trip matching deterministic.

---

## 6. Dependencies

| Dependency | Version | Notes |
|---|---|---|
| Revit API | 2024 (target 2022+) | `RevitAPI.dll`, `RevitAPIUI.dll` |
| .NET Framework | 4.8 | Required by Revit |
| `System.Text.Json` | bundled in .NET | No external JSON lib needed |
| `Newtonsoft.Json` | optional | If `System.Text.Json` causes issues |

---

## 7. File locations

| File | Description |
|---|---|
| `%APPDATA%\Autodesk\Revit\Addins\2024\ScotchRevit.addin` | Add-in manifest (installed) |
| `%APPDATA%\Scotch\projects\` | Exported JSON staging area |
| Revit family library | Searched for door/window families |

---

## 8. Phase 14 implementation sequence

1. **14.1** — C# project scaffold (`ScotchRevit.csproj`, `App.cs`, ribbon button)
2. **14.2** — JSON deserialization + DTO models
3. **14.3** — Element creation: Levels → Walls → Floors → Rooms → Doors → Windows
4. **14.4** — Mapping documentation + family finder
5. **14.5** — Round-trip: SyncCommand + shared parameter strategy

> Live testing requires Revit installed. CI builds the DLL without Revit available using the Revit API stub package (`RevitApiStubs`).
