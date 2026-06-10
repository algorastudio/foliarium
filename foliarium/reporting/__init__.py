"""
foliarium.reporting — Layer di reportistica (PDF, in futuro export tabellari).
"""

from foliarium.reporting.pdf import (
    FPDF_AVAILABLE,
    ModernCatastoPDF,
    PDFPartita,
    PDFPossessore,
    GenericTextReportPDF,
    BulkReportPDF,
)

__all__ = [
    "FPDF_AVAILABLE",
    "ModernCatastoPDF",
    "PDFPartita",
    "PDFPossessore",
    "GenericTextReportPDF",
    "BulkReportPDF",
]
