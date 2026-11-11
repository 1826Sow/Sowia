"""FINAL TEC investor dashboard prototype.

The current view is intentionally synthetic. It must not be used as evidence
of real product performance, revenue, partnerships, or investor commitments.
"""
from __future__ import annotations

from typing import Any


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


def render_dashboard(st: Any) -> None:
    """Render the read-only investor dashboard prototype using Streamlit."""
    snapshot = build_demo_snapshot()

    st.subheader("FINAL TEC LIVE — Investor Dashboard")
    st.caption(
        "Espace de présentation en lecture seule · prototype graphique "
        "préparatoire à l'ouverture d'un accès investisseur contrôlé"
    )
    st.warning(snapshot["notice"])

    meta_cols = st.columns(2)
    meta_cols[0].caption("Source : " + snapshot["source"])
    meta_cols[1].caption("Actualisation : " + snapshot["updated_at"])

    st.markdown("### Indicateurs clés")
    kpis = snapshot["kpis"]
    columns = st.columns(4)
    columns[0].metric("Jalons techniques", kpis["technical_milestones"]["value"])
    columns[1].metric("Tests", kpis["validated_tests"]["value"])
    columns[2].metric("Partenariats confirmés", kpis["confirmed_partners"]["value"])
    columns[3].metric("Pilotes commerciaux", kpis["commercial_pilots"]["value"])

    st.markdown("### Performance technique — série fictive")
    performance = snapshot["performance"]
    left, right = st.columns(2)
    with left:
        st.caption("Latence simulée (ms) — plus bas est préférable")
        st.line_chart(
            [{"Période": row["period"], "Latence (ms)": row["latency_ms"]} for row in performance],
            x="Période",
            y="Latence (ms)",
        )
    with right:
        st.caption("Disponibilité simulée (%) — série fictive")
        st.line_chart(
            [{"Période": row["period"], "Disponibilité (%)": row["availability_pct"]} for row in performance],
            x="Période",
            y="Disponibilité (%)",
        )

    st.markdown("### Feuille de route — progression illustrative")
    st.bar_chart(
        [
            {"Jalon": row["milestone"], "Progression (%)": row["progress_pct"]}
            for row in snapshot["roadmap"]
        ],
        x="Jalon",
        y="Progression (%)",
    )

    st.markdown("### Provenance et règles de publication")
    st.dataframe(
        [
            {"Indicateur": "Avancement technique", "Source attendue": "Jalons GitHub validés", "État": "Non connecté"},
            {"Indicateur": "Tests IA / Edge", "Source attendue": "Rapports de benchmark reproductibles", "État": "Non connecté"},
            {"Indicateur": "Coûts et budget", "Source attendue": "Registre financier FINAL TEC", "État": "Non connecté"},
            {"Indicateur": "Partenariats et pilotes", "Source attendue": "Contrats ou validations autorisées", "État": "Non connecté"},
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.info(
        "Aucun accès externe investisseur n'est activé par cette maquette. "
        "Avant toute ouverture, il faudra créer une liste d'investisseurs autorisés, "
        "des droits de lecture limités, un journal d'accès et des sources de données "
        "validées. Les projections devront rester séparées des résultats réalisés."
    )
