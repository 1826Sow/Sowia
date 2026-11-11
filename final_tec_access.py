"""Fail-closed authorization and read-only metric retrieval for FINAL TEC."""
from __future__ import annotations

from typing import Any

from final_tec_evidence import EvidenceValidationError, validate_indicator


def authorize_final_tec_investor_viewer(
    supabase_client: Any,
    authenticated_user: Any,
) -> bool:
    """Return True only when Supabase confirms an active FINAL TEC viewer grant."""
    user_id = getattr(authenticated_user, "id", None)
    if not user_id or supabase_client is None:
        return False

    try:
        rpc = getattr(supabase_client, "rpc", None)
        if not callable(rpc):
            return False
        response = rpc("final_tec_can_view_published_metrics").execute()
        return getattr(response, "data", None) is True
    except Exception:
        return False


def fetch_published_final_tec_metrics(supabase_client: Any) -> list[dict[str, Any]] | None:
    """Fetch only RLS-authorized published metrics; None means source unavailable.

    RLS remains the security boundary. The query filters again for clarity, and
    every returned row is checked for evidence provenance before display.
    """
    if supabase_client is None:
        return None
    try:
        response = (
            supabase_client.table("final_tec_published_metrics")
            .select(
                "id,metric_key,title,category,metric_value,unit,evidence_status,"
                "source_url,observed_at,evidence_ref,evidence_owner,assumptions,"
                "horizon,synthetic_label,publication_state,published_at"
            )
            .eq("project_key", "final-tec")
            .eq("publication_state", "published")
            .order("published_at", desc=True)
            .limit(500)
            .execute()
        )
        rows = getattr(response, "data", None)
        if not isinstance(rows, list):
            return None

        accepted: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if row.get("publication_state") != "published":
                continue
            if row.get("evidence_status") not in {"verified", "projected", "synthetic"}:
                continue
            evidence_record = {
                "status": row.get("evidence_status"),
                "source_url": row.get("source_url"),
                "observed_at": row.get("observed_at"),
                "evidence_ref": row.get("evidence_ref"),
                "owner": row.get("evidence_owner"),
                "assumptions": row.get("assumptions"),
                "horizon": row.get("horizon"),
                "label": row.get("synthetic_label"),
            }
            try:
                evidence = validate_indicator(evidence_record)
            except EvidenceValidationError:
                continue
            accepted.append({**row, "display_status": evidence["display_status"]})
        return accepted
    except Exception:
        # Do not substitute local demo values when the live source is unavailable.
        return None
