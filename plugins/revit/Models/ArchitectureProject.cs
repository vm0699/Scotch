using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace ScotchRevit.Models
{
    // ── Top-level project ──────────────────────────────────────────────────────

    public class ArchitectureProject
    {
        [JsonPropertyName("id")]    public string Id   { get; set; } = "";
        [JsonPropertyName("name")]  public string Name { get; set; } = "";
        [JsonPropertyName("units")] public string Units { get; set; } = "feet";

        [JsonPropertyName("site")]     public SiteDto     Site     { get; set; } = new();
        [JsonPropertyName("building")] public BuildingDto Building { get; set; } = new();

        [JsonPropertyName("rooms")]   public List<RoomDto>   Rooms   { get; set; } = new();
        [JsonPropertyName("doors")]   public List<DoorDto>   Doors   { get; set; } = new();
        [JsonPropertyName("windows")] public List<WindowDto> Windows { get; set; } = new();
        [JsonPropertyName("walls")]   public List<WallDto>   Walls   { get; set; } = new();
        [JsonPropertyName("levels")]  public List<LevelDto>  Levels  { get; set; } = new();

        [JsonPropertyName("notes")]    public List<string>        Notes      { get; set; } = new();
        [JsonPropertyName("warnings")] public List<WarningDto>    Warnings   { get; set; } = new();
    }

    // ── Site ──────────────────────────────────────────────────────────────────

    public class SiteDto
    {
        [JsonPropertyName("width")]       public double Width       { get; set; }
        [JsonPropertyName("depth")]       public double Depth       { get; set; }
        [JsonPropertyName("orientation")] public string Orientation { get; set; } = "north";
    }

    // ── Building ──────────────────────────────────────────────────────────────

    public class BuildingDto
    {
        [JsonPropertyName("type")]         public string Type        { get; set; } = "residential";
        [JsonPropertyName("style")]        public string Style       { get; set; } = "modern";
        [JsonPropertyName("floors")]       public int    Floors      { get; set; } = 1;
        [JsonPropertyName("floor_height")] public double FloorHeight { get; set; } = 10.0;
    }

    // ── Room ──────────────────────────────────────────────────────────────────

    public class RoomDto
    {
        [JsonPropertyName("id")]    public string Id   { get; set; } = "";
        [JsonPropertyName("name")]  public string Name { get; set; } = "";
        [JsonPropertyName("type")]  public string Type { get; set; } = "";
        [JsonPropertyName("x")]     public double X     { get; set; }
        [JsonPropertyName("y")]     public double Y     { get; set; }
        [JsonPropertyName("width")] public double Width { get; set; }
        [JsonPropertyName("depth")] public double Depth { get; set; }
        [JsonPropertyName("level")] public int    Level { get; set; }
    }

    // ── Door ──────────────────────────────────────────────────────────────────

    public class DoorDto
    {
        [JsonPropertyName("id")]      public string Id      { get; set; } = "";
        [JsonPropertyName("room_id")] public string RoomId  { get; set; } = "";
        [JsonPropertyName("wall")]    public string Wall    { get; set; } = "";  // north|south|east|west
        [JsonPropertyName("offset")]  public double Offset  { get; set; }
        [JsonPropertyName("width")]   public double Width   { get; set; }
    }

    // ── Window ────────────────────────────────────────────────────────────────

    public class WindowDto
    {
        [JsonPropertyName("id")]      public string Id      { get; set; } = "";
        [JsonPropertyName("room_id")] public string RoomId  { get; set; } = "";
        [JsonPropertyName("wall")]    public string Wall    { get; set; } = "";
        [JsonPropertyName("offset")]  public double Offset  { get; set; }
        [JsonPropertyName("width")]   public double Width   { get; set; }
    }

    // ── Explicit wall segment (optional in Scotch JSON) ───────────────────────

    public class WallDto
    {
        [JsonPropertyName("id")]        public string Id        { get; set; } = "";
        [JsonPropertyName("x1")]        public double X1        { get; set; }
        [JsonPropertyName("y1")]        public double Y1        { get; set; }
        [JsonPropertyName("x2")]        public double X2        { get; set; }
        [JsonPropertyName("y2")]        public double Y2        { get; set; }
        [JsonPropertyName("thickness")] public double Thickness { get; set; } = 0.5;
        [JsonPropertyName("room_id")]   public string? RoomId   { get; set; }
    }

    // ── Level ─────────────────────────────────────────────────────────────────

    public class LevelDto
    {
        [JsonPropertyName("index")]     public int    Index     { get; set; }
        [JsonPropertyName("name")]      public string Name      { get; set; } = "";
        [JsonPropertyName("elevation")] public double Elevation { get; set; }
    }

    // ── Warning (ignored on import, included for completeness) ────────────────

    public class WarningDto
    {
        [JsonPropertyName("id")]       public string Id       { get; set; } = "";
        [JsonPropertyName("severity")] public string Severity { get; set; } = "info";
        [JsonPropertyName("message")]  public string Message  { get; set; } = "";
    }

    // ── Phase 25 sync protocol DTOs ───────────────────────────────────────────

    /// <summary>A single room row in the sync contract (GET /projects/{id}/sync).</summary>
    public class SyncRoomDto
    {
        [JsonPropertyName("id")]    public string Id    { get; set; } = "";
        [JsonPropertyName("name")]  public string Name  { get; set; } = "";
        [JsonPropertyName("type")]  public string Type  { get; set; } = "";
        [JsonPropertyName("x")]     public double X     { get; set; }
        [JsonPropertyName("y")]     public double Y     { get; set; }
        [JsonPropertyName("width")] public double Width { get; set; }
        [JsonPropertyName("depth")] public double Depth { get; set; }
        [JsonPropertyName("level")] public int    Level { get; set; }
    }

    /// <summary>Response from GET /projects/{id}/sync.</summary>
    public class SyncContractDto
    {
        [JsonPropertyName("project_id")]     public string          ProjectId     { get; set; } = "";
        [JsonPropertyName("rooms")]          public List<SyncRoomDto> Rooms       { get; set; } = new();
        [JsonPropertyName("source_version")] public string?         SourceVersion { get; set; }
    }

    /// <summary>Payload for POST /projects/{id}/sync.</summary>
    public class SyncPayloadDto
    {
        [JsonPropertyName("rooms")]  public List<SyncRoomDto> Rooms  { get; set; } = new();
        [JsonPropertyName("source")] public string            Source { get; set; } = "revit";
    }

    /// <summary>Per-field conflict returned by POST /projects/{id}/sync.</summary>
    public class SyncConflictDto
    {
        [JsonPropertyName("room_id")]        public string RoomId        { get; set; } = "";
        [JsonPropertyName("room_name")]      public string RoomName      { get; set; } = "";
        [JsonPropertyName("field")]          public string Field         { get; set; } = "";
        [JsonPropertyName("scotch_value")]   public double ScotchValue   { get; set; }
        [JsonPropertyName("incoming_value")] public double IncomingValue { get; set; }
        [JsonPropertyName("delta")]          public double Delta         { get; set; }
    }

    /// <summary>Response from POST /projects/{id}/sync.</summary>
    public class SyncPushResponseDto
    {
        [JsonPropertyName("added")]     public List<string>          Added     { get; set; } = new();
        [JsonPropertyName("updated")]   public List<string>          Updated   { get; set; } = new();
        [JsonPropertyName("flagged")]   public List<string>          Flagged   { get; set; } = new();
        [JsonPropertyName("conflicts")] public List<SyncConflictDto> Conflicts { get; set; } = new();
    }
}
