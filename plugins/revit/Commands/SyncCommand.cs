using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
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
    /// IExternalCommand — "Scotch ↔ Sync" ribbon button (Phase 27.5).
    ///
    /// Bidirectional round-trip using the Phase 25 sync protocol:
    ///   PULL  — GET /projects/{id}/sync  → show current Scotch room list
    ///   PUSH  — POST /projects/{id}/sync → send Revit rooms to Scotch
    ///
    /// The dialog lets the architect choose Pull, Push, or Both (pull first to
    /// see what Scotch has, then push Revit changes back).
    ///
    /// Conflicts (dimension delta > 6 in or name mismatch) are surfaced in
    /// the result dialog so the architect can decide which side wins.
    /// </summary>
    [Transaction(TransactionMode.ReadOnly)]
    [Regeneration(RegenerationOption.Manual)]
    public class SyncCommand : IExternalCommand
    {
        // ── IExternalCommand entry ────────────────────────────────────────────

        public Result Execute(ExternalCommandData commandData,
                              ref string message,
                              ElementSet elements)
        {
            Document doc = commandData.Application.ActiveUIDocument.Document;

            // ── 1. Project ID + mode ──────────────────────────────────────────
            string? projectId;
            SyncMode mode;
            if (!AskForSettings(out projectId, out mode) || projectId == null)
                return Result.Cancelled;

            // ── 2. Backend reachability ───────────────────────────────────────
            using var client = new ScotchClient();
            if (!client.IsReachable())
            {
                TaskDialog.Show("Scotch — connection error",
                    "Cannot reach the Scotch backend at http://localhost:8000.\n" +
                    "Make sure it is running:\n  cd services/api\n  uvicorn app.main:app --reload --port 8000");
                return Result.Failed;
            }

            // ── 3. Pull (always fetch for context; show summary on Pull-only) ─
            var contract = client.PullSync(projectId);
            if (contract == null)
            {
                TaskDialog.Show("Scotch — pull failed",
                    $"GET /projects/{projectId}/sync returned an error.\n" +
                    "Verify the project ID and that the backend is running.");
                return Result.Failed;
            }

            if (mode == SyncMode.PullOnly)
            {
                ShowPullSummary(projectId, contract);
                return Result.Succeeded;
            }

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
                    "Place rooms first (Architecture → Room), then sync.");
                return Result.Cancelled;
            }

            // ── 5. Build SyncPayload ──────────────────────────────────────────
            string units = client.GetProject(projectId)?.Units ?? "feet";
            var syncRooms = BuildSyncRooms(doc, revitRooms, units, out int skipped);

            // ── 6. POST /projects/{id}/sync ───────────────────────────────────
            var payload = new SyncPayloadDto { Rooms = syncRooms, Source = "revit" };
            var pushResult = client.PushSync(projectId, payload);

            if (pushResult == null)
            {
                TaskDialog.Show("Scotch — push failed",
                    $"POST /projects/{projectId}/sync was rejected by the backend.\n" +
                    "Check the backend logs for details.");
                return Result.Failed;
            }

            // ── 7. Result dialog ──────────────────────────────────────────────
            ShowPushResult(projectId, pushResult, skipped);
            return Result.Succeeded;
        }

        // ── Build SyncRoomDto list from Revit room collector ──────────────────

        private static List<SyncRoomDto> BuildSyncRooms(
            Document doc,
            List<Room> revitRooms,
            string scotchUnits,
            out int skipped)
        {
            var result  = new List<SyncRoomDto>();
            skipped = 0;

            foreach (var rr in revitRooms)
            {
                try
                {
                    string scotchId = rr.LookupParameter("ScotchId")?.AsString()
                                   ?? $"revit-{rr.Id.IntegerValue}";

                    BoundingBoxXYZ? bb = rr.get_BoundingBox(null);
                    if (bb == null) { skipped++; continue; }

                    double xFt    = ScaleToScotch(bb.Min.X, scotchUnits);
                    double yFt    = ScaleToScotch(bb.Min.Y, scotchUnits);
                    double wFt    = ScaleToScotch(bb.Max.X - bb.Min.X, scotchUnits);
                    double dFt    = ScaleToScotch(bb.Max.Y - bb.Min.Y, scotchUnits);
                    int    level  = GetFloorIndex(doc, rr);

                    result.Add(new SyncRoomDto
                    {
                        Id    = scotchId,
                        Name  = rr.Name,
                        Type  = NormalizeRoomType(rr.Name),
                        X     = Math.Round(xFt, 3),
                        Y     = Math.Round(yFt, 3),
                        Width = Math.Round(wFt, 3),
                        Depth = Math.Round(dFt, 3),
                        Level = level,
                    });
                }
                catch
                {
                    skipped++;
                }
            }

            return result;
        }

        // ── Dialog helpers ─────────────────────────────────────────────────────

        private static bool AskForSettings(out string? projectId, out SyncMode mode)
        {
            projectId = null;
            mode      = SyncMode.PushOnly;

            var form = new System.Windows.Forms.Form
            {
                Text            = "Scotch — Sync (Phase 25 protocol)",
                Width           = 460,
                Height          = 230,
                FormBorderStyle = System.Windows.Forms.FormBorderStyle.FixedDialog,
                StartPosition   = System.Windows.Forms.FormStartPosition.CenterScreen,
                MaximizeBox     = false,
                MinimizeBox     = false,
            };

            int top = 12;
            var lblId = new System.Windows.Forms.Label
                { Text = "Scotch project ID:", Left = 12, Top = top, Width = 420 };
            top += 20;
            var txtId = new System.Windows.Forms.TextBox
                { Left = 12, Top = top, Width = 420 };
            top += 36;

            var rbPull = new System.Windows.Forms.RadioButton
                { Text = "Pull only  — fetch Scotch → show what Scotch has", Left = 12, Top = top, Width = 420, Checked = false };
            top += 22;
            var rbPush = new System.Windows.Forms.RadioButton
                { Text = "Push only  — send Revit rooms → Scotch", Left = 12, Top = top, Width = 420, Checked = true };
            top += 22;
            var rbBoth = new System.Windows.Forms.RadioButton
                { Text = "Both (pull then push)", Left = 12, Top = top, Width = 420, Checked = false };
            top += 30;

            var btnOk = new System.Windows.Forms.Button
                { Text = "Sync", Left = 280, Top = top, Width = 72,
                  DialogResult = System.Windows.Forms.DialogResult.OK };
            var btnCancel = new System.Windows.Forms.Button
                { Text = "Cancel", Left = 364, Top = top, Width = 72,
                  DialogResult = System.Windows.Forms.DialogResult.Cancel };

            form.Controls.AddRange(new System.Windows.Forms.Control[]
                { lblId, txtId, rbPull, rbPush, rbBoth, btnOk, btnCancel });
            form.AcceptButton = btnOk;
            form.CancelButton = btnCancel;

            if (form.ShowDialog() != System.Windows.Forms.DialogResult.OK)
                return false;

            projectId = txtId.Text.Trim();
            if (projectId.Length == 0) return false;

            if (rbPull.Checked) mode = SyncMode.PullOnly;
            else if (rbBoth.Checked) mode = SyncMode.Both;
            else mode = SyncMode.PushOnly;

            return true;
        }

        private static void ShowPullSummary(string projectId, SyncContractDto contract)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Project: {projectId}");
            if (contract.SourceVersion != null)
                sb.AppendLine($"Version: {contract.SourceVersion}");
            sb.AppendLine($"Rooms in Scotch: {contract.Rooms.Count}");
            sb.AppendLine();
            foreach (var r in contract.Rooms.Take(20))
                sb.AppendLine($"  {r.Name} ({r.Type}) — {r.Width:F1} × {r.Depth:F1} ft");
            if (contract.Rooms.Count > 20)
                sb.AppendLine($"  … and {contract.Rooms.Count - 20} more");
            sb.AppendLine();
            sb.AppendLine("To push Revit rooms back, run Sync again with Push mode.");

            TaskDialog.Show("Scotch — pull summary", sb.ToString());
        }

        private static void ShowPushResult(string projectId, SyncPushResponseDto result, int skipped)
        {
            var sb = new StringBuilder();
            sb.AppendLine($"Project: {projectId}");
            sb.AppendLine();
            sb.AppendLine($"  Added:   {result.Added.Count}");
            sb.AppendLine($"  Updated: {result.Updated.Count}");
            sb.AppendLine($"  Flagged: {result.Flagged.Count}");
            if (skipped > 0)
                sb.AppendLine($"  Skipped (no bounding box): {skipped}");

            if (result.Conflicts.Count > 0)
            {
                sb.AppendLine();
                sb.AppendLine($"{result.Conflicts.Count} conflict(s) — Revit vs. Scotch:");
                foreach (var c in result.Conflicts.Take(8))
                    sb.AppendLine($"  {c.RoomName}.{c.Field}: Scotch={c.ScotchValue:F1}, Revit={c.IncomingValue:F1} (Δ{c.Delta:+0.1;-0.1})");
                if (result.Conflicts.Count > 8)
                    sb.AppendLine($"  … and {result.Conflicts.Count - 8} more");
                sb.AppendLine();
                sb.AppendLine("Open the Scotch workspace → Sync panel to resolve conflicts.");
            }
            else
            {
                sb.AppendLine();
                sb.AppendLine("No conflicts — all rooms accepted.");
            }

            TaskDialog.Show("Scotch — sync complete", sb.ToString());
        }

        // ── Utility helpers ────────────────────────────────────────────────────

        private enum SyncMode { PullOnly, PushOnly, Both }

        private static double ScaleToScotch(double revitInternalFt, string scotchUnits)
            => scotchUnits == "meters" ? revitInternalFt / 3.28084 : revitInternalFt;

        private static int GetFloorIndex(Document doc, Room room)
        {
            Level? level = doc.GetElement(room.LevelId) as Level;
            if (level == null) return 0;
            var allLevels = new FilteredElementCollector(doc)
                .OfClass(typeof(Level))
                .Cast<Level>()
                .OrderBy(l => l.Elevation)
                .ToList();
            int idx = allLevels.FindIndex(l => l.Id == level.Id);
            return idx >= 0 ? idx : 0;
        }

        private static string NormalizeRoomType(string roomName)
        {
            string lower = roomName.ToLowerInvariant();
            if (lower.Contains("bed"))     return lower.Contains("master") ? "master_bedroom" : "bedroom";
            if (lower.Contains("bath"))    return "bathroom";
            if (lower.Contains("toilet"))  return "bathroom";
            if (lower.Contains("kitchen")) return "kitchen";
            if (lower.Contains("living"))  return "living";
            if (lower.Contains("dining"))  return "dining";
            if (lower.Contains("study"))   return "study";
            if (lower.Contains("garage"))  return "garage";
            if (lower.Contains("balcon"))  return "balcony";
            if (lower.Contains("stair"))   return "stair";
            if (lower.Contains("park"))    return "parking";
            return lower.Replace(" ", "_");
        }
    }
}
