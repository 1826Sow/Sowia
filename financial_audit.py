"""Read-only access to the authenticated user's financial audit events."""

from __future__ import annotations


def load_user_financial_audit_events(admin_client, user_id: str, *, limit: int = 200):
    """Load only the requested user's audit rows through the trusted server client."""
    normalized_user_id = str(user_id or "").strip()
    if admin_client is None:
        raise RuntimeError("Client administratif Supabase indisponible.")
    if not normalized_user_id:
        raise PermissionError("Connexion requise.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise ValueError("Limite de lecture d'audit invalide.")

    response = (
        admin_client.table("sowia_financial_audit_log")
        .select(
            "event_id, ledger_row_id, user_id, actor_id, actor_role, operation, "
            "transaction_id, changed_at, before_data, after_data"
        )
        .eq("user_id", normalized_user_id)
        .order("changed_at", desc=True)
        .limit(limit)
        .execute()
    )
    rows = getattr(response, "data", None) or []
    if not isinstance(rows, list):
        raise RuntimeError("Réponse du journal d'audit invalide.")
    return rows


def present_audit_events(rows):
    """Return a minimal display-safe view; omit full JSON snapshots and user IDs."""
    if not isinstance(rows, (list, tuple)):
        raise ValueError("Les événements d'audit doivent être une liste.")

    def snapshot_value(snapshot, key):
        if not isinstance(snapshot, dict):
            return "—"
        value = snapshot.get(key)
        return "—" if value is None else str(value)

    presented = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        before = row.get("before_data")
        after = row.get("after_data")
        presented.append({
            "Date UTC": row.get("changed_at") or "—",
            "Opération": row.get("operation") or "—",
            "Écriture": row.get("ledger_row_id") or "—",
            "Acteur": row.get("actor_role") or ("Utilisateur connecté" if row.get("actor_id") else "Serveur / système"),
            "Statut avant": snapshot_value(before, "status"),
            "Statut après": snapshot_value(after, "status"),
            "Référence EUR avant": snapshot_value(before, "reference_amount_eur"),
            "Référence EUR après": snapshot_value(after, "reference_amount_eur"),
            "Taxe EUR avant": snapshot_value(before, "tax_amount_eur"),
            "Taxe EUR après": snapshot_value(after, "tax_amount_eur"),
            "Montant avant": (
                snapshot_value(before, "gross_amount") + " " + snapshot_value(before, "gross_currency")
                if isinstance(before, dict) else "—"
            ),
            "Montant après": (
                snapshot_value(after, "gross_amount") + " " + snapshot_value(after, "gross_currency")
                if isinstance(after, dict) else "—"
            ),
        })
    return presented
