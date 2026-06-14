using System.Collections.Generic;
using Autodesk.Revit.DB;

namespace ScotchRevit.Mapping
{
    /// <summary>
    /// Maps a (roomId, wallSide) tuple to the Revit ElementId of the wall
    /// created during import so doors and windows can be hosted on it.
    /// </summary>
    public class WallResolver
    {
        // Key: "roomId:north" | "roomId:south" | "roomId:east" | "roomId:west"
        private readonly Dictionary<string, ElementId> _map = new();

        public void Register(string roomId, string wallSide, ElementId wallId)
            => _map[$"{roomId}:{wallSide}"] = wallId;

        public ElementId? Resolve(string roomId, string wallSide)
        {
            _map.TryGetValue($"{roomId}:{wallSide}", out var id);
            return id;
        }

        /// <summary>
        /// When a wall segment is shared between two rooms (deduplication),
        /// the same ElementId is registered for the segment key of both rooms.
        /// Call this when a segment is reused rather than newly created.
        /// </summary>
        public void RegisterShared(string roomId, string wallSide, ElementId existingWallId)
            => Register(roomId, wallSide, existingWallId);
    }
}
