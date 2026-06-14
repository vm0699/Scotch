using Autodesk.Revit.DB;
using ScotchRevit.Models;

namespace ScotchRevit.Mapping
{
    /// <summary>
    /// Converts Scotch plan coordinates to Revit XYZ.
    ///
    /// Scotch plan space: x = west→east, y = north→south (y=0 at entrance/top).
    /// Revit model space: same XY orientation; Z = elevation in decimal feet.
    ///
    /// Unit handling: Scotch default is "feet" (decimal). Revit 2022+ uses
    /// decimal feet as its internal unit for the DB API. Meter projects are
    /// converted on the way in.
    /// </summary>
    public class CoordinateConverter
    {
        private readonly double _scale; // multiplier: scotch_unit → revit_internal_ft

        public CoordinateConverter(string scotchUnits)
        {
            _scale = scotchUnits == "meters" ? 3.28084 : 1.0;
        }

        public double Ft(double scotchValue) => scotchValue * _scale;

        /// <summary>Plan-space point at given elevation.</summary>
        public XYZ Pt(double x, double y, double z = 0.0)
            => new XYZ(Ft(x), Ft(y), Ft(z));

        /// <summary>Midpoint of a wall side on a room boundary.</summary>
        public XYZ WallMidpoint(RoomDto room, string wall, double elevation)
        {
            return wall switch
            {
                "north" => Pt(room.X + room.Width / 2, room.Y,              elevation),
                "south" => Pt(room.X + room.Width / 2, room.Y + room.Depth, elevation),
                "west"  => Pt(room.X,              room.Y + room.Depth / 2, elevation),
                "east"  => Pt(room.X + room.Width, room.Y + room.Depth / 2, elevation),
                _       => Pt(room.X + room.Width / 2, room.Y + room.Depth / 2, elevation),
            };
        }

        /// <summary>
        /// Insertion point for a door or window on the given wall side,
        /// using the opening's offset from the wall start (left/top corner).
        /// </summary>
        public XYZ OpeningInsertPt(RoomDto room, string wall, double offset, double openingWidth, double elevation)
        {
            double centre = offset + openingWidth / 2;
            return wall switch
            {
                "north" => Pt(room.X + centre,  room.Y,              elevation),
                "south" => Pt(room.X + centre,  room.Y + room.Depth, elevation),
                "west"  => Pt(room.X,            room.Y + centre,     elevation),
                "east"  => Pt(room.X + room.Width, room.Y + centre,   elevation),
                _       => Pt(room.X + room.Width / 2, room.Y + room.Depth / 2, elevation),
            };
        }

        /// <summary>Room centroid as a UV for Revit Room placement.</summary>
        public UV RoomCentroid(RoomDto room)
            => new UV(Ft(room.X + room.Width / 2), Ft(room.Y + room.Depth / 2));

        // ── Wall endpoint helpers ─────────────────────────────────────────────

        public (XYZ p1, XYZ p2) WallEndpoints(RoomDto room, string wall, double elevation)
        {
            double x  = Ft(room.X),            y  = Ft(room.Y);
            double x2 = Ft(room.X + room.Width), y2 = Ft(room.Y + room.Depth);
            double z  = Ft(elevation);
            return wall switch
            {
                "north" => (new XYZ(x,  y,  z), new XYZ(x2, y,  z)),
                "south" => (new XYZ(x,  y2, z), new XYZ(x2, y2, z)),
                "west"  => (new XYZ(x,  y,  z), new XYZ(x,  y2, z)),
                "east"  => (new XYZ(x2, y,  z), new XYZ(x2, y2, z)),
                _       => (new XYZ(x,  y,  z), new XYZ(x2, y2, z)),
            };
        }

        /// <summary>Canonical string key for a wall segment (order-independent).</summary>
        public static string SegmentKey(XYZ p1, XYZ p2)
        {
            // Normalise direction so (A→B) and (B→A) map to the same key
            bool swap = p1.X > p2.X || (p1.X == p2.X && p1.Y > p2.Y);
            var (a, b) = swap ? (p2, p1) : (p1, p2);
            return $"{a.X:F4},{a.Y:F4};{b.X:F4},{b.Y:F4}";
        }
    }
}
