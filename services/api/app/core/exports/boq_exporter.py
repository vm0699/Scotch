"""BOQ export adapters — Phase 31.8.

Exports:
  CSV  — one row per BOQItem, grouped by category
  JSON — full CostPlan + MaterialPlan as structured JSON
  PDF  — text-based summary using reportlab (fallback to plain text if unavailable)
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from app.core.models.project import ArchitectureProject


# ── CSV export ────────────────────────────────────────────────────────────────


def export_boq_csv(project: ArchitectureProject, output_path: Path) -> Path:
    """Write BOQ as CSV. Returns output_path."""
    cost = project.cost_plan
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Category", "Description", "Unit", "Quantity", "Rate (INR)", "Amount (INR)",
            "Source Objects", "Confidence", "Needs Review",
        ])
        for item in cost.boq_items:
            writer.writerow([
                item.category,
                item.description,
                item.unit,
                f"{item.quantity:.3f}",
                f"{item.rate:.2f}",
                f"{item.amount:.2f}",
                "|".join(item.source_object_ids),
                f"{item.confidence:.2f}",
                "Yes" if item.needs_review else "No",
            ])
        # Totals
        writer.writerow([])
        writer.writerow(["CATEGORY TOTALS", "", "", "", "", "", "", "", ""])
        for ct in cost.category_totals:
            writer.writerow([ct.category, "", "", "", "", f"{ct.total:.2f}", "", "", ""])
        writer.writerow(["GRAND TOTAL", "", "", "", "", f"{cost.grand_total:.2f}", "", "", ""])
        # Missing rates
        if cost.missing_rates:
            writer.writerow([])
            writer.writerow(["MISSING RATES — amounts excluded from totals", "", "", "", "", "", "", "", ""])
            for mr in cost.missing_rates:
                writer.writerow([mr, "", "", "", "0", "0", "", "", ""])
        # Assumptions
        if cost.assumptions:
            writer.writerow([])
            writer.writerow(["ASSUMPTIONS", "", "", "", "", "", "", "", ""])
            for a in cost.assumptions:
                writer.writerow([a, "", "", "", "", "", "", "", ""])
    return output_path


# ── JSON export ───────────────────────────────────────────────────────────────


def export_boq_json(project: ArchitectureProject, output_path: Path) -> Path:
    """Write full BOQ + MaterialPlan as structured JSON. Returns output_path."""
    payload = {
        "project_id": project.id,
        "project_name": project.name,
        "cost_plan": project.cost_plan.model_dump(),
        "material_plan": project.material_plan.model_dump(),
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


# ── PDF / text summary export ─────────────────────────────────────────────────

_PDF_WIDTH  = 595   # A4 points
_PDF_HEIGHT = 842


def export_boq_pdf(project: ArchitectureProject, output_path: Path) -> Path:
    """Write a BOQ PDF summary. Falls back to a .txt file if reportlab unavailable."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas as rl_canvas
        _export_pdf_reportlab(project, output_path)
    except ImportError:
        _export_pdf_fallback_text(project, output_path.with_suffix(".txt"))
    return output_path


def _export_pdf_reportlab(project: ArchitectureProject, output_path: Path) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas

    cost = project.cost_plan
    c = rl_canvas.Canvas(str(output_path), pagesize=A4)
    W, H = A4
    y = H - 20 * mm

    def line(text: str, size: int = 9, bold: bool = False, indent: float = 0) -> None:
        nonlocal y
        font = "Helvetica-Bold" if bold else "Helvetica"
        c.setFont(font, size)
        c.drawString(20 * mm + indent, y, text)
        y -= (size + 3)
        if y < 20 * mm:
            c.showPage()
            nonlocal_reset()

    def nonlocal_reset() -> None:
        nonlocal y
        y = H - 20 * mm

    # Header
    line(f"Bill of Quantities — {project.name}", 13, bold=True)
    line(f"Advisory estimate  |  Confidence: {int(cost.confidence * 100)}%  |  Review before procurement", 8)
    y -= 4
    c.line(20 * mm, y, W - 20 * mm, y)
    y -= 8

    # Category totals
    line("Category Totals", 10, bold=True)
    for ct in cost.category_totals:
        label = ct.category.replace("_", " ").title()
        line(f"  {label}:  ₹{ct.total:,.0f}", 9)
    y -= 4
    c.line(20 * mm, y, W - 20 * mm, y)
    y -= 8
    line(f"Grand Total:  ₹{cost.grand_total:,.0f}", 11, bold=True)
    y -= 8

    # Missing rates
    if cost.missing_rates:
        line("Missing Rates (amounts excluded):", 9, bold=True)
        for mr in cost.missing_rates[:10]:
            line(f"  • {mr}", 8)
        y -= 4

    # Assumptions
    if cost.assumptions:
        line("Assumptions:", 9, bold=True)
        for a in cost.assumptions[:8]:
            line(f"  • {a}", 8)
        y -= 4

    # All items table
    line("Detailed Items", 10, bold=True)
    y -= 2
    headers = ["Category", "Description", "Unit", "Qty", "Rate", "Amount"]
    x_cols = [20 * mm, 45 * mm, 100 * mm, 120 * mm, 135 * mm, 158 * mm]
    c.setFont("Helvetica-Bold", 7)
    for i, h in enumerate(headers):
        c.drawString(x_cols[i], y, h)
    y -= 10
    c.setFont("Helvetica", 7)
    for item in cost.boq_items:
        if y < 20 * mm:
            c.showPage()
            y = H - 20 * mm
            c.setFont("Helvetica", 7)
        vals = [
            item.category,
            item.description[:38],
            item.unit,
            f"{item.quantity:.1f}",
            f"₹{item.rate:,.0f}" if item.rate else "—",
            f"₹{item.amount:,.0f}" if item.amount else "—",
        ]
        for i, v in enumerate(vals):
            c.drawString(x_cols[i], y, str(v))
        y -= 9

    c.save()


def _export_pdf_fallback_text(project: ArchitectureProject, output_path: Path) -> None:
    cost = project.cost_plan
    lines = [
        f"BILL OF QUANTITIES — {project.name}",
        f"Advisory estimate | Confidence: {int(cost.confidence * 100)}%",
        "=" * 60,
        "",
        "CATEGORY TOTALS:",
    ]
    for ct in cost.category_totals:
        lines.append(f"  {ct.category}: INR {ct.total:,.0f}")
    lines += ["", f"GRAND TOTAL: INR {cost.grand_total:,.0f}", ""]
    if cost.missing_rates:
        lines += ["MISSING RATES:"] + [f"  - {mr}" for mr in cost.missing_rates] + [""]
    if cost.assumptions:
        lines += ["ASSUMPTIONS:"] + [f"  - {a}" for a in cost.assumptions] + [""]
    lines += ["DETAILED ITEMS:", "-" * 60]
    for item in cost.boq_items:
        lines.append(
            f"{item.category:12s}  {item.description[:30]:30s}  "
            f"{item.unit:6s}  {item.quantity:8.1f}  "
            f"INR {item.rate:8.0f}  INR {item.amount:10.0f}"
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")
