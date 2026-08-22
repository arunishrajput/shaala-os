"""Timetable export to PDF (PROMPT.md §8: GET /timetable/export.pdf).

Generates a printable landscape-A4 grid — one page per class section or per
teacher. Mirrors the reportlab style already established in id_cards.py.

Grid orientation: days as rows (Mon–Sat), periods as columns (1–8). Each
cell shows the subject, the counterpart entity (teacher name in class-view;
class label in teacher-view), and the room. Empty cells are left blank so
the printed sheet also works as a manual-entry fallback.

Returns valid PDF bytes even when no active timetable exists — the caller
gets a single informative page rather than an exception, per the "never an
error screen on the live URL" contract in PROMPT.md §11.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.db.models import TimetableEntry
from app.services.timetable.solver import SolveInput

# ── Layout constants (landscape A4 = 297 × 210 mm) ───────────────────────────
_W, _H = landscape(A4)
_M = 12 * mm           # page margin (all sides)
_HEADER_H = 18 * mm    # title-bar height
_FOOTER_H = 8 * mm     # footer clearance
_PERIOD_ROW_H = 9 * mm # period-number header row height
_DAY_COL_W = 22 * mm   # day-label column width

# Derived y-coordinates (reportlab origin = bottom-left)
_GRID_TOP = _H - _M - _HEADER_H          # top of the grid (bottom of title bar)
_GRID_BOT = _M + _FOOTER_H               # bottom of the grid
_GRID_LEFT = _M + _DAY_COL_W             # left edge of the period columns
_GRID_RIGHT = _W - _M                    # right edge of the grid

_COL_W = (_GRID_RIGHT - _GRID_LEFT) / 8  # width of one period column (8 periods)
_ROW_H = (_GRID_TOP - _PERIOD_ROW_H - _GRID_BOT) / 6  # height of one day row (6 days)

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

# ── Palette (matches theme.dart AppColors) ────────────────────────────────────
_SLATE_900 = colors.HexColor("#0F172A")
_SLATE_800 = colors.HexColor("#1E293B")
_SLATE_700 = colors.HexColor("#334155")
_SLATE_600 = colors.HexColor("#475569")
_SLATE_100 = colors.HexColor("#F1F5F9")
_SLATE_50 = colors.HexColor("#F8FAFC")
_SLATE_LINE = colors.HexColor("#CBD5E1")
_INDIGO = colors.HexColor("#6366F1")
_WHITE = colors.white
_TEXT_MAIN = colors.HexColor("#0F172A")
_TEXT_SUB = colors.HexColor("#475569")
_TEXT_LIGHT = colors.white
_TEXT_FAINT = colors.HexColor("#94A3B8")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _draw_header(c: canvas.Canvas, title: str, subtitle: str) -> None:
    """Slate title bar with school name, entity title, and timestamp."""
    c.setFillColor(_SLATE_800)
    c.rect(_M, _GRID_TOP, _W - 2 * _M, _HEADER_H, fill=1, stroke=0)

    # School name — left
    c.setFillColor(_TEXT_LIGHT)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(_M + 5 * mm, _GRID_TOP + _HEADER_H * 0.58, "Shaala Public School")

    # Entity title — left, below school name
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.drawString(_M + 5 * mm, _GRID_TOP + _HEADER_H * 0.22, title)

    # Timestamp — right
    c.setFont("Helvetica", 8)
    c.drawRightString(_W - _M - 5 * mm, _GRID_TOP + _HEADER_H * 0.4, subtitle)


def _draw_grid_frame(c: canvas.Canvas) -> None:
    """Draw the period-header row, day-label column, and all cell borders."""
    # ── Period header row (indigo band) ───────────────────────────────────────
    c.setFillColor(_INDIGO)
    c.rect(_M, _GRID_TOP - _PERIOD_ROW_H, _W - 2 * _M, _PERIOD_ROW_H, fill=1, stroke=0)

    # Top-left corner cell (above day labels)
    c.setFillColor(_SLATE_800)
    c.rect(_M, _GRID_TOP - _PERIOD_ROW_H, _DAY_COL_W, _PERIOD_ROW_H, fill=1, stroke=0)

    # Period numbers
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(_TEXT_LIGHT)
    for p in range(8):
        cx = _GRID_LEFT + p * _COL_W + _COL_W / 2
        cy = _GRID_TOP - _PERIOD_ROW_H + _PERIOD_ROW_H * 0.33
        c.drawCentredString(cx, cy, f"P {p + 1}")

    # ── Day rows ──────────────────────────────────────────────────────────────
    for d in range(6):
        row_top = _GRID_TOP - _PERIOD_ROW_H - d * _ROW_H
        row_bot = row_top - _ROW_H

        # Day label cell — alternating slate shades
        c.setFillColor(_SLATE_700 if d % 2 == 0 else _SLATE_600)
        c.rect(_M, row_bot, _DAY_COL_W, _ROW_H, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(_TEXT_LIGHT)
        c.drawCentredString(_M + _DAY_COL_W / 2, row_bot + _ROW_H * 0.38, DAYS[d])

        # Period cells — subtle alternating tint
        for p in range(8):
            cx = _GRID_LEFT + p * _COL_W
            c.setFillColor(_SLATE_50 if p % 2 == 0 else _WHITE)
            c.rect(cx, row_bot, _COL_W, _ROW_H, fill=1, stroke=0)

    # ── Grid lines ────────────────────────────────────────────────────────────
    c.setStrokeColor(_SLATE_LINE)
    c.setLineWidth(0.5)

    # Horizontal row separators
    for d in range(1, 6):
        y = _GRID_TOP - _PERIOD_ROW_H - d * _ROW_H
        c.line(_M, y, _W - _M, y)

    # Vertical column separators (period columns only — start below header row)
    for p in range(1, 8):
        x = _GRID_LEFT + p * _COL_W
        c.line(x, _GRID_TOP - _PERIOD_ROW_H, x, _GRID_BOT)

    # Separator between day-label column and period columns
    c.setLineWidth(1)
    c.setStrokeColor(_SLATE_700)
    c.line(_GRID_LEFT, _GRID_TOP - _PERIOD_ROW_H, _GRID_LEFT, _GRID_BOT)

    # Outer border
    c.setStrokeColor(_SLATE_LINE)
    c.setLineWidth(1)
    c.rect(_M, _GRID_BOT, _W - 2 * _M, _GRID_TOP - _GRID_BOT, stroke=1, fill=0)


def _draw_cell(
    c: canvas.Canvas,
    day: int,
    period: int,  # 1-indexed
    line1: str,
    line2: str,
    line3: str,
    is_sub: bool = False,
) -> None:
    """Write three lines of text into the (day, period) cell.

    line1 = subject name (bold)
    line2 = teacher / class (regular)
    line3 = room (faint)
    is_sub = True marks the cell with an amber left-edge (substitution).
    """
    x = _GRID_LEFT + (period - 1) * _COL_W
    y_bot = _GRID_TOP - _PERIOD_ROW_H - (day + 1) * _ROW_H
    pad = 2.5 * mm

    if is_sub:
        c.setFillColor(colors.HexColor("#F59E0B"))  # amber accent
        c.rect(x, y_bot, 1.5 * mm, _ROW_H, fill=1, stroke=0)

    # Subject name
    c.setFillColor(_TEXT_MAIN)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x + pad + (2 * mm if is_sub else 0), y_bot + _ROW_H * 0.60, _truncate(line1, _COL_W - pad * 2))

    # Teacher / class
    c.setFont("Helvetica", 7)
    c.setFillColor(_TEXT_SUB)
    c.drawString(x + pad + (2 * mm if is_sub else 0), y_bot + _ROW_H * 0.38, _truncate(line2, _COL_W - pad * 2))

    # Room
    c.setFont("Helvetica", 6.5)
    c.setFillColor(_TEXT_FAINT)
    c.drawString(x + pad + (2 * mm if is_sub else 0), y_bot + _ROW_H * 0.16, _truncate(line3, _COL_W - pad * 2))


def _truncate(text: str, max_width: float, font: str = "Helvetica", size: float = 7) -> str:
    """Shorten text to fit within max_width points (approximate — 1 char ≈ size * 0.55 pt)."""
    char_w = size * 0.55
    limit = max(1, int(max_width / char_w))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _footer(c: canvas.Canvas, page_num: int, total: int) -> None:
    c.setFont("Helvetica", 7)
    c.setFillColor(_TEXT_FAINT)
    c.drawCentredString(_W / 2, _M + 2 * mm, f"Page {page_num} of {total}")


# ── Public API ────────────────────────────────────────────────────────────────

def generate_timetable_pdf(
    entries: list[TimetableEntry],
    si: SolveInput,
    view: str = "class",  # "class" | "teacher"
    entity_id: int | None = None,
) -> bytes:
    """Generate a printable timetable PDF.

    view="class"   → one page per class section; cells show subject / teacher / room.
    view="teacher" → one page per teacher;        cells show subject / class  / room.

    If entity_id is given, only one page is generated for that specific entity.
    If entries is empty, a single informative page is returned instead of an
    empty PDF.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))

    generated_at = datetime.now().strftime("%d %b %Y %H:%M")

    if not entries:
        _no_timetable_page(c, generated_at)
        c.save()
        return buffer.getvalue()

    # Group entries by the entity being rendered
    if view == "class":
        entities = sorted(si.sections, key=lambda s: (s.grade, s.section))
        if entity_id is not None:
            entities = [s for s in entities if s.id == entity_id]

        total = len(entities)
        for page_num, section in enumerate(entities, 1):
            section_entries = [e for e in entries if e.class_id == section.id]
            title = f"Class {section.grade}-{section.section}"
            subtitle = f"Generated {generated_at}"

            _draw_header(c, title, subtitle)
            _draw_grid_frame(c)

            for entry in section_entries:
                slot = si.slots_by_id[entry.slot_id]
                teacher = si.teachers_by_id[entry.teacher_id]
                subject = si.subjects_by_id[entry.subject_id]
                room = si.rooms_by_id[entry.room_id]
                _draw_cell(
                    c,
                    day=slot.day,
                    period=slot.period,
                    line1=subject.name,
                    line2=teacher.name,
                    line3=room.name,
                    is_sub=entry.is_substitution,
                )

            _footer(c, page_num, total)
            if page_num < total:
                c.showPage()

    else:  # view == "teacher"
        teachers = sorted(si.teachers, key=lambda t: t.name)
        if entity_id is not None:
            teachers = [t for t in teachers if t.id == entity_id]

        total = len(teachers)
        for page_num, teacher in enumerate(teachers, 1):
            teacher_entries = [e for e in entries if e.teacher_id == teacher.id]
            title = f"Teacher: {teacher.name}  ·  {teacher.dept}"
            subtitle = f"Generated {generated_at}"

            _draw_header(c, title, subtitle)
            _draw_grid_frame(c)

            for entry in teacher_entries:
                slot = si.slots_by_id[entry.slot_id]
                section = si.sections_by_id[entry.class_id]
                subject = si.subjects_by_id[entry.subject_id]
                room = si.rooms_by_id[entry.room_id]
                _draw_cell(
                    c,
                    day=slot.day,
                    period=slot.period,
                    line1=subject.name,
                    line2=f"{section.grade}-{section.section}",
                    line3=room.name,
                    is_sub=entry.is_substitution,
                )

            _footer(c, page_num, total)
            if page_num < total:
                c.showPage()

    c.save()
    return buffer.getvalue()


def _no_timetable_page(c: canvas.Canvas, generated_at: str) -> None:
    """Single informative page when no active timetable exists."""
    _draw_header(c, "Timetable Export", f"Generated {generated_at}")
    c.setFont("Helvetica", 13)
    c.setFillColor(_TEXT_SUB)
    c.drawCentredString(
        _W / 2,
        _H / 2 + 6 * mm,
        "No active timetable found.",
    )
    c.setFont("Helvetica", 10)
    c.drawCentredString(
        _W / 2,
        _H / 2 - 6 * mm,
        "Generate a timetable first, then export.",
    )
