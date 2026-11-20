"""Generate a tiny synthetic technical manual + gold questions.

This stands in for "download a DUDE/MP-DocVQA slice + an FAA handbook" so the lab's
smoke test is hermetic: no network, no licence, no GPU. The generated PDF has prose,
figures (with captions), and a gridded table across a few pages, and the gold questions
carry page-level evidence labels — exactly the shape the evaluator expects. Swap in a
real corpus by dropping PDFs in ``data/raw`` and pointing ``corpus.input_dir`` at it.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

from .evaluation.dataset import GoldQuestion, save_gold


def _png(width: int, height: int, rgb) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * width
    idat = zlib.compress(row * height, 9)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def _prose(page, x, y, text, size=11, lead=16, width=92):
    for line in _wrap(text, width):
        page.insert_text((x, y), line, fontsize=size)
        y += lead
    return y


def _table(page, x, y, table, col_w=150, row_h=26):
    try:
        import pymupdf as fitz
    except Exception:
        import fitz
    for r, record in enumerate(table):
        for c, val in enumerate(record):
            xx, yy = x + c * col_w, y + r * row_h
            page.draw_rect(fitz.Rect(xx, yy, xx + col_w, yy + row_h), color=(0, 0, 0), width=0.6)
            page.insert_text((xx + 4, yy + 17), str(val), fontsize=9)
    return y + len(table) * row_h


def build_sample_corpus(out_dir: str | Path) -> tuple[list[Path], Path]:
    """Write the sample PDF(s) + gold_questions.json into *out_dir*. Returns (pdfs, gold_path)."""
    try:
        import pymupdf as fitz
    except Exception:
        import fitz

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = out_dir / "amt_handbook_excerpt.pdf"
    doc = fitz.open()

    # --- page 1: prose (electrical) ---
    p1 = doc.new_page(width=612, height=792)
    p1.insert_text((72, 90), "Chapter 4 — Electrical Systems", fontsize=16)
    _prose(p1, 72, 128,
           "The aircraft electrical system distributes power from the battery and generator "
           "to the avionics and lighting buses. A relay control circuit isolates faults so a "
           "short in one bus does not de-energise the others. Fault code E-214 indicates an "
           "open master relay coil. Routine maintenance includes checking torque on the main "
           "bus terminals and verifying continuity across the master relay.")

    # --- page 2: figure + table (wiring + torque/fault codes) ---
    p2 = doc.new_page(width=612, height=792)
    p2.insert_text((72, 80), "4.3 Relay Control Wiring", fontsize=14)
    p2.insert_image(fitz.Rect(72, 104, 330, 300), stream=_png(160, 120, (40, 90, 160)))
    p2.insert_text((72, 316), "Figure 4-12. Relay control wiring diagram (master bus).", fontsize=10)
    yy = _table(p2, 72, 360, [
        ["Terminal", "Torque in-lb", "Fault code"],
        ["Main bus A", "25", "E214"],
        ["Main bus B", "25", "E215"],
        ["Ground stud", "18", "E220"],
    ])
    p2.insert_text((72, yy + 18), "Table 4-1. Bus terminal torque and fault codes.", fontsize=10)

    # --- page 3: prose + exploded-view figure (hydraulics) ---
    p3 = doc.new_page(width=612, height=792)
    p3.insert_text((72, 80), "Chapter 7 — Hydraulic Actuators", fontsize=16)
    _prose(p3, 72, 118,
           "The landing gear actuator converts hydraulic pressure into linear motion to "
           "extend and retract the gear. Service the actuator by relieving system pressure, "
           "removing the retaining ring, and inspecting the piston seal for scoring.")
    p3.insert_image(fitz.Rect(72, 210, 330, 420), stream=_png(160, 130, (150, 70, 40)))
    p3.insert_text((72, 436), "Figure 7-3. Exploded view of the landing gear actuator.", fontsize=10)

    doc.save(str(pdf_path))
    doc.close()

    gold = [
        GoldQuestion("q1", "relay control wiring diagram for the master bus",
                     "figure", "amt_handbook_excerpt", [2]),
        GoldQuestion("q2", "bus terminal torque values and fault codes table",
                     "table", "amt_handbook_excerpt", [2]),
        GoldQuestion("q3", "what does fault code E-214 indicate",
                     "text", "amt_handbook_excerpt", [1]),
        GoldQuestion("q4", "exploded view of the landing gear actuator",
                     "figure", "amt_handbook_excerpt", [3]),
        GoldQuestion("q5", "how to service the landing gear hydraulic actuator",
                     "text", "amt_handbook_excerpt", [3]),
    ]
    gold_path = out_dir / "gold_questions.json"
    save_gold(gold, gold_path)
    return [pdf_path], gold_path
