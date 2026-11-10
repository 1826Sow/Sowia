"""Persistance Supabase des évaluations de technologies, isolée par utilisateur et espace."""
from datetime import datetime, timezone

WORKSPACES = {"personal", "professional"}


def _owner(user):
    value = getattr(user, "id", None)
    if not value:
        raise PermissionError("Connexion requise.")
    return str(value)


def _workspace(value):
    workspace = str(value or "personal")
    if workspace not in WORKSPACES:
        raise ValueError("Espace de travail invalide.")
    return workspace


def list_technology_candidates(client, user, workspace_id="personal", limit=100):
    return (
        client.table("sowia_technology_candidates")
        .select("id, name, scores, score, decision, reasons, evidence, compliant, compliance_verified, critical_incident, created_at, updated_at")
        .eq("user_id", _owner(user))
        .eq("workspace_id", _workspace(workspace_id))
        .order("updated_at", desc=True)
        .limit(min(max(int(limit), 1), 200))
        .execute().data
    )


def upsert_technology_candidate(client, user, workspace_id="personal", **values):
    name = str(values.get("name") or "").strip()
    if not name or len(name) > 120:
        raise ValueError("Le nom de la solution doit contenir entre 1 et 120 caractères.")
    scores = values.get("scores")
    if not isinstance(scores, dict) or len(scores) != 8:
        raise ValueError("Les huit notes du comparatif sont obligatoires.")
    evidence = values.get("evidence") or []
    if not isinstance(evidence, list) or len(evidence) > 30:
        raise ValueError("La liste des références est invalide.")
    cleaned_evidence = [str(item).strip()[:500] for item in evidence if str(item).strip()]
    row = {
        "user_id": _owner(user),
        "workspace_id": _workspace(workspace_id),
        "name": name,
        "scores": scores,
        "score": float(values.get("score")),
        "decision": str(values.get("decision") or "")[:40],
        "reasons": [str(item)[:500] for item in (values.get("reasons") or [])][:20],
        "evidence": cleaned_evidence,
        "compliant": bool(values.get("compliant", True)),
        "compliance_verified": bool(values.get("compliance_verified", False)),
        "critical_incident": bool(values.get("critical_incident", False)),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if row["decision"] not in {"Prioritaire", "À tester", "À documenter", "Non prioritaire", "Écarter"}:
        raise ValueError("Décision de comparaison invalide.")
    return (
        client.table("sowia_technology_candidates")
        .upsert(row, on_conflict="user_id,workspace_id,name")
        .execute().data
    )


def delete_all_technology_candidates(client, user, workspace_id="personal"):
    return (
        client.table("sowia_technology_candidates")
        .delete()
        .eq("user_id", _owner(user))
        .eq("workspace_id", _workspace(workspace_id))
        .execute()
    )
