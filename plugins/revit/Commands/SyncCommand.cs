using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;
using ScotchRevit.Mapping;
using ScotchRevit.Models;
using ScotchRevit.Services;

namespace ScotchRevit.Commands
{
    /// <summary>
    /// IExternalCommand — "Scotch ← Sync" ribbon button.
    ///
    /// Flow:
    ///   1. Ask for project ID (or read from document ExtensibleStorage)
    ///   2. Verify Scotch backend is reachable
    ///   3. Collect Revit Rooms via FilteredElementCollector
    ///   4. Build a partial ArchitectureProject patch payload (rooms only)
    ///   5. PATCH /projects/{id} via ScotchClient
    ///   6. Report success / failure
    ///
    /// The sync is rooms-only: it updates names, dimensions, and positions.
    /// Wall geometry changes are not synced back (use the Import flow to re-import).
    /// </summary>
    [Transaction(TransactionMode.ReadOnly)]
    [Regeneration(RegenerationOption.Manual)]
    public class SyncCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData,
                              ref string message,
                              ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;

            // ── 1. Get project ID ─────────────────────────────────────────────
            string? projectId = AskForProjectId();
            if (projectId == null) return Result.Cancelled;

            // ── 2. Check backend ──────────────────────────────────────────────
            using var client = new ScotchClient();
            if (!client.IsReachable())
            {
                TaskDialog.Show("Scotch — connection error",
                    "Cannot reach the Scotch backend at http://localhost:8000.\n" +
                    "Make sure the backend is running:\n  cd services/api && uvicorn app.main:app --reload --port 8000");
                return Result.Failed;
            }

            // ── 3. Fetch current project for unit context ─────────────────────
            var existing = client.GetProject(projectId);
            string units = existing?.Units ?? "feet";
            var conv = new CoordinateConverter(units);

            // ── 4. Collect Revit rooms ────────────────────────────────────────
            var revitRooms = new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Rooms)
                .Cast<Room>()
                .Where(r => r.Area > 0)
                .ToList();

            if (revitRooms.Count == 0)
            {
                TaskDialog.Show("Scotch — no rooms",
                    "No placed rooms found in this Revit model.\n" +
                    "Place rooms first, then sync.");
                return Result.Cancelled;
            }

            // ── 5. Build patch payload ────────────────────────────────────────
            var rooms = new List<RoomDto>();
            int skipped = 0;

            foreach (var rr in revitRooms)
            {
                try
                {
                    // Read ScotchId shared parameter (may be absent — generate placeholder)
                    string scotchId = rr.LookupParameter("ScotchId")?.AsString()
                                   ?? $"revit-{rr.Id.IntegerValue}";

                    // Room bounding box (in Revit internal feet)
                    BoundingBoxXYZ? bb = rr.get_BoundingBox(null);
                    if (bb == null) { skipped++; continue; }

                    double xFt    = ScaleBack(bb.Min.X, units);
                    double yFt    = ScaleBack(bb.Min.Y, units);
                    double wFt    = ScaleBack(bb.Max.X - bb.Min.X, units);
                    double dFt    = ScaleBack(bb.Max.Y - bb.Min.Y, units);
                    int    floor  = GetFloorIndex(doc, rr);

                    rooms.Add(new RoomDto
                    {
                        Id    = scotchId,
                        Name  = rr.Name,
                        Type  = NormalizeRoomType(rr.Name),
                        X     = Math.Round(xFt, 3),
                        Y     = Math.Round(yFt, 3),
                        Width = Math.Round(wFt, 3),
                        Depth = Math.Round(dFt, 3),
                        Level = floor,
                    });
                }
                catch (Exception)
                {
                    skipped++;
                }
            }

            // ── 6. PATCH ──────────────────────────────────────────────────────
            var payload = new { rooms };
            bool ok = client.PatchProject(projectId, payload);

            if (!ok)
            {
                TaskDialog.Show("Scotch — sync failed",
                    $"The backend rejected the PATCH for project \"{projectId}\".\n" +
                    "Check the backend logs for details.");
                return Result.Failed;
            }

            // ── 7. Report ─────────────────────────────────────────────────────
            string skipMsg = skipped > 0 ? $"\n  Skipped: {skipped}" : "";
            TaskDialog.Show("Scotch — sync complete",
                $"Project \"{projectId}\" updated.\n\n" +
                $"  Rooms synced: {rooms.Count}" + skipMsg + "\n\n" +
                "Reload the workspace in Scotch to see the changes.");

            return Result.Succeeded;
        }

        // ── Helpers ───────────────────────────────────────────────────────────

        private static string? AskForProjectId()
        {
            // Simple text-input dialog using TaskDialogCommandLinkId workaround.
            // For a production add-in this would be a proper WPF dialog.
            // Here we use a Windows InputBox-style approach.
            string? id = null;
            var form = new System.Windows.Forms.Form
            {
                Text            = "Scotch — Sync",
                Width           = 420,
                Height          = 160,
                FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog,
                StartPosition   = System.Windows.Forms.FormStartPosition.CenterScreen,
                MaximizeBox     = false,
                MinimizeBox     = false,
            };

            var label = new System.Windows.Forms.Label
            {
                Text     = "Scotch project ID  (from the URL or project panel):",
                Left     = 12, Top = 12, Width = 380,
            };

            var textBox = new System.Windows.Forms.TextBox
            {
                Left  = 12, Top = 36, Width = 380,
            };

            var ok = new System.Windows.Forms.Button
            {
                Text         = "Sync",
                Left         = 220, Top = 76, Width = 80,
                DialogResult = System.Windows.Forms.DialogResult.OK,
            };

            var cancel = new System.Windows.Forms.Button
            {
                Text         = "Cancel",
                Left         = 312, Top = 76, Width = 80,
                DialogResult = System.Windows.Forms.DialogResult.Cancel,
            };

            form.Controls.AddRange(new System.Windows.Forms.Control[] { label, textBox, ok, cancel });
            form.AcceptButton = ok;
            form.CancelButton = cancel;

            if (form.ShowDialog() == System.Windows.Forms.DialogResult.OK)
            {
                id = textBox.Text.Trim();
                if (id.Length == 0) id = null;
            }

            return id;
        }

        private static int GetFloorIndex(Document doc, Room room)
        {
            Level? level = doc.GetElement(room.LevelId) as Level;
            if (level == null) return 0;

            // Sort all levels by elevation and find this one's index
            var allLevels = new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .Cast<Level>()
                .OrderBy(l => l.Elevation)
                .ToList();

            int idx = allLevels.FindIndex(l => l.Id == level.Id);
            return idx >= 0 ? idx : 0;
        }

        private static double ScaleBack(double revitFt, string scotchUnits)
            => scotchUnits == "meters" ? revitFt / 3.28084 : revitFt;

        private static string NormalizeRoomType(string roomName)
        {
            // Map common Revit room names to Scotch room types
            string lower = roomName.ToLowerInvariant();
            if (lower.Contains("bed"))    return lower.Contains("master") ? "master_bedroom" : "bedroom";
            if (lower.Contains("bath"))   return "bathroom";
            if (lower.Contains("toilet")) return "bathroom";
            if (lower.Contains("kitchen")) return "kitchen";
            if (lower.Contains("living")) return "living";
            if (lower.Contains("dining")) return "dining";
            if (lower.Contains("study"))  return "study";
            if (lower.Contains("garage")) return "garage";
            if (lower.Contains("balcon")) return "balcony";
            return lower.Replace(" ", "_");
        }
    }
}
