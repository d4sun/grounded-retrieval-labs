"""Stage [3b] — turn a table into searchable text while keeping its structure.

The structured rows/cols stay in the unit's artefact (that's what we return). Here we
produce a *search_text* copy — markdown or ``col=value`` rows — including the table's
caption and nearby headings, so the table is findable. Cell text is whitespace-normalised
to undo the spacing/newline noise that PDF table extractors introduce.
"""

from __future__ import annotations

from ..config import Config
from ..logging_utils import get_logger
from ..provenance import Unit, UnitType

log = get_logger("grounded_retrieval.enrichment.linearise")


def _norm(cell: str) -> str:
    return " ".join(str(cell).split())


def _to_markdown(cells: list[list[str]]) -> str:
    if not cells:
        return ""
    width = max(len(r) for r in cells)
    rows = [[_norm(c) for c in r] + [""] * (width - len(r)) for r in cells]
    header = rows[0]
    lines = ["| " + " | ".join(header) + " |",
             "| " + " | ".join(["---"] * width) + " |"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def _to_kv(cells: list[list[str]]) -> str:
    if not cells:
        return ""
    header = [_norm(c) for c in cells[0]]
    out = []
    for r in cells[1:]:
        pairs = []
        for i, c in enumerate(r):
            col = header[i] if i < len(header) else f"col{i}"
            pairs.append(f"{col}={_norm(c)}")
        out.append("; ".join(pairs))
    return "\n".join(out)


def linearise_table(unit: Unit, style: str = "markdown") -> str:
    cells = unit.artefact.get("cells") or []
    caption = unit.meta.get("nearby_caption", "") or ""
    body = _to_kv(cells) if style == "kv" else _to_markdown(cells)
    parts = []
    if caption:
        parts.append(_norm(caption))
    parts.append(body)
    return "\n".join(p for p in parts if p).strip()


def linearise_units(units: list[Unit], cfg: Config) -> int:
    style = cfg.get("enrichment.tables.linearise", "markdown")
    n = 0
    for u in units:
        if u.unit_type is UnitType.TABLE:
            u.search_text = linearise_table(u, style=style)
            u.meta["linearise_style"] = style
            n += 1
    log.info("linearised %d tables (style=%s)", n, style)
    return n
