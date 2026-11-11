"""Session-only FINAL TEC evidence register and monitoring summaries.

Submissions remain pending/draft. This module does not verify, approve, publish,
persist, or fetch evidence from external systems.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from final_tec_evidence_intake import EvidenceIntakeError, prepare_evidence_submission


def prepare_evidence_batch(payload: Any) -> list[dict[str, Any]]:
    """Validate a list of submissions; force all entries to pending/draft."""
    if not isinstance(payload, list):
        raise EvidenceIntakeError("Le registre doit être une liste JSON.")
    if len(payload) > 500:
        raise EvidenceIntakeError("Maximum 500 éléments par lot.")
    prepared = []
    seen = set()
    for index, item in enumerate(payload):
        try:
            row = prepare_evidence_submission(item)
        except EvidenceIntakeError as exc:
            raise EvidenceIntakeError(f"Élément {index + 1} : {exc}") from exc
        key = row["metric_key"]
        if key in seen:
            raise EvidenceIntakeError(f"Identifiant répété dans le lot : {key}.")
        seen.add(key)
        # Client intake is never allowed to self-approve or publish.
        row["evidence_status"] = "pending"
        row["publication_state"] = "draft"
        row["approved_by"] = None
        row["published_at"] = None
        prepared.append(row)
    return prepared


def build_evidence_monitor_snapshot(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build truthful session monitoring counts; no performance claims."""
    if not isinstance(records, list):
        raise EvidenceIntakeError("Les enregistrements doivent être une liste.")
    category_counts = Counter()
    status_counts = Counter()
    timeline = []
    for row in records:
        if not isinstance(row, dict):
            continue
        category = row.get("category") or "uncategorized"
        status = row.get("evidence_status") or "pending"
        category_counts[category] += 1
        status_counts[status] += 1
        observed = row.get("observed_at")
        try:
            sort_time = datetime.fromisoformat(str(observed).replace("Z", "+00:00")) if observed else None
        except ValueError:
            sort_time = None
        timeline.append({
            "metric_key": row.get("metric_key", "unknown"),
            "title": row.get("title", "Sans titre"),
            "category": category,
            "evidence_status": status,
            "publication_state": row.get("publication_state", "draft"),
            "observed_at": observed or "Non renseignée",
            "source_url": row.get("source_url") or "Non renseignée",
            "evidence_ref": row.get("evidence_ref") or "Non renseignée",
            "_sort_time": sort_time,
        })
    timeline.sort(key=lambda item: (
        item["_sort_time"] is None,
        item["_sort_time"] or datetime.min.replace(tzinfo=None),
        item["metric_key"],
    ))
    for item in timeline:
        item.pop("_sort_time", None)
    return {
        "total_submissions": len(records),
        "pending": status_counts.get("pending", 0),
        "verified": status_counts.get("verified", 0),
        "projected": status_counts.get("projected", 0),
        "synthetic": status_counts.get("synthetic", 0),
        "by_category": dict(sorted(category_counts.items())),
        "timeline": timeline,
        "mode": "session_only",
        "notice": "Suivi des soumissions de preuves en session ; ce n'est pas une télémétrie temps réel.",
    }
