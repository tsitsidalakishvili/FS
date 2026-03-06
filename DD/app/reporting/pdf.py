from pathlib import Path
from typing import Iterable


def generate_pdf_report(
    output_path: Path, title: str, sections: Iterable[tuple[str, list[str]]]
) -> None:
    try:
        from fpdf import FPDF
    except ImportError as exc:
        raise RuntimeError(
            "PDF export requires 'fpdf2'. Install with: pip install fpdf2"
        ) from exc

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True)

    for section_title, lines in sections:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, section_title, ln=True)
        pdf.set_font("Helvetica", size=11)
        if not lines:
            pdf.cell(0, 6, "No data available.", ln=True)
        else:
            for line in lines:
                pdf.multi_cell(0, 6, line)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
