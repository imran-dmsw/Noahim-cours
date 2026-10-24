"""Export PDF des fiches (fpdf2, aucune dépendance système)."""
from __future__ import annotations

import re

from fpdf import FPDF

# Les polices intégrées du PDF ne connaissent que le latin-1 :
# on remplace les symboles courants par un équivalent lisible.
REPLACEMENTS = {
    "→": "->", "⇒": "=>", "⇔": "<=>", "←": "<-", "≤": "<=", "≥": ">=", "≠": "!=",
    "≈": "~", "∞": "infini", "√": "racine", "π": "pi", "Δ": "Delta", "δ": "delta",
    "θ": "theta", "λ": "lambda", "α": "alpha", "β": "beta", "ω": "omega", "Ω": "Ohm",
    "∈": " appartient a ", "∑": "somme", "−": "-", "–": "-", "—": "-", "’": "'",
    "‘": "'", "“": '"', "”": '"', "…": "...", "•": "-", "₀": "0", "₁": "1",
    "₂": "2", "₃": "3", "ⁿ": "^n", "⁻": "-", "€": "EUR", "œ": "oe", "Œ": "OE",
}
# Couleurs de la charte (RVB)
ACCENT = (26, 130, 212)
DARK = (13, 27, 42)
GREY = (90, 100, 115)


def _clean(text: str) -> str:
    for src, dst in REPLACEMENTS.items():
        text = text.replace(src, dst)
    # Emojis et autres caractères hors latin-1 : supprimés.
    text = text.encode("latin-1", "ignore").decode("latin-1")
    return text.strip()


def _strip_md(text: str) -> str:
    """Retire le gras / italique Markdown (le PDF reste simple et lisible)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"\1", text)
    return text.replace("`", "")


def fiche_to_pdf(markdown: str) -> bytes:
    """Convertit le Markdown d'une fiche en PDF (titres, listes, questions flash)."""
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(18, 18, 18)
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    for raw in markdown.splitlines():
        line = raw.rstrip()
        if not line.strip():
            pdf.ln(2)
            continue
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(width, 9, _clean(_strip_md(line[2:])))
            pdf.set_draw_color(*ACCENT)
            pdf.set_line_width(0.8)
            pdf.line(pdf.l_margin, pdf.get_y() + 1, pdf.l_margin + 40, pdf.get_y() + 1)
            pdf.ln(4)
        elif line.startswith("## ") or line.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 13)
            pdf.set_text_color(*ACCENT)
            pdf.multi_cell(width, 7, _clean(_strip_md(line.lstrip("#").strip())))
            pdf.ln(1)
        elif re.match(r"^\s*[-*]\s+", line):
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*DARK)
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(width - 4, 6, "- " + _clean(_strip_md(re.sub(r"^\s*[-*]\s+", "", line))))
        elif re.match(r"^\s*Q\d*\s*:", line):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*DARK)
            pdf.multi_cell(width, 6, _clean(_strip_md(line)))
        elif re.match(r"^\s*R\s*:", line):
            pdf.set_font("Helvetica", "I", 11)
            pdf.set_text_color(*GREY)
            pdf.set_x(pdf.l_margin + 4)
            pdf.multi_cell(width - 4, 6, _clean(_strip_md(line)))
        else:
            pdf.set_font("Helvetica", "I" if line.startswith("*") else "", 11)
            pdf.set_text_color(*(GREY if line.startswith("*") else DARK))
            pdf.multi_cell(width, 6, _clean(_strip_md(line)))

    pdf.set_y(-15)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 6, "Noahim Revise", align="C")
    return bytes(pdf.output())
