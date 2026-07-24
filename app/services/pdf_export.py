"""Conversation history -> PDF, shared by both frontends (Streamlit and the
Catalyst-native HTML UI). Server-side so neither frontend needs its own
PDF/font toolchain."""

import os
from datetime import datetime

from fpdf import FPDF

FONT_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts", "NotoSansKannada.ttf")


def build_conversation_pdf(conversation: list[dict]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("Noto", "", FONT_PATH)
    pdf.set_font("Noto", size=16)
    pdf.cell(0, 10, "KAVAL AI — Conversation History", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Noto", size=9)
    pdf.cell(0, 6, datetime.now().strftime("Generated %Y-%m-%d %H:%M"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for i, turn in enumerate(conversation, 1):
        pdf.set_font("Noto", size=12)
        pdf.multi_cell(0, 7, f"Q{i}: {turn['question']}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Noto", size=11)
        pdf.multi_cell(0, 6, f"A{i}: {turn['answer']}", new_x="LMARGIN", new_y="NEXT")
        if turn.get("sql"):
            pdf.set_font("Noto", size=8)
            pdf.multi_cell(0, 5, f"SQL: {turn['sql']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
    return bytes(pdf.output())
