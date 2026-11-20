"""Evaluate retrieval BY TYPE + faithfulness (stage [7]).

"This is what makes it engineering." A good aggregate can hide that figures retrieve
terribly, so recall@k and MRR are **broken out by question type** (text / figure / table).
Relevance uses the gold page-level evidence: a hit is relevant iff its provenance names
the gold document and one of the gold evidence pages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..answering.answerer import Answerer
from ..logging_utils import get_logger
from ..retrieval.retriever import Retriever
from .dataset import GoldQuestion

log = get_logger("grounded_retrieval.evaluation.metrics")


def _is_relevant(unit, gold: GoldQuestion) -> bool:
    p = unit.provenance
    return p.is_resolvable() and p.doc_id == gold.doc_id and p.page in set(gold.evidence_pages)


def _first_relevant_rank(hits, gold: GoldQuestion) -> int | None:
    for i, h in enumerate(hits):
        if _is_relevant(h.unit, gold):
            return i + 1  # 1-indexed
    return None


@dataclass
class TypeReport:
    n: int = 0
    recall_at: dict[int, float] = field(default_factory=dict)
    mrr: float = 0.0


def _aggregate(per_q: list[dict], k_values: list[int]) -> TypeReport:
    n = len(per_q)
    rep = TypeReport(n=n)
    if n == 0:
        rep.recall_at = {k: 0.0 for k in k_values}
        return rep
    for k in k_values:
        rep.recall_at[k] = sum(q["recall_at"][k] for q in per_q) / n
    rep.mrr = sum(q["rr"] for q in per_q) / n
    return rep


def evaluate(retriever: Retriever, gold: list[GoldQuestion],
             k_values: list[int] | None = None, by_type: bool = True) -> dict[str, Any]:
    k_values = sorted(k_values or [1, 3, 5, 10])
    max_k = max(k_values)
    per_q: list[dict] = []

    for g in gold:
        hits = retriever.retrieve(g.question, k=max_k)
        rank = _first_relevant_rank(hits, g)
        recall_at = {k: 1.0 if (rank is not None and rank <= k) else 0.0 for k in k_values}
        rr = (1.0 / rank) if rank else 0.0
        per_q.append({"qid": g.qid, "type": g.answer_type,
                      "recall_at": recall_at, "rr": rr, "rank": rank})

    report: dict[str, Any] = {
        "n": len(gold),
        "k_values": k_values,
        "overall": _aggregate(per_q, k_values).__dict__,
    }
    if by_type:
        types = sorted({q["type"] for q in per_q})
        report["by_type"] = {
            t: _aggregate([q for q in per_q if q["type"] == t], k_values).__dict__
            for t in types
        }
    report["per_question"] = per_q
    return report


@dataclass
class FaithfulnessCase:
    qid: str
    question: str
    answered_type: str
    citation: str | None
    page_in_evidence: bool
    note: str = ""


def faithfulness_spotcheck(answerer: Answerer, gold: list[GoldQuestion],
                           n: int = 5) -> list[FaithfulnessCase]:
    """For n answers: does the cited artefact actually sit on a gold evidence page?
    Flags the dangerous case — an answer that reads well but shows the WRONG artefact."""
    cases: list[FaithfulnessCase] = []
    for g in gold[:n]:
        ans = answerer.answer(g.question)
        page = ans.artefact.get("page")
        doc_ok = ans.artefact.get("doc_id") == g.doc_id
        in_ev = bool(doc_ok and page in set(g.evidence_pages))
        note = ""
        if ans.answer_type == "none":
            note = "abstained (fail-closed): no sourced unit"
        elif not in_ev:
            note = "answer cites a page outside the gold evidence — inspect"
        cases.append(FaithfulnessCase(
            qid=g.qid, question=g.question, answered_type=ans.answer_type,
            citation=ans.citation, page_in_evidence=in_ev, note=note))
    return cases


def format_report(report: dict[str, Any]) -> str:
    """Compact human-readable summary for the CLI."""
    lines = [f"Retrieval eval over {report['n']} questions  (k={report['k_values']})", ""]

    def row(label: str, r: dict) -> str:
        rec = "  ".join(f"R@{k}={r['recall_at'][k]:.2f}" for k in report["k_values"])
        return f"  {label:<8} n={r['n']:<3} {rec}  MRR={r['mrr']:.3f}"

    lines.append("OVERALL")
    lines.append(row("all", report["overall"]))
    if "by_type" in report:
        lines.append("")
        lines.append("BY TYPE  (a good aggregate can hide that figures retrieve badly)")
        for t, r in report["by_type"].items():
            lines.append(row(t, r))
    return "\n".join(lines)
