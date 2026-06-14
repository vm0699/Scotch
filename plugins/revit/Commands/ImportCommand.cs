using System;
using System.IO;
using System.Text.Json;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using ScotchRevit.Mapping;
using ScotchRevit.Models;

namespace ScotchRevit.Commands
{
    /// <summary>
    /// IExternalCommand — "Scotch → Import" ribbon button.
    ///
    /// Flow:
    ///   1. Open file-picker → user selects scotch_project.json
    ///   2. Deserialize → ArchitectureProject
    ///   3. Run ElementMapper inside a Transaction
    ///   4. Report result summary
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class ImportCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData,
                              ref string message,
                              ElementSet elements)
        {
            UIDocument uiDoc = commandData.Application.ActiveUIDocument;
            Document   doc   = uiDoc.Document;

            // ── 1. File picker ────────────────────────────────────────────────
            string? filePath = PickJsonFile();
            if (filePath == null) return Result.Cancelled;

            // ── 2. Deserialize ────────────────────────────────────────────────
            ArchitectureProject project;
            try
            {
                string json = File.ReadAllText(filePath);
                var opts = new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true,
                    AllowTrailingCommas         = true,
                };
                project = JsonSerializer.Deserialize<ArchitectureProject>(json, opts)
                       ?? throw new InvalidDataException("Deserialization returned null.");
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Scotch — JSON error",
                    $"Could not read the Scotch project file.\n\n{ex.Message}");
                return Result.Failed;
            }

            // ── 3. Create elements ────────────────────────────────────────────
            ImportResult importResult;
            using (var transaction = new Transaction(doc, $"Scotch Import — {project.Name}"))
            {
                transaction.Start();
                try
                {
                    importResult = ElementMapper.Import(doc, project);
                    transaction.Commit();
                }
                catch (Exception ex)
                {
                    transaction.RollBack();
                    TaskDialog.Show("Scotch — import error",
                        $"Element creation failed. The transaction was rolled back.\n\n{ex.Message}");
                    return Result.Failed;
                }
            }

            // ── 4. Report ─────────────────────────────────────────────────────
            TaskDialog.Show($"Scotch — {project.Name}", importResult.ToString());
            return Result.Succeeded;
        }

        // ── File picker helper ────────────────────────────────────────────────

        private static string? PickJsonFile()
        {
            using var dialog = new System.Windows.Forms.OpenFileDialog
            {
                Title       = "Open Scotch JSON project",
                Filter      = "Scotch JSON (*.json)|*.json|All files (*.*)|*.*",
                Multiselect = false,
            };

            // Default to %APPDATA%\Scotch\projects if it exists
            string defaultDir = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "Scotch", "projects");
            if (Directory.Exists(defaultDir))
                dialog.InitialDirectory = defaultDir;

            return dialog.ShowDialog() == System.Windows.Forms.DialogResult.OK
                ? dialog.FileName
                : null;
        }
    }
}
