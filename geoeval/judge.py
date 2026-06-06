"""Optional LLM-as-judge with *measured* human agreement.

Some geospatial answers (e.g. natural-language explanations, or whether two
phrasings of a refusal are equivalent) can't be graded by a deterministic
verifier. For those, an LLM-as-judge decides equivalence — but a judge is only
trustworthy if we report how often it agrees with humans. This module runs the
judge over a small hand-annotated calibration set (``judge/human_labels.jsonl``)
and reports the agreement rate rather than assuming it (cf. GeoBenchX, which
reports 88–96% panel-vs-human agreement).

Offline, the ``replay`` adapter serves recorded judge decisions so the agreement
number is reproducible with no API key.
"""
from __future__ import annotations

import json
from pathlib import Path

from .adapters import get_adapter
from .adapters.base import LLMClient

ROOT = Path(__file__).resolve().parent.parent
HUMAN_LABELS = ROOT / "judge" / "human_labels.jsonl"

JUDGE_SYSTEM = (
    "You are a strict GIS answer judge. Decide whether the CANDIDATE answer is "
    "geospatially equivalent to the REFERENCE answer. Reply with a single word: "
    "EQUIVALENT or DIFFERENT."
)


def _decision(text: str) -> bool:
    t = text.strip().lower()
    if "equivalent" in t and "not equivalent" not in t and "in-equivalent" not in t:
        return True
    if t.startswith(("yes", "true", "match", "same")):
        return True
    return False


def load_labels() -> list[dict]:
    if not HUMAN_LABELS.exists():
        return []
    return [json.loads(l) for l in HUMAN_LABELS.read_text().splitlines() if l.strip()]


def run_judge(client: LLMClient | None = None) -> dict:
    """Run the judge over the calibration set and report agreement.

    Defaults to the offline replay adapter reading recorded decisions from the
    same labels file (field ``replay_response``).
    """
    if client is None:
        client = get_adapter("replay", path=str(HUMAN_LABELS))

    items = load_labels()
    by_item, agree = [], 0
    for it in items:
        out = client.complete(it["judge_prompt"], system=JUDGE_SYSTEM, key=str(it["id"]))
        judged = _decision(out)
        human = bool(it["human"])
        ok = judged == human
        agree += ok
        by_item.append({"id": it["id"], "judge": judged, "human": human, "agree": ok})

    n = len(items)
    return {
        "calibrated": n > 0,
        "n_labels": n,
        "human_agreement": round(agree / n, 4) if n else None,
        "by_item": by_item,
    }
