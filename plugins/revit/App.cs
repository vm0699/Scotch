using System.Reflection;
using Autodesk.Revit.UI;

namespace ScotchRevit
{
    /// <summary>
    /// IExternalApplication entry point — registers the Scotch ribbon tab on startup.
    /// </summary>
    public class App : IExternalApplication
    {
        public Result OnStartup(UIControlledApplication app)
        {
            try
            {
                string assemblyPath = Assembly.GetExecutingAssembly().Location;

                RibbonPanel panel = app.CreateRibbonPanel("Scotch");

                // Import button
                var importData = new PushButtonData(
                    "ScotchImport",
                    "Import\nScotch",
                    assemblyPath,
                    "ScotchRevit.Commands.ImportCommand")
                {
                    ToolTip        = "Import a Scotch JSON floor plan into the current document.",
                    LongDescription =
                        "Reads a scotch_project.json file exported from Scotch and creates " +
                        "Levels, Walls, Floors, Rooms, Doors, and Windows in the active Revit model.",
                };

                // Sync button
                var syncData = new PushButtonData(
                    "ScotchSync",
                    "Sync to\nScotch",
                    assemblyPath,
                    "ScotchRevit.Commands.SyncCommand")
                {
                    ToolTip        = "Push Revit geometry changes back to the Scotch backend.",
                    LongDescription =
                        "Reads current Room/Wall geometry from Revit and PATCHes the Scotch " +
                        "project via the local API (http://localhost:8000).",
                };

                panel.AddItem(importData);
                panel.AddSeparator();
                panel.AddItem(syncData);

                return Result.Succeeded;
            }
            catch (System.Exception ex)
            {
                TaskDialog.Show("Scotch — startup error", ex.Message);
                return Result.Failed;
            }
        }

        public Result OnShutdown(UIControlledApplication app) => Result.Succeeded;
    }
}
