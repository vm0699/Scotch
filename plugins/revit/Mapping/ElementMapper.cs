using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using ScotchRevit.Models;

namespace ScotchRevit.Mapping
{
    /// <summary>
    /// Translates a Scotch ArchitectureProject into Revit elements.
    ///
    /// Creation order (dependency graph):
    ///   1. Levels
    ///   2. WallTypes / FloorTypes  (find-or-create)
    ///   3. Walls      (one per room edge; shared segments deduplicated)
    ///   4. Floors     (one slab per room)
    ///   5. Rooms      (placed at centroid, bounded by walls)
    ///   6. Doors      (hosted on the resolved wall, offset from room corner)
    ///   7. Windows    (same pattern)
    ///
    /// The entire import runs inside a single Transaction opened by ImportCommand.
    /// </summary>
    public static class ElementMapper
    {
        private const string WALL_TYPE_NAME  = "Scotch Wall 6\"";
        private const string FLOOR_TYPE_NAME = "Scotch Floor 6\"";
        private const string SHARED_PARAM_SCOTCH_ID = "ScotchId";

        // ── Public entry point ────────────────────────────────────────────────

        public static ImportResult Import(Document doc, ArchitectureProject project)
        {
            var result    = new ImportResult();
            var converter = new CoordinateConverter(project.Units);
            var resolver  = new WallResolver();

            double floorHt = converter.Ft(project.Building.FloorHeight);

            // 1. Levels
            var levelMap = CreateLevels(doc, project, converter, floorHt, result);

            // 2. Type helpers
            WallType  wallType  = FindOrCreateWallType(doc);
            FloorType floorType = FindOrCreateFloorType(doc);

            // 3. Walls (with segment deduplication)
            var segmentIndex = new Dictionary<string, ElementId>();
            CreateWalls(doc, project, levelMap, converter, floorHt, wallType, resolver, segmentIndex, result);

            // 4. Floors
            CreateFloors(doc, project, levelMap, converter, floorType, result);

            // 5. Rooms
            CreateRooms(doc, project, levelMap, converter, result);

            // 6. Doors
            CreateDoors(doc, project, levelMap, converter, resolver, result);

            // 7. Windows
            CreateWindows(doc, project, levelMap, converter, resolver, result);

            return result;
        }

        // ── 1. Levels ─────────────────────────────────────────────────────────

        private static Dictionary<int, Level> CreateLevels(
            Document doc, ArchitectureProject project,
            CoordinateConverter conv, double floorHt, ImportResult result)
        {
            var map = new Dictionary<int, Level>();

            for (int i = 0; i < project.Building.Floors; i++)
            {
                double elevation = i * floorHt;
                Level level = Level.Create(doc, elevation);
                level.Name = i == 0 ? "Ground Floor" : $"Level {i + 1}";
                map[i] = level;
                result.Levels++;
            }

            return map;
        }

        // ── 2. Type helpers ───────────────────────────────────────────────────

        private static WallType FindOrCreateWallType(Document doc)
        {
            var existing = new FilteredElementCollector(doc)
                .OfClass(typeof(WallType))
                .Cast<WallType>()
                .FirstOrDefault(wt => wt.Name == WALL_TYPE_NAME);

            if (existing != null) return existing;

            // Duplicate the first basic wall type found
            var source = new FilteredElementCollector(doc)
                .OfClass(typeof(WallType))
                .Cast<WallType>()
                .First(wt => wt.Kind == WallKind.Basic);

            return (WallType)source.Duplicate(WALL_TYPE_NAME);
        }

        private static FloorType FindOrCreateFloorType(Document doc)
        {
            var existing = new FilteredElementCollector(doc)
                .OfClass(typeof(FloorType))
                .Cast<FloorType>()
                .FirstOrDefault(ft => ft.Name == FLOOR_TYPE_NAME);

            if (existing != null) return existing;

            var source = new FilteredElementCollector(doc)
                .OfClass(typeof(FloorType))
                .Cast<FloorType>()
                .First();

            return (FloorType)source.Duplicate(FLOOR_TYPE_NAME);
        }

        // ── 3. Walls ──────────────────────────────────────────────────────────

        private static void CreateWalls(
            Document doc, ArchitectureProject project,
            Dictionary<int, Level> levelMap, CoordinateConverter conv,
            double floorHt, WallType wallType, WallResolver resolver,
            Dictionary<string, ElementId> segmentIndex, ImportResult result)
        {
            string[] sides = { "north", "south", "east", "west" };

            foreach (var room in project.Rooms)
            {
                if (!levelMap.TryGetValue(room.Level, out var level)) continue;
                double elev = level.Elevation;

                foreach (var side in sides)
                {
                    var (p1, p2) = conv.WallEndpoints(room, side, elev);
                    string key   = CoordinateConverter.SegmentKey(p1, p2);

                    if (segmentIndex.TryGetValue(key, out var existingId))
                    {
                        // Reuse shared wall — register it for door/window resolution
                        resolver.RegisterShared(room.Id, side, existingId);
                        continue;
                    }

                    try
                    {
                        var line = Line.CreateBound(p1, p2);
                        var wall = Wall.Create(doc, line, wallType.Id, level.Id,
                            floorHt, 0, false, false);

                        segmentIndex[key]   = wall.Id;
                        resolver.Register(room.Id, side, wall.Id);
                        result.Walls++;
                    }
                    catch (Exception)
                    {
                        // Very short wall (< Revit minimum ~1 mm) — skip
                        result.Skipped++;
                    }
                }
            }
        }

        // ── 4. Floors ─────────────────────────────────────────────────────────

        private static void CreateFloors(
            Document doc, ArchitectureProject project,
            Dictionary<int, Level> levelMap, CoordinateConverter conv,
            FloorType floorType, ImportResult result)
        {
            foreach (var room in project.Rooms)
            {
                if (!levelMap.TryGetValue(room.Level, out var level)) continue;

                try
                {
                    double elev = level.Elevation;
                    double x  = conv.Ft(room.X),             y  = conv.Ft(room.Y);
                    double x2 = conv.Ft(room.X + room.Width), y2 = conv.Ft(room.Y + room.Depth);
                    double z  = conv.Ft(elev);

                    var loop = new CurveLoop();
                    loop.Append(Line.CreateBound(new XYZ(x,  y,  z), new XYZ(x2, y,  z)));
                    loop.Append(Line.CreateBound(new XYZ(x2, y,  z), new XYZ(x2, y2, z)));
                    loop.Append(Line.CreateBound(new XYZ(x2, y2, z), new XYZ(x,  y2, z)));
                    loop.Append(Line.CreateBound(new XYZ(x,  y2, z), new XYZ(x,  y,  z)));

                    Floor.Create(doc, new List<CurveLoop> { loop }, floorType.Id, level.Id);
                    result.Floors++;
                }
                catch (Exception)
                {
                    result.Skipped++;
                }
            }
        }

        // ── 5. Rooms ──────────────────────────────────────────────────────────

        private static void CreateRooms(
            Document doc, ArchitectureProject project,
            Dictionary<int, Level> levelMap, CoordinateConverter conv,
            ImportResult result)
        {
            foreach (var room in project.Rooms)
            {
                if (!levelMap.TryGetValue(room.Level, out var level)) continue;

                try
                {
                    UV centroid  = conv.RoomCentroid(room);
                    Room revitRoom = doc.Create.NewRoom(level, centroid);
                    revitRoom.Name = room.Name;

                    // Persist Scotch ID as a shared parameter for round-trip matching
                    SetScotchId(revitRoom, room.Id);
                    result.Rooms++;
                }
                catch (Exception)
                {
                    result.Skipped++;
                }
            }
        }

        // ── 6. Doors ──────────────────────────────────────────────────────────

        private static void CreateDoors(
            Document doc, ArchitectureProject project,
            Dictionary<int, Level> levelMap, CoordinateConverter conv,
            WallResolver resolver, ImportResult result)
        {
            var roomIndex = project.Rooms.ToDictionary(r => r.Id);

            foreach (var door in project.Doors)
            {
                if (!roomIndex.TryGetValue(door.RoomId, out var room)) continue;
                if (!levelMap.TryGetValue(room.Level, out var level))  continue;

                var wallId = resolver.Resolve(door.RoomId, door.Wall);
                if (wallId == null) continue;

                var hostWall = doc.GetElement(wallId) as Wall;
                if (hostWall == null) continue;

                var symbol = FamilyFinder.FindDoor(doc, conv.Ft(door.Width))
                          ?? FamilyFinder.FindAny(doc, BuiltInCategory.OST_Doors);
                if (symbol == null) { result.Skipped++; continue; }

                if (!symbol.IsActive) symbol.Activate();

                try
                {
                    var insertPt = conv.OpeningInsertPt(room, door.Wall,
                        door.Offset, door.Width, level.Elevation);

                    doc.Create.NewFamilyInstance(insertPt, symbol, hostWall,
                        level, Autodesk.Revit.DB.Structure.StructuralType.NonStructural);
                    result.Doors++;
                }
                catch (Exception)
                {
                    result.Skipped++;
                }
            }
        }

        // ── 7. Windows ────────────────────────────────────────────────────────

        private static void CreateWindows(
            Document doc, ArchitectureProject project,
            Dictionary<int, Level> levelMap, CoordinateConverter conv,
            WallResolver resolver, ImportResult result)
        {
            var roomIndex = project.Rooms.ToDictionary(r => r.Id);

            foreach (var win in project.Windows)
            {
                if (!roomIndex.TryGetValue(win.RoomId, out var room)) continue;
                if (!levelMap.TryGetValue(room.Level, out var level))  continue;

                var wallId = resolver.Resolve(win.RoomId, win.Wall);
                if (wallId == null) continue;

                var hostWall = doc.GetElement(wallId) as Wall;
                if (hostWall == null) continue;

                var symbol = FamilyFinder.FindWindow(doc, conv.Ft(win.Width))
                          ?? FamilyFinder.FindAny(doc, BuiltInCategory.OST_Windows);
                if (symbol == null) { result.Skipped++; continue; }

                if (!symbol.IsActive) symbol.Activate();

                try
                {
                    // Windows sit at sill height — default 2.5 ft above floor
                    double sillOffset = 2.5;
                    var insertPt = conv.OpeningInsertPt(room, win.Wall,
                        win.Offset, win.Width, level.Elevation + sillOffset);

                    doc.Create.NewFamilyInstance(insertPt, symbol, hostWall,
                        level, Autodesk.Revit.DB.Structure.StructuralType.NonStructural);
                    result.Windows++;
                }
                catch (Exception)
                {
                    result.Skipped++;
                }
            }
        }

        // ── Shared parameter helper ───────────────────────────────────────────

        private static void SetScotchId(Element element, string scotchId)
        {
            var param = element.LookupParameter(SHARED_PARAM_SCOTCH_ID);
            param?.Set(scotchId);
            // If the shared parameter isn't loaded in the project, the
            // set is a no-op — the add-in still functions, just without
            // round-trip ID persistence. See docs/integrations/revit-mapping.md
            // for how to load the Scotch shared parameter file.
        }
    }

    // ── Result summary ────────────────────────────────────────────────────────

    public class ImportResult
    {
        public int Levels  { get; set; }
        public int Walls   { get; set; }
        public int Floors  { get; set; }
        public int Rooms   { get; set; }
        public int Doors   { get; set; }
        public int Windows { get; set; }
        public int Skipped { get; set; }

        public override string ToString() =>
            $"Import complete.\n\n" +
            $"  Levels:  {Levels}\n" +
            $"  Walls:   {Walls}\n" +
            $"  Floors:  {Floors}\n" +
            $"  Rooms:   {Rooms}\n" +
            $"  Doors:   {Doors}\n" +
            $"  Windows: {Windows}\n" +
            (Skipped > 0 ? $"\n  Skipped: {Skipped} element(s) (see journal for details)" : "");
    }
}
