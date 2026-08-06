"""Printable QR ID cards (PROMPT.md §6.4A): reportlab + qrcode, laid out in a
grid so a school can actually print and cut them. Each card's QR encodes the
same `qr_token` the seed data and the admission-form commit path already
derive via `security.qr_token_for` -- the kiosk scanner (POST
/attendance/scan) looks students up by that exact field.
"""

from __future__ import annotations

import io

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.db.models import ClassSection, Student

CARD_WIDTH = 85 * mm
CARD_HEIGHT = 54 * mm
MARGIN = 10 * mm
COLS = 2
ROWS = 4


def _class_label(sections: dict[int, ClassSection], class_id: int) -> str:
    section = sections.get(class_id)
    return f"{section.grade}-{section.section}" if section else "?"


def generate_id_cards_pdf(students: list[Student], sections: dict[int, ClassSection]) -> bytes:
    buffer = io.BytesIO()
    _, page_height = A4
    c = canvas.Canvas(buffer, pagesize=A4)

    per_page = COLS * ROWS
    for i, student in enumerate(students):
        slot = i % per_page
        if slot == 0 and i > 0:
            c.showPage()
        col = slot % COLS
        row = slot // COLS

        x = MARGIN + col * (CARD_WIDTH + MARGIN)
        y = page_height - MARGIN - (row + 1) * CARD_HEIGHT - row * MARGIN

        c.roundRect(x, y, CARD_WIDTH, CARD_HEIGHT, 4 * mm, stroke=1, fill=0)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(x + 4 * mm, y + CARD_HEIGHT - 8 * mm, "Shaala Public School")
        c.setFont("Helvetica", 10)
        c.drawString(x + 4 * mm, y + CARD_HEIGHT - 16 * mm, student.name)
        c.setFont("Helvetica", 8)
        label = _class_label(sections, student.class_id)
        c.drawString(x + 4 * mm, y + CARD_HEIGHT - 22 * mm, f"{label} · Roll {student.roll_no}")
        c.drawString(x + 4 * mm, y + CARD_HEIGHT - 27 * mm, student.admission_no)

        qr_img = qrcode.make(student.qr_token)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        qr_size = 28 * mm
        c.drawImage(
            ImageReader(qr_buffer),
            x + CARD_WIDTH - qr_size - 4 * mm,
            y + 4 * mm,
            width=qr_size,
            height=qr_size,
        )

    c.save()
    return buffer.getvalue()
