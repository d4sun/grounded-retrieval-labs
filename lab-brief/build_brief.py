#!/usr/bin/env python3
"""Build the Course 3 · Day 2 · Lab A participant brief as a self-contained HTML file.

Diagrams are generated as inline SVG; the HTML is rendered to PDF with headless Chrome.
"""
from __future__ import annotations
import html, pathlib

OUT = pathlib.Path(__file__).resolve().parent
INK = "#1d2330"; BODY = "#2b313c"; MUTE = "#5b6472"
INDIGO = "#4f46e5"; TEAL = "#0d9488"; AMBER = "#b45309"; ROSE = "#be123c"
LINE = "#d7dbe3"; CARD = "#f6f7f9"; BADGE = "#eef0fb"

# --------------------------------------------------------------------------- #
# Diagram 1 — reference architecture (vertical pipeline + provenance rail)
# --------------------------------------------------------------------------- #
def diagram_pipeline() -> str:
    stages = [
        ("1", "Parse &amp; route", "PDF → text / figure / table regions + page numbers; scanned pages → OCR behind a quality gate"),
        ("2", "Extract", "figure crops + structured tables — each stamped doc→page→id"),
        ("3", "Enrich", "caption figures (vision model) · linearise tables → searchable text"),
        ("4", "Embed &amp; index", "one index over text + figure-caption + table-text; provenance in metadata"),
        ("5", "Retrieve", "vector search (+ optional BM25 fusion for exact identifiers)"),
        ("6", "Answer", "decide text / figure / table → return the REAL artefact + page citation (fail-closed)"),
        ("7", "Evaluate", "recall@k + MRR broken out BY TYPE · faithfulness spot-check"),
    ]
    x, w, h, gap, top = 16, 540, 54, 20, 16
    W = 680; H = top + len(stages) * (h + gap) - gap + 16
    parts = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Inter,Arial,sans-serif">']
    # provenance rail
    rail_x = x + w + 24
    parts.append(f'<rect x="{rail_x}" y="{top}" width="18" height="{len(stages)*(h+gap)-gap}" rx="9" fill="{TEAL}" opacity="0.14"/>')
    parts.append(f'<rect x="{rail_x+5}" y="{top}" width="8" height="{len(stages)*(h+gap)-gap}" rx="4" fill="{TEAL}" opacity="0.5"/>')
    parts.append(f'<text x="{rail_x+9}" y="{top + (len(stages)*(h+gap)-gap)/2}" transform="rotate(90 {rail_x+9} {top + (len(stages)*(h+gap)-gap)/2})" text-anchor="middle" fill="{TEAL}" font-size="12" font-weight="700" letter-spacing="1">doc → page → id  provenance carried end-to-end</text>')
    for i, (n, title, desc) in enumerate(stages):
        y = top + i * (h + gap)
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="#ffffff" stroke="{LINE}"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="6" height="{h}" rx="3" fill="{INDIGO}"/>')
        parts.append(f'<circle cx="{x+30}" cy="{y+h/2}" r="14" fill="{BADGE}"/>')
        parts.append(f'<text x="{x+30}" y="{y+h/2+5}" text-anchor="middle" fill="{INDIGO}" font-size="15" font-weight="700">{n}</text>')
        parts.append(f'<text x="{x+56}" y="{y+22}" fill="{INK}" font-size="14.5" font-weight="700">{title}</text>')
        parts.append(f'<text x="{x+56}" y="{y+40}" fill="{MUTE}" font-size="11.5">{desc}</text>')
        if i < len(stages) - 1:
            ay = y + h + gap / 2
            parts.append(f'<path d="M{x+w/2} {y+h} L{x+w/2} {ay+6}" stroke="{INDIGO}" stroke-width="2" marker-end="url(#ah)"/>')
    parts.append(f'<defs><marker id="ah" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{INDIGO}"/></marker></defs>')
    parts.append('</svg>')
    return "".join(parts)

# --------------------------------------------------------------------------- #
# Diagram 2 — the Unit data model (retrieve-by-text / answer-with-artefact)
# --------------------------------------------------------------------------- #
def diagram_unit() -> str:
    W, H = 680, 300
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Inter,Arial,sans-serif">']
    # Unit container
    p.append(f'<rect x="20" y="16" width="640" height="200" rx="12" fill="{CARD}" stroke="{LINE}"/>')
    p.append(f'<text x="40" y="44" fill="{INK}" font-size="15" font-weight="700">Unit</text>')
    p.append(f'<text x="80" y="44" fill="{MUTE}" font-size="11.5">— the atom of retrieval (type: text | figure | table)</text>')
    # search_text column
    p.append(f'<rect x="40" y="58" width="280" height="110" rx="9" fill="#fff" stroke="{INDIGO}" stroke-opacity="0.4"/>')
    p.append(f'<text x="56" y="82" fill="{INDIGO}" font-size="12.5" font-weight="700">search_text  — what we EMBED</text>')
    for i, t in enumerate(["text → the prose chunk", "figure → the vision caption", "table → the linearised rows"]):
        p.append(f'<text x="56" y="{104+i*20}" fill="{BODY}" font-size="11.5">• {t}</text>')
    # artefact column
    p.append(f'<rect x="360" y="58" width="280" height="110" rx="9" fill="#fff" stroke="{TEAL}" stroke-opacity="0.5"/>')
    p.append(f'<text x="376" y="82" fill="{TEAL}" font-size="12.5" font-weight="700">artefact  — what we RETURN</text>')
    for i, t in enumerate(["text → the text span", "figure → the real image file", "table → the structured cells"]):
        p.append(f'<text x="376" y="{104+i*20}" fill="{BODY}" font-size="11.5">• {t}</text>')
    # provenance strip
    p.append(f'<rect x="40" y="180" width="600" height="26" rx="7" fill="{TEAL}" opacity="0.10"/>')
    p.append(f'<text x="56" y="197" fill="{TEAL}" font-size="12" font-weight="700">provenance: doc_id → page → unit_id (+ bbox)</text>')
    p.append(f'<text x="330" y="197" fill="{MUTE}" font-size="11">— no resolvable page ⇒ not a sourced answer (fail closed)</text>')
    # arrows out
    p.append(f'<text x="120" y="250" fill="{INDIGO}" font-size="11.5" font-weight="600">↓ indexed &amp; searched</text>')
    p.append(f'<text x="470" y="250" fill="{TEAL}" font-size="11.5" font-weight="600">↓ handed back to the user</text>')
    p.append(f'<path d="M180 214 L180 236" stroke="{INDIGO}" stroke-width="2" marker-end="url(#ah2)"/>')
    p.append(f'<path d="M520 214 L520 236" stroke="{TEAL}" stroke-width="2" marker-end="url(#ah3)"/>')
    p.append(f'<text x="20" y="286" fill="{MUTE}" font-size="11">Retrieve-by-text, answer-with-artefact: we search a description, but hand back the original figure/table, linked by provenance.</text>')
    p.append(f'<defs><marker id="ah2" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{INDIGO}"/></marker>'
             f'<marker id="ah3" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{TEAL}"/></marker></defs>')
    p.append('</svg>')
    return "".join(p)

# --------------------------------------------------------------------------- #
# Diagram 3 — answer flow (decision + fail-closed)
# --------------------------------------------------------------------------- #
def diagram_answer() -> str:
    W, H = 680, 250
    p = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="Inter,Arial,sans-serif">']
    def box(x, y, w, h, fill, stroke, title, sub=""):
        s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{stroke}"/>'
        s += f'<text x="{x+w/2}" y="{y+ (22 if sub else h/2+4)}" text-anchor="middle" fill="{INK}" font-size="12.5" font-weight="700">{title}</text>'
        if sub:
            s += f'<text x="{x+w/2}" y="{y+40}" text-anchor="middle" fill="{MUTE}" font-size="10.5">{sub}</text>'
        return s
    p.append(box(20, 100, 120, 50, "#fff", LINE, "Query"))
    p.append(box(170, 100, 130, 50, "#fff", LINE, "Retrieve", "top-k by text"))
    p.append(box(330, 92, 150, 66, CARD, INDIGO, "Decide type", "of top SOURCED hit"))
    # three outputs
    p.append(box(520, 20, 140, 46, "#fff", TEAL, "Figure", "image + page"))
    p.append(box(520, 100, 140, 46, "#fff", TEAL, "Table", "rows + page"))
    p.append(box(520, 180, 140, 46, "#fff", TEAL, "Text", "span + page"))
    # fail-closed note
    p.append(f'<rect x="330" y="176" width="150" height="46" rx="9" fill="#fff" stroke="{ROSE}" stroke-dasharray="4 3"/>')
    p.append(f'<text x="405" y="197" text-anchor="middle" fill="{ROSE}" font-size="11.5" font-weight="700">no provenance?</text>')
    p.append(f'<text x="405" y="213" text-anchor="middle" fill="{ROSE}" font-size="10.5">abstain (fail closed)</text>')
    arr = lambda x1,y1,x2,y2,c=INDIGO: f'<path d="M{x1} {y1} L{x2} {y2}" stroke="{c}" stroke-width="2" marker-end="url(#ha)"/>'
    p.append(arr(140,125,168,125)); p.append(arr(300,125,328,125))
    p.append(arr(480,120,518,45,TEAL)); p.append(arr(480,122,518,122,TEAL)); p.append(arr(480,128,518,200,TEAL))
    p.append(arr(405,158,405,174,ROSE))
    p.append(f'<defs><marker id="ha" markerWidth="9" markerHeight="9" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="{INDIGO}"/></marker></defs>')
    p.append('</svg>')
    return "".join(p)

print("diagrams generated:",
      len(diagram_pipeline()), len(diagram_unit()), len(diagram_answer()))

# --------------------------------------------------------------------------- #
# Backlog data (epics -> stories / tasks / done). Guidance, not hard rules.
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #
# Backlog: epics -> user stories, each with what-to-do + acceptance.
# Guidance, not hard rules. The acceptance lines encode the non-negotiables.
# --------------------------------------------------------------------------- #
EPICS = [
 dict(id="E0", title="Environment &amp; corpus", stage="setup",
   goal="Stand up a free, reproducible workspace and get a small multimodal corpus that ships evaluation gold.",
   stories=[
     dict(title="As an engineer, I want a one-command, free setup so anyone can reproduce the lab with no billing wall.",
       do=["Create a virtualenv; keep a light core (parsing + index) so the offline path installs fast — no torch/CUDA required to start.",
           "Make every model swappable free↔local from one config file; keep no paid key on the default path.",
           "Expose a single `smoke` command that runs ingest→answer→evaluate end-to-end with no network."],
       acc=["A fresh clone installs and runs the smoke path with no API key and no GPU."]),
     dict(title="As an engineer, I want a small corpus with page-level evidence labels so I can measure retrieval objectively.",
       do=["Pull an eval slice that ships gold evidence (DUDE or MP-DocVQA).",
           "Add one real manual (an FAA handbook, or a few iFixit guides) for the live ‘return the real figure’ demo.",
           "Cap the corpus to a few hundred pages so iteration stays fast."],
       acc=["Corpus loaded; every gold question names a doc + its evidence page(s)."]),
   ]),
 dict(id="E1", title="Parse &amp; route content types", stage="[1]",
   goal="Turn each PDF into routed text / figure / table regions with page numbers, and handle scanned pages safely.",
   stories=[
     dict(title="As an engineer, I want each content type routed correctly so figures and tables aren’t lost as flat text.",
       do=["Run a structural parser (Docling, or a PyMuPDF route) to get text blocks, figure regions and table regions.",
           "Attach a page number to every region; preserve reading order.",
           "Decide the first loader you’d reach for — and note exactly what it would drop (the diagram? the table structure?)."],
       acc=["Every page is classified; each figure/table region carries a page number."]),
     dict(title="As an engineer, I want scanned pages OCR’d behind a quality gate so garbled text never silently enters the index.",
       do=["Detect image-only pages (no text layer + a page-filling image).",
           "Render and OCR them (Tesseract or equiv).",
           "Score the output (mean confidence + garbled-char ratio); send failures to a review queue instead of the index."],
       acc=["Scanned pages are OCR’d or flagged; a review queue exists; sub-threshold pages are never indexed."]),
   ]),
 dict(id="E2", title="Extract figures &amp; tables with provenance", stage="[2]",
   goal="Make figures and tables first-class units, each able to name the exact page it came from.",
   stories=[
     dict(title="As an engineer, I want the real figure image exported so I can hand it back as the answer.",
       do=["For each figure region, export the cropped image — the embedded raster where possible, else render the bbox.",
           "Record doc→page→figure_id, the bbox, and any nearby caption text on the unit.",
           "Filter out rules/icons below a minimum size so they aren’t mistaken for figures."],
       acc=["Figure images are written to disk; each one resolves to its exact page."]),
     dict(title="As an engineer, I want tables kept as structured rows/cols so I never flatten them.",
       do=["Extract each table preserving rows/cols (Camelot / pdfplumber / parser tables).",
           "Store the structured form plus the source-page reference; keep the caption.",
           "Leave `search_text` empty here — enrichment fills it; the structure is the artefact you return."],
       acc=["Tables stored structured + page; no table is reduced to a flat string."]),
     dict(title="As an engineer, I want a provenance spot-check so I catch lost citations before building on them.",
       do=["Sample five units by hand and confirm each can name the exact page it came from.",
           "Fix provenance now if any can’t — everything downstream depends on it."],
       acc=["Spot-check passes: every sampled unit resolves to a page."]),
   ]),
 dict(id="E3", title="Enrich: caption &amp; linearise", stage="[3]",
   goal="Make figures and tables retrievable by giving them searchable text — without discarding the artefact.",
   stories=[
     dict(title="As an engineer, I want each figure described for search so an image can be found by a text query.",
       do=["Send each figure image to a free vision model with a search prompt (component/system, visible labels, part numbers).",
           "Store the caption as the figure’s `search_text`, linked to the original image + page.",
           "Cache captions on disk and caption selectively (figure/table pages only); keep a local model as fallback for rate limits or sensitive data."],
       acc=["Every figure unit has non-empty search_text; re-runs are served from cache; the image is untouched."]),
     dict(title="As an engineer, I want tables linearised to text while keeping the structured copy for the answer.",
       do=["Turn each table into searchable text (markdown or col=value rows); normalise the spacing/newline noise PDF extractors introduce.",
           "Include the table’s caption and nearby headings in the search text.",
           "Keep the structured cells as the artefact — linearisation is for search only."],
       acc=["Every table unit has search_text; the structured cells are unchanged."]),
   ]),
 dict(id="E4", title="Embed &amp; index", stage="[4]",
   goal="Build one index over text + figure-caption + table-text, with provenance in metadata.",
   stories=[
     dict(title="As an engineer, I want a single mixed index so one query can reach any content type.",
       do=["Embed `search_text` with a free local model (e.g. bge-small-en-v1.5).",
           "Chunk prose by structure/heading; keep a table or a figure-caption as ONE unit (don’t split).",
           "Index all unit types together (FAISS or equiv)."],
       acc=["Index persists; text, figure-caption and table-text units are all present and searchable."]),
     dict(title="As an engineer, I want provenance stored next to every vector so hits can be cited.",
       do=["Write each unit’s full provenance (doc→page→id, bbox, source path) into the index metadata.",
           "Persist units + vectors together so a reload reconstructs citations."],
       acc=["Each indexed row carries doc→page→id; reloading the index preserves citations."]),
   ]),
 dict(id="E5", title="Retrieve", stage="[5]",
   goal="Return the top-k units with their provenance; make exact identifiers findable.",
   stories=[
     dict(title="As an engineer, I want retrieval to return citations so every hit is traceable.",
       do=["Implement retrieve(query, k) returning the top-k units with their provenance and scores.",
           "Surface a human-readable citation (e.g. `doc p.212`) on every hit."],
       acc=["Retrieval returns units, each with a resolvable citation."]),
     dict(title="As an engineer, I want exact codes (part/fault numbers) to match so dense vectors don’t smear them.",
       do=["Add a lexical BM25 scorer over the same search texts.",
           "Fuse BM25 with the vector score (min-max normalise both; weight with an alpha you can tune).",
           "Test on a fault-code / part-number query and compare fused vs vector-only ranking."],
       acc=["An exact-identifier query surfaces the right unit at or near the top."]),
   ]),
 dict(id="E6", title="Answer with the artefact", stage="[6]",
   goal="Decide text / figure / table and return the REAL artefact + citation — never a paraphrase, never un-sourced.",
   stories=[
     dict(title="As a field engineer, I want the actual figure/table when that’s the answer, not a description of it.",
       do=["Decide the answer type from the top SOURCED hit.",
           "Figure → return the image path + page (optionally a one-line grounded caption). Table → return the exact rows + page. Text → the span + page.",
           "Keep the structured/real artefact in the response, not a paraphrase of it."],
       acc=["Figure and table answers return the real artefact plus its page citation."]),
     dict(title="As an engineer, I want the system to abstain when nothing has provenance so I never cite nothing.",
       do=["Filter out any retrieved unit whose provenance can’t name a page before choosing an answer.",
           "If no sourced unit remains, abstain and say why rather than presenting an un-sourced hit."],
       acc=["No-provenance hits are never presented as sourced; the system abstains cleanly when it must."]),
   ]),
 dict(id="E7", title="Evaluate &amp; engineer against failures", stage="[7]",
   goal="Measure retrieval BY TYPE, record a baseline, then fix measured failure modes.",
   stories=[
     dict(title="As an engineer, I want recall@k / MRR split by type so a good aggregate can’t hide that figures retrieve badly.",
       do=["Using the gold evidence pages, mark a hit relevant when its provenance matches the gold doc + page.",
           "Compute recall@k and MRR broken out by text / figure / table.",
           "Record the baseline numbers BEFORE any tuning."],
       acc=["Per-type metrics are reported and a baseline is recorded."]),
     dict(title="As an engineer, I want a faithfulness check so an answer that shows the WRONG figure is caught.",
       do=["Spot-check five answers: does each show/cite the exact source artefact on a gold evidence page?",
           "Flag the dangerous case — reads well but shows the wrong figure."],
       acc=["Five answers reviewed; any wrong-artefact answer is flagged."]),
     dict(title="As an engineer, I want to fix measured failure modes so the system improves with evidence.",
       do=["Pick two failure modes from the Appendix table.",
           "Reproduce each from its measured symptom, apply the fix, and re-measure.",
           "Show before/after numbers for each."],
       acc=["Two failure modes fixed, each with before/after metrics."]),
   ]),
]

def render_backlog() -> str:
    out = []
    for e in EPICS:
        stories_html = ""
        for i, s in enumerate(e["stories"], 1):
            do = "".join(f"<li>{t}</li>" for t in s["do"])
            acc = "".join(f"<li>{t}</li>" for t in s["acc"])
            stories_html += (
                f'<div class="story"><div class="story-title">'
                f'<span class="us">Story {e["id"]}.{i}</span> &mdash; {s["title"]}</div>'
                f'<div class="sub-lbl">What needs to be done</div><ul>{do}</ul>'
                f'<div class="acc"><div class="sub-lbl acc-lbl">Acceptance</div><ul>{acc}</ul></div>'
                f'</div>')
        out.append(
            f'<div class="epic"><div class="epic-head"><span class="epic-id">{e["id"]}</span>'
            f'<span class="epic-title">{e["title"]}</span><span class="epic-stage">{e["stage"]}</span></div>'
            f'<p class="epic-goal">{e["goal"]}</p>{stories_html}</div>')
    return "".join(out)
print("backlog epics:", len(EPICS), "stories:", sum(len(e["stories"]) for e in EPICS))

# --------------------------------------------------------------------------- #
# Assembly
# --------------------------------------------------------------------------- #
CSS = """
@page { size: Letter; margin: 20mm 18mm 18mm 18mm;
  @bottom-center { content: counter(page) " / " counter(pages); color:#8a93a3; font-size:9px; } }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { font-family: 'Inter','Helvetica Neue',Arial,sans-serif; color:#2b313c; font-size:11.3px; line-height:1.5; margin:0; }
h1,h2,h3 { color:#1d2330; font-weight:700; line-height:1.2; }
h2 { font-size:17px; margin:26px 0 8px; padding-bottom:5px; border-bottom:2px solid #4f46e5; }
h3 { font-size:13px; margin:16px 0 5px; }
p { margin:6px 0; }
ul { margin:5px 0 8px; padding-left:18px; } li { margin:3px 0; }
a { color:#4f46e5; text-decoration:none; }
.small { font-size:10px; color:#5b6472; }
.mute { color:#5b6472; }
svg { width:100%; height:auto; display:block; }
.kicker { color:#4f46e5; font-weight:700; letter-spacing:2px; font-size:11px; text-transform:uppercase; }
.rule { height:3px; background:#4f46e5; width:60px; margin:14px 0 18px; border-radius:2px; }
.cover { padding-top:60px; }
.cover h1 { font-size:34px; margin:6px 0 4px; letter-spacing:-0.5px; }
.cover .sub { font-size:16px; color:#2b313c; font-weight:600; margin:2px 0; }
.cover .meta { margin-top:26px; color:#5b6472; font-size:12px; }
.cover .tag { display:inline-block; background:#eef0fb; color:#4f46e5; border-radius:20px; padding:4px 12px; font-size:11px; font-weight:700; margin-top:18px; }
.callout { background:#f6f7f9; border-left:4px solid #0d9488; border-radius:8px; padding:12px 16px; margin:12px 0; }
.callout.indigo { border-left-color:#4f46e5; }
.callout.rose { border-left-color:#be123c; }
.nn { display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin:12px 0; }
.nn .card { background:#fff; border:1px solid #d7dbe3; border-radius:10px; padding:12px; }
.nn .n { color:#4f46e5; font-weight:700; font-size:12px; }
.nn h4 { margin:4px 0 4px; font-size:12.5px; color:#1d2330; }
.nn p { font-size:10.6px; color:#5b6472; margin:0; }
.figwrap { border:1px solid #e4e7ec; border-radius:12px; padding:14px 16px; margin:10px 0 6px; background:#fff; }
.figcap { font-size:10px; color:#5b6472; margin-top:6px; }
.epic { border:1px solid #d7dbe3; border-radius:12px; padding:14px 16px; margin:14px 0; background:#fff; }
.epic-head { display:flex; align-items:center; gap:10px; }
.story { border:1px solid #e8eaef; border-left:3px solid #4f46e5; border-radius:8px; padding:9px 12px 7px; margin:9px 0; background:#fbfbfd; break-inside:avoid; }
.story-title { font-weight:600; color:#1d2330; font-size:11.4px; margin-bottom:3px; line-height:1.4; }
.story-title .us { color:#4f46e5; font-weight:700; }
.sub-lbl { font-size:9px; font-weight:700; color:#4f46e5; text-transform:uppercase; letter-spacing:0.6px; margin:5px 0 1px; }
.story ul { margin:1px 0 3px; padding-left:16px; } .story li { font-size:10.3px; margin:2px 0; }
.acc { background:#f0faf7; border-radius:6px; padding:4px 10px 5px; margin-top:5px; }
.acc .acc-lbl { color:#0d9488; }
.epic-id { background:#4f46e5; color:#fff; font-weight:700; border-radius:7px; padding:2px 9px; font-size:12px; }
.epic-title { font-weight:700; color:#1d2330; font-size:14px; flex:1; }
.epic-stage { color:#0d9488; font-weight:700; font-size:11px; }
.epic-goal { color:#2b313c; margin:8px 0 10px; font-size:11px; }
.cols { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.lbl { font-size:10px; font-weight:700; color:#4f46e5; text-transform:uppercase; letter-spacing:0.6px; margin-bottom:2px; }
.cols ul { margin-top:2px; } .cols li { font-size:10.6px; }
.done { margin-top:10px; background:#f0faf7; border-radius:8px; padding:8px 12px; }
.done-lbl { font-size:10px; font-weight:700; color:#0d9488; text-transform:uppercase; letter-spacing:0.6px; }
.done ul { margin:3px 0 0; } .done li { font-size:10.4px; }
table { width:100%; border-collapse:collapse; margin:10px 0; font-size:10.4px; }
th { background:#1d2330; color:#fff; text-align:left; padding:7px 9px; font-weight:600; }
td { border-bottom:1px solid #e4e7ec; padding:6px 9px; vertical-align:top; }
tr:nth-child(even) td { background:#f6f7f9; }
.pill { display:inline-block; background:#eef0fb; color:#4f46e5; border-radius:5px; padding:1px 7px; font-size:9.5px; font-weight:600; }
.pagebreak { page-break-before:always; }
.chk li { list-style:none; margin-left:-14px; } .chk li::before { content:"\\2610  "; color:#0d9488; font-weight:700; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
"""

def main():
    html_doc = (
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>" + CSS + "</style></head><body>"
        # ---------- cover ----------
        "<section class='cover'>"
        "<div class='kicker'>AI Engineering Transformation Program · Curriculum v2.0</div>"
        "<div class='rule'></div>"
        "<div class='sub'>Course 3 — Agentic Systems and Retrieval · Day 2 · Lab A</div>"
        "<h1>Rich Answers, Not Just Text</h1>"
        "<div class='sub'>Multimodal Retrieval over Technical Manuals</div>"
        "<p class='mute' style='margin-top:14px;max-width:70%'>A build brief for engineers. You get the requirements, the reference "
        "diagrams, and a backlog of epics, user stories and tasks. You plan the system and implement it with your coding agent. "
        "The stack is free end to end.</p>"
        "<div class='tag'>Participant Brief &amp; Build Backlog</div>"
        "<div class='meta'>Companion to the facilitator playbook · Sub-Track 1A: <i>The Grounded Agent</i></div>"
        "</section>"

        # ---------- the brief ----------
        "<div class='pagebreak'></div>"
        "<h2>1 · The brief</h2>"
        "<p>Field engineers don't want a paragraph <i>about</i> a wiring diagram — they want the diagram, and the page it's on. "
        "Build a retrieval system over technical manuals (PDFs, including scans) that, <b>when a figure or table is the answer, returns "
        "the actual artefact with its page/source citation</b> — not a prose paraphrase.</p>"
        "<div class='callout indigo'><b>Guiding principle — retrieve-by-text, answer-with-artefact.</b> "
        "Index something searchable (a caption, a linearised table, OCR text), but hand back the original figure/table, linked by provenance.</div>"
        "<h3>The three non-negotiables</h3>"
        "<div class='nn'>"
        "<div class='card'><div class='n'>01</div><h4>Route content types</h4><p>Text, figures, tables and scanned pages each take a different path. Don't let a diagram collapse into flat text.</p></div>"
        "<div class='card'><div class='n'>02</div><h4>Make figures &amp; tables retrievable</h4><p>An image doesn't retrieve on its own. A description of it does — caption figures, linearise tables.</p></div>"
        "<div class='card'><div class='n'>03</div><h4>Carry provenance end-to-end</h4><p><span class='pill'>doc → page → id</span> on every unit, so an answer can show and cite the real thing.</p></div>"
        "</div>"
        "<div class='callout'><b>What success looks like.</b> Ask “show the relay control wiring” and get back the actual figure image "
        "with <i>amt_handbook p.212</i> — not a sentence describing it. Ask for a torque spec and get the exact table rows + page.</div>"

        # ---------- architecture ----------
        "<div class='pagebreak'></div>"
        "<h2>2 · Reference architecture</h2>"
        "<p>These are the diagrams to plan against. The pipeline is seven stages; provenance rides along the whole way.</p>"
        "<div class='figwrap'>" + diagram_pipeline() + "<div class='figcap'>Fig 1. The ingest → retrieve → answer → evaluate pipeline. Each stage is a natural unit of work (see the backlog).</div></div>"

        "<div class='figwrap'>" + diagram_unit() + "<div class='figcap'>Fig 2. The data backbone. Every stored thing is a Unit that separates what we <i>search</i> from what we <i>return</i>, tied together by provenance.</div></div>"

        "<div class='figwrap'>" + diagram_answer() + "<div class='figcap'>Fig 3. Answering. The top sourced hit decides the modality; a hit with no resolvable page is never presented as a sourced answer.</div></div>"

        # ---------- how you'll work ----------
        "<div class='pagebreak'></div>"
        "<h2>3 · How you'll work</h2>"
        "<p>This is an <b>agent-driven</b> build. You own the architecture and the decisions; your coding agent writes most of the code. "
        "There are no hard-and-fast rules on implementation — pick your libraries from the free menu in §6 and justify your choices. "
        "What we care about is the three non-negotiables and that you can <i>measure</i> what you built.</p>"
        "<div class='grid2'>"
        "<div><h3>Rhythm</h3><ul>"
        "<li>Work in thin vertical slices — one epic at a time, ingest→answer before polishing any stage.</li>"
        "<li>Use a feature branch per epic; keep commits small and reviewable.</li>"
        "<li>Write a test as you finish each stage; a synthetic 2-page PDF is enough to start.</li>"
        "<li>Record a baseline the moment retrieval works end-to-end, before any tuning.</li></ul></div>"
        "<div><h3>What to hand your agent</h3><ul>"
        "<li>This brief + the backlog below as the plan.</li>"
        "<li>The three non-negotiables as acceptance gates it must not skip.</li>"
        "<li>The failure-mode table (§Appendix) as its debugging checklist.</li>"
        "<li>Review its plan before it codes; make it show provenance and per-type eval.</li></ul></div>"
        "</div>"

        # ---------- backlog ----------
        "<div class='pagebreak'></div>"
        "<h2>4 · Build backlog</h2>"
        "<p class='small'>Epics map to the pipeline stages. Stories and tasks are a starting point, not a contract — reshape them. "
        "The <b>Done when</b> criteria are the part to respect: they encode the non-negotiables.</p>"
        + render_backlog() +

        # ---------- guidelines ----------
        "<div class='pagebreak'></div>"
        "<h2>5 · Guidelines</h2>"
        "<h3>Engineering</h3><ul>"
        "<li><b>Provenance is sacred.</b> If a unit can't name its page, it can't be a sourced answer. Carry doc→page→id from extraction to the final citation.</li>"
        "<li><b>Fail closed.</b> Prefer abstaining over citing nothing. A confident answer on the wrong figure is the most dangerous outcome — design so it can't happen silently.</li>"
        "<li><b>Keep structure.</b> Return structured table rows, not a flattened string. Keep the search copy (linearised) separate from the artefact.</li>"
        "<li><b>Measure by type.</b> A good aggregate recall can hide that figures retrieve terribly. Always break metrics out by text / figure / table.</li>"
        "<li><b>Cache the expensive calls.</b> Vision captioning is the one metered step — cache it, caption selectively, keep a local fallback.</li>"
        "<li><b>Record a baseline before tuning</b> so every change has a before/after.</li></ul>"
        "<h3>Working with your agent</h3><ul>"
        "<li>Give it the plan, then let it propose an approach; correct the plan, not every line.</li>"
        "<li>Make it write the provenance spot-check and the per-type eval — don't accept a stage without them.</li>"
        "<li>Have it keep the code modular (one package per stage) so you can swap a backend without a rewrite.</li>"
        "<li>When it gets stuck, point it at the failure-mode table rather than prescribing the fix.</li></ul>"
        "<div class='callout rose'><b>Cost &amp; privacy.</b> Use free endpoints with the <b>public</b> datasets only. Never send confidential "
        "manuals to a free endpoint — for real data, switch captioning and embeddings to <b>local</b> models so no bytes leave the machine. "
        "This is itself a production lesson (data residency / tenancy).</div>"

        # ---------- models ----------
        "<div class='pagebreak'></div>"
        "<h2>6 · Models &amp; tools (all free)</h2>"
        "<p>Pick one per row. Everything here is free to run locally or on a free tier — no paid API is required to complete the lab.</p>"
        "<table><tr><th>Layer</th><th>Recommended (free / open)</th><th>Alternatives</th></tr>"
        "<tr><td>PDF → structure</td><td><b>Docling</b> (IBM, MIT) — figures, tables, layout, reading order</td><td>Marker, Unstructured, PyMuPDF</td></tr>"
        "<tr><td>Figure extraction</td><td><b>PyMuPDF</b> (image xrefs / region render)</td><td>Docling figure export, pdfimages</td></tr>"
        "<tr><td>Table extraction</td><td><b>Camelot</b> / <b>pdfplumber</b></td><td>Docling tables, Tabula</td></tr>"
        "<tr><td>OCR (scans)</td><td><b>Tesseract</b> (pytesseract)</td><td>PaddleOCR, docTR, EasyOCR</td></tr>"
        "<tr><td>Figure captioning</td><td><b>Free OpenRouter vision model</b></td><td>Local BLIP-2 / Qwen2-VL / LLaVA</td></tr>"
        "<tr><td>Text embeddings</td><td><b>bge-small-en-v1.5</b> / all-MiniLM-L6-v2 (local)</td><td>e5-base-v2, nomic-embed-text</td></tr>"
        "<tr><td>Vector index</td><td><b>FAISS</b> (local)</td><td>Chroma, Qdrant, LanceDB, pgvector</td></tr>"
        "<tr><td>Grounded answer</td><td><b>Free OpenRouter vision model</b></td><td>local Qwen2-VL / Llama-3.2-Vision</td></tr>"
        "<tr><td>(Advanced) page-image retrieval</td><td><b>ColPali / ColQwen2</b> (open weights)</td><td>OpenCLIP, SigLIP, Nomic Embed Vision</td></tr>"
        "</table>"
        "<div class='grid2'>"
        "<div><h3>Free vision models (OpenRouter <span class='pill'>:free</span>)</h3><ul class='small'>"
        "<li><code>qwen/qwen2.5-vl-72b-instruct:free</code> — strong on charts/labels</li>"
        "<li><code>qwen/qwen2.5-vl-7b-instruct:free</code> — lighter, lower rate-limit pressure</li>"
        "<li><code>meta-llama/llama-3.2-11b-vision-instruct:free</code></li>"
        "<li><code>mistralai/mistral-small-3.1-24b-instruct:free</code></li>"
        "<li><code>openrouter/free</code> — auto-router, accepts images (safest default)</li></ul>"
        "<p class='small'>The free list rotates and is rate-limited — confirm live at <code>openrouter.ai/models?max_price=0</code>. Enforce :free-only in code.</p></div>"
        "<div><h3>Fully local (private — for sensitive data)</h3><ul class='small'>"
        "<li>Embeddings: <code>bge-small-en-v1.5</code>, <code>all-MiniLM-L6-v2</code>, <code>e5-base-v2</code></li>"
        "<li>Captioning / VQA: <code>Qwen2-VL-2B/7B</code>, <code>blip2-flan-t5-xl</code>, <code>llava-hf</code></li>"
        "<li>Page-image retrieval: <code>vidore/colpali</code>, <code>vidore/colqwen2</code>, OpenCLIP, SigLIP</li></ul>"
        "<p class='small'>Trial credits (optional, stronger models): Google AI Studio, Groq, Mistral La Plateforme, Cohere — keep the default path free/local.</p></div>"
        "</div>"

        # ---------- datasets ----------
        "<h2>7 · Datasets (all free)</h2>"
        "<p>Pick <b>one eval set with evidence labels</b> (DUDE or MP-DocVQA) <b>plus one real manual</b> (an FAA handbook or a few iFixit guides) for the live “return the real figure” demo.</p>"
        "<table><tr><th>Source</th><th>What it gives you</th><th>Licence (verify)</th></tr>"
        "<tr><td><b>DUDE</b></td><td>Multi-page docs incl. technical manuals; questions with <b>page-level evidence</b></td><td>Research / CC BY</td></tr>"
        "<tr><td><b>MP-DocVQA</b></td><td>Multi-page scanned docs; answers + <b>evidence page</b> labels</td><td>MIT (HF card)</td></tr>"
        "<tr><td>DocVQA / InfographicVQA</td><td>Single-page images rich in figures, tables, infographics</td><td>Research</td></tr>"
        "<tr><td>TAT-DQA</td><td>Table + text document QA (stresses the table path)</td><td>Research</td></tr>"
        "<tr><td>DocLayNet / PubLayNet</td><td>Layout (figure/table regions) to validate extraction</td><td>CDLA-Permissive</td></tr>"
        "<tr><td><b>FAA handbooks</b></td><td>Real manual: wiring diagrams, exploded views, spec tables</td><td>US-gov <b>public domain</b></td></tr>"
        "<tr><td><b>iFixit guides</b></td><td>Repair procedures with step photos; free API</td><td>CC BY-NC-SA</td></tr>"
        "<tr><td>NASA NTRS / US Army TMs</td><td>Engineering reports/manuals with diagrams &amp; tables</td><td>Public domain</td></tr>"
        "</table>"
        "<p class='small'>Evidence labels are the gift — DUDE/MP-DocVQA give page-level gold for free; don't rebuild a question set by hand.</p>"

        # ---------- DoD ----------
        "<div class='pagebreak'></div>"
        "<h2>8 · Definition of Done</h2>"
        "<p>You're done when every box is ticked — these are the milestone gates, not the implementation.</p>"
        "<ul class='chk'>"
        "<li>Corpus loaded (eval set with evidence labels + one real manual).</li>"
        "<li>Content routed; scanned pages OCR'd behind a quality gate.</li>"
        "<li>Figures &amp; tables extracted with <span class='pill'>doc→page→id</span> provenance.</li>"
        "<li>Figures captioned / tables linearised (free vision model, cached).</li>"
        "<li>Mixed index built with provenance in metadata (local embeddings + FAISS).</li>"
        "<li>Retrieval returns units with citations.</li>"
        "<li>Answer step returns the real figure/table + page, not a paraphrase.</li>"
        "<li>Retrieval measured by type; baseline recorded; 2 failure modes fixed with before/after.</li>"
        "</ul>"
        "<h3>Stretch goals</h3><ul>"
        "<li>BM25 + vector fusion for exact identifiers (sets up Lab B).</li>"
        "<li>ColPali / ColQwen2 page-image retrieval as a second index.</li>"
        "<li>Local vision fallback when the free tier rate-limits you.</li>"
        "<li>Multi-hop retrieval (Lab B) and trust/abstention (Lab C) on top of this corpus.</li></ul>"

        # ---------- appendix ----------
        "<h2>Appendix · Failure modes</h2>"
        "<p>Reproduce from the measured symptom, then fix. Pick at least two for E7.</p>"
        "<table><tr><th>Symptom</th><th>Likely cause</th><th>Fix</th></tr>"
        "<tr><td>Scanned-text noise in results</td><td>garbled OCR indexed silently</td><td>OCR confidence + garbled-ratio gate; flag for review</td></tr>"
        "<tr><td>Figures never retrieved</td><td>images have no searchable text</td><td>caption figures for search</td></tr>"
        "<tr><td>Table answers are mush</td><td>table flattened to a string</td><td>keep structure; linearise only for search</td></tr>"
        "<tr><td>Can't cite the source</td><td>provenance lost in extraction</td><td>carry doc→page→id on every unit; fail closed</td></tr>"
        "<tr><td>Right text, wrong figure</td><td>caption–image drift</td><td>add model/variant terms; re-caption from the real image</td></tr>"
        "<tr><td>Vision cost blowout</td><td>captioning every page</td><td>caption selectively + cache</td></tr>"
        "</table>"
        "<p class='small' style='margin-top:18px'>This brief implements Sub-Track 1A. Its enriched, provenance-carrying corpus is the input to Sub-Track 1B "
        "(multi-hop retrieval) and, with 1C (trust / abstention), forms the retrieval layer of the Course 3 mini-project, <i>The Grounded Agent</i>.</p>"

        "</body></html>"
    )
    path = OUT / "brief.html"
    path.write_text(html_doc, encoding="utf-8")
    print("wrote", path, len(html_doc), "bytes")

if __name__ == "__main__":
    main()
