"""Descriptive statistics for completed human-vs-SOW IA decision trials."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping


def summarize_decisions(records: Iterable[Mapping]) -> dict:
    """Summarize only completed trials with both human and AI outcomes.

    Unresolved, unverified, or incomplete records are excluded and counted separately.
    This is descriptive benchmarking, not proof of causality or future performance.
    """
    totals = {"human": 0, "ai": 0, "tie": 0}
    differences = []
    completed = 0
    excluded = 0
    by_category = defaultdict(lambda: {"human": 0, "ai": 0, "tie": 0, "n": 0, "differences": []})

    for record in records:
        outcomes = record.get("outcomes")
        ai_choice = record.get("ai_choice")
        human_choice = record.get("human_choice")
        if not outcomes or not ai_choice or ai_choice not in outcomes or human_choice not in outcomes:
            excluded += 1
            continue
        try:
            human_score = float(outcomes[human_choice])
            ai_score = float(outcomes[ai_choice])
        except (TypeError, ValueError):
            excluded += 1
            continue
        if not (0 <= human_score <= 100 and 0 <= ai_score <= 100):
            excluded += 1
            continue

        completed += 1
        delta = ai_score - human_score
        differences.append(delta)
        winner = "tie" if delta == 0 else ("ai" if delta > 0 else "human")
        totals[winner] += 1

        category = str(record.get("category") or "Non classé").strip() or "Non classé"
        by_category[category][winner] += 1
        by_category[category]["n"] += 1
        by_category[category]["differences"].append(delta)

    def stats(n, human, ai, tie, deltas):
        return {
            "sample_size": n,
            "human_wins": human,
            "ai_wins": ai,
            "ties": tie,
            "human_win_rate_pct": round(human / n * 100, 1) if n else None,
            "ai_win_rate_pct": round(ai / n * 100, 1) if n else None,
            "tie_rate_pct": round(tie / n * 100, 1) if n else None,
            "mean_ai_minus_human": round(sum(deltas) / len(deltas), 2) if deltas else None,
        }

    categories = {}
    for name, values in sorted(by_category.items()):
        categories[name] = stats(
            values["n"], values["human"], values["ai"], values["tie"],
            values["differences"],
        )

    return {
        "overall": stats(completed, totals["human"], totals["ai"], totals["tie"], differences),
        "by_category": categories,
        "excluded_incomplete": excluded,
        "interpretation": (
            "Statistiques descriptives sur les seuls cas évalués. "
            "Un échantillon plus large et comparable est nécessaire avant toute conclusion."
        ),
    }
