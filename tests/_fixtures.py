"""Shared test fixtures: build a tiny synthetic technical manual PDF in-memory.

Uses only PyMuPDF (a core dep) so tests run with the light install. The generated
PDF has, deterministically:

  page 1 — prose only (routing: text)
  page 2 — an embedded figure with a "Figure 1" caption, and a gridded table with
           a "Table 1" caption (routing: figure + table)

This gives the parsing/extraction/indexing tests real regions to find without
needing any downloaded corpus.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _solid_png(width: int = 160, height: int = 120, rgb=(40, 90, 160)) -> bytes:
    """Minimal valid PNG of a solid colour — avoids a Pillow/numpy dependency."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    row = b"\x00" + bytes(rgb) * width
    raw = row * height
    idat = zlib.compress(raw, 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def make_test_pdf(path: str | Path) -> Path:
    try:
        import pymupdf as fitz
    except Exception:  # pragma: no cover
        import fitz

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    # --- page 1: prose ---
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((72, 90), "Chapter 4 — Electrical Systems", fontsize=16)
    prose = (
        "The aircraft electrical system distributes power from the battery and "
        "generator to the avionics and lighting buses. A relay control circuit "
        "isolates faults so that a short in one bus does not de-energise the others. "
        "Routine maintenance includes checking torque on the main bus terminals and "
        "verifying continuity across the master relay. Fault code E-214 indicates an "
        "open master relay coil and is covered later in this chapter."
    )
    y = 130
    for line in _wrap(prose, 92):
        p1.insert_text((72, y), line, fontsize=11)
        y += 16

    # --- page 2: figure + table ---
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((72, 80), "4.3 Relay Control Wiring", fontsize=14)

    # embedded figure
    img = _solid_png()
    rect = fitz.Rect(72, 110, 320, 300)
    p2.insert_image(rect, stream=img)
    p2.insert_text((72, 316), "Figure 4-12. Relay control wiring diagram (master bus).",
                   fontsize=10)

    # gridded table: header + 3 rows, 3 cols, drawn with lines so find_tables sees it
    tx, ty = 72, 380
    col_w, row_h = 150, 26
    headers = ["Terminal", "Torque (in-lb)", "Fault code"]
    rows = [
        ["Main bus A", "25", "E-214"],
        ["Main bus B", "25", "E-215"],
        ["Ground stud", "18", "E-220"],
    ]
    table = [headers] + rows
    for r, record in enumerate(table):
        for c, val in enumerate(record):
            x = tx + c * col_w
            yy = ty + r * row_h
            p2.draw_rect(fitz.Rect(x, yy, x + col_w, yy + row_h), color=(0, 0, 0), width=0.6)
            p2.insert_text((x + 4, yy + 17), val, fontsize=9)
    p2.insert_text((tx, ty + len(table) * row_h + 16),
                   "Table 4-1. Bus terminal torque and fault codes.", fontsize=10)

    doc.save(str(path))
    doc.close()
    return path


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines
