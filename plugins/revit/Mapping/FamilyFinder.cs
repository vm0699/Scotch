using System;
using System.Collections.Generic;
using System.Linq;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;

namespace ScotchRevit.Mapping
{
    /// <summary>
    /// Resolves Revit door and window FamilySymbols by size.
    ///
    /// Priority:
    ///   1. Search loaded families for the closest width match.
    ///   2. Fall back to a generic type from the project template.
    ///   3. Last resort: null (caller must handle gracefully).
    /// </summary>
    public static class FamilyFinder
    {
        private const double SIZE_TOLERANCE_FT = 0.5; // ±6 inches

        // ── Doors ─────────────────────────────────────────────────────────────

        public static FamilySymbol? FindDoor(Document doc, double widthFt)
            => FindSymbol(doc, BuiltInCategory.OST_Doors, widthFt);

        public static FamilySymbol? FindWindow(Document doc, double widthFt)
            => FindSymbol(doc, BuiltInCategory.OST_Windows, widthFt);

        // ── Generic fallback ──────────────────────────────────────────────────

        /// <summary>Return the first active symbol of the given category.</summary>
        public static FamilySymbol? FindAny(Document doc, BuiltInCategory category)
        {
            return new FilteredElementCollector(doc)
                .OfClass(typeof(FamilySymbol))
                .OfCategory(category)
                .Cast<FamilySymbol>()
                .FirstOrDefault(s => s.IsActive);
        }

        // ── Internal ──────────────────────────────────────────────────────────

        private static FamilySymbol? FindSymbol(Document doc, BuiltInCategory category, double widthFt)
        {
            var symbols = new FilteredElementCollector(doc)
                .OfClass(typeof(FamilySymbol))
                .OfCategory(category)
                .Cast<FamilySymbol>()
                .Where(s => s.IsActive)
                .ToList();

            if (!symbols.Any())
                return null;

            // Try to match by width parameter (common built-in or shared param name)
            FamilySymbol? best         = null;
            double        bestDelta    = double.MaxValue;

            foreach (var sym in symbols)
            {
                double? w = GetWidthParam(sym);
                if (w == null) continue;

                double delta = Math.Abs(w.Value - widthFt);
                if (delta < bestDelta)
                {
                    bestDelta = delta;
                    best      = sym;
                }
            }

            // Accept if within tolerance, otherwise return first available
            return (best != null && bestDelta <= SIZE_TOLERANCE_FT) ? best : symbols.First();
        }

        private static double? GetWidthParam(FamilySymbol sym)
        {
            // Built-in parameter names vary; try the most common ones
            var candidates = new[]
            {
                BuiltInParameter.DOOR_WIDTH,
                BuiltInParameter.CASEWORK_WIDTH,
                BuiltInParameter.FURNITURE_WIDTH,
                BuiltInParameter.GENERIC_WIDTH,
            };

            foreach (var bip in candidates)
            {
                var p = sym.get_Parameter(bip);
                if (p != null && p.HasValue && p.StorageType == StorageType.Double)
                    return p.AsDouble();
            }

            // Also check shared/type parameters named "Width"
            var widthParam = sym.LookupParameter("Width");
            if (widthParam != null && widthParam.StorageType == StorageType.Double)
                return widthParam.AsDouble();

            return null;
        }
    }
}
