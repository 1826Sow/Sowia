"""FINAL TEC investor dashboard prototype.

The current view is intentionally synthetic. It must not be used as evidence
of real product performance, revenue, partnerships, or investor commitments.
"""
from __future__ import annotations

from typing import Any

from final_tec_evidence import build_pending_register


DEMO_NOTICE = (
    "MAQUETTE DE DÉMONSTRATION — toutes les valeurs et séries affichées sont "
    "fictives. Aucune donnée réelle de FINAL TEC n'est connectée."
)


def build_demo_snapshot() -> dict[str, Any]:
    """Return deterministic, explicitly synthetic data for the first UI prototype."""
    return {
        "mode": "demo",
        "notice": DEMO_NOTICE,
        "source": "Jeu de données synthétique local",
        "updated_at": "Non applicable — démonstration statique",
        "kpis": {
            "technical_milestones": {"value": 3, "unit": "jalons fictifs"},
            "validated_tests": {"value": 12, "unit": "tests fictifs"},
            "confirmed_partners": {"value": 0, "unit": "partenariat confirmé"},
            "commercial_pilots": {"value": 0, "unit": "pilote confirmé"},
        },
        "performance": [
            {"period": "M1", "latency_ms": 180, "availability_pct": 96.0},
            {"period": "M2", "latency_ms": 165, "availability_pct": 96.8},
            {"period": "M3", "latency_ms": 152, "availability_pct": 97.2},
            {"period": "M4", "latency_ms": 145, "availability_pct": 97.8},
            {"period": "M5", "latency_ms": 138, "availability_pct": 98.1},
        ],
        "roadmap": [
            {"milestone": "Cadrage", "progress_pct": 100},
            {"milestone": "Prototype simulé", "progress_pct": 60},
            {"milestone": "Tests sur ressources autorisées", "progress_pct": 0},
            {"milestone": "Pilote client", "progress_pct": 0},
        ],
    }


def render_dashboard(st: Any, metrics: list[dict[str, Any]] | None) -> None:
    """Render only Supabase-published FINAL TEC metrics; never show demo values as live."""
    st.subheader("FINAL TEC LIVE — Investor Dashboard")
    st.caption(
        "Espace en lecture seule · indicateurs issus du registre de publication FINAL TEC "
        "et filtrés par les règles RLS Supabase"
    )

    if metrics is None:
        st.error(
            "La source des indicateurs FINAL TEC est indisponible. "
            "Aucune donnée locale ou fictive n'est substituée."
        )
        st.info("Réessayez ultérieurement ou faites vérifier la connexion Supabase.")
        return

    if not metrics:
        st.info(
            "Aucun indicateur n'a encore été publié pour FINAL TEC. "
            "Le tableau reste vide jusqu'à validation et publication de données sourcées."
        )
        st.caption(
            "Les données de démonstration ne sont pas affichées dans cet espace investisseur."
        )
        return

    st.success(f"{len(metrics)} indicateur(s) publié(s) et autorisé(s).")
    display_rows = []
    for row in metrics:
        value = row.get("metric_value")
        if isinstance(value, (dict, list)):
            import json
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        display_rows.append(
            {
                "Indicateur": row.get("title") or row.get("metric_key") or "Sans titre",
                "Catégorie": row.get("category") or "Non classée",
                "Valeur publiée": value if value is not None else "Non renseignée",
                "Unité": row.get("unit") or "",
                "Nature de la donnée": row.get("display_status", "Statut non disponible"),
                "Date de mesure": row.get("observed_at") or "Non applicable",
                "Date de publication": row.get("published_at") or "Non renseignée",
                "Référence de preuve": row.get("evidence_ref") or "—",
                "Responsable": row.get("evidence_owner") or "—",
                "Source": row.get("source_url") or "—",
                "Hypothèses": row.get("assumptions") or "—",
                "Horizon": row.get("horizon") or "—",
                "Étiquette synthétique": row.get("synthetic_label") or "—",
            }
        )

    st.markdown("### Indicateurs publiés")
    st.dataframe(display_rows, use_container_width=True, hide_index=True)
    st.caption(
        "Les résultats vérifiés, projections et démonstrations synthétiques sont "
        "explicitement distingués. Une projection n'est pas un résultat réalisé."
    )
    st.info(
        "Affichage en lecture seule. La visibilité des lignes dépend de l'autorisation "
        "FINAL TEC et des politiques RLS Supabase. Aucun chiffre n'est calculé ou "
        "complété localement pour combler une donnée manquante."
    )
