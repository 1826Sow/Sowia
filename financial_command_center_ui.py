"""SOWIA Financial Command Center — prototype synthétique en lecture seule.

Aucune connexion bancaire, aucun accès Supabase et aucune écriture financière.
Les chiffres ci-dessous sont des exemples fictifs destinés à valider l'ergonomie.
"""
from __future__ import annotations

import streamlit as st


ENTITIES = {
    "SOWIA": {
        "description": "Plateforme centrale et services numériques",
        "currency": "EUR",
        "scenario": {"inflow": 12450.00, "fees": 312.50, "refunds": 180.00, "pending": 640.00, "anomalies": 2},
    },
    "FINAL TEC PLATFORM": {
        "description": "Projet de plateforme technologique indépendante",
        "currency": "USD",
        "scenario": {"inflow": 8200.00, "fees": 205.00, "refunds": 0.00, "pending": 1250.00, "anomalies": 1},
    },
    "EDGE FINDS": {
        "description": "Périmètre exploratoire Edge Finds",
        "currency": "EUR",
        "scenario": {"inflow": 3150.00, "fees": 78.75, "refunds": 45.00, "pending": 0.00, "anomalies": 0},
    },
}

SAMPLE_EVENTS = [
    {"Date (exemple)": "2026-11-10", "Entité": "SOWIA", "Source": "PayPal Sandbox", "Référence": "DEMO-SW-001", "Devise": "EUR", "Montant": 125.00, "Statut": "À rapprocher"},
    {"Date (exemple)": "2026-11-09", "Entité": "FINAL TEC PLATFORM", "Source": "Simulation interne", "Référence": "DEMO-FT-002", "Devise": "USD", "Montant": 400.00, "Statut": "Scénario fictif"},
    {"Date (exemple)": "2026-11-08", "Entité": "EDGE FINDS", "Source": "Donnée synthétique", "Référence": "DEMO-EF-003", "Devise": "EUR", "Montant": 75.00, "Statut": "Anomalie simulée"},
]


def render_financial_command_center() -> None:
    """Render an isolated, synthetic-only financial operations dashboard."""
    st.subheader("🏦 SOWIA FINANCIAL COMMAND CENTER")
    st.caption(
        "Prototype de pilotage multi-entités · données entièrement fictives · "
        "lecture seule · aucune connexion à un compte bancaire ou à PayPal."
    )
    st.warning(
        "MODE DÉMONSTRATION — les chiffres, événements et anomalies affichés sont inventés. "
        "Ils ne représentent ni trésorerie, ni revenus, ni paiements réellement reçus."
    )

    entity = st.selectbox(
        "Périmètre de consultation",
        list(ENTITIES),
        key="financial_command_center_entity",
    )
    data = ENTITIES[entity]
    scenario = data["scenario"]
    currency = data["currency"]

    st.markdown(f"### {entity}")
    st.caption(data["description"] + f" · Devise de référence de démonstration : {currency}")
    st.caption("Chaque entité conserve son propre sous-registre. Aucun solde inter-entités n'est calculé.")

    metrics = st.columns(4)
    metrics[0].metric("Entrées simulées", f"{scenario['inflow']:,.2f} {currency}")
    metrics[1].metric("Frais simulés", f"{scenario['fees']:,.2f} {currency}")
    metrics[2].metric("Remboursements simulés", f"{scenario['refunds']:,.2f} {currency}")
    metrics[3].metric("En attente (simulation)", f"{scenario['pending']:,.2f} {currency}")

    st.markdown("#### Contrôles opérationnels")
    controls = st.columns(3)
    controls[0].metric("Anomalies fictives", scenario["anomalies"])
    controls[1].metric("Événements à rapprocher", 1 if scenario["pending"] else 0)
    controls[2].metric("Écritures comptabilisées", 0)
    st.caption(
        "Aucune écriture n'est comptabilisée dans ce prototype. "
        "Les compteurs servent uniquement à tester la présentation."
    )

    st.markdown("#### Événements de démonstration")
    selected_rows = [row for row in SAMPLE_EVENTS if row["Entité"] == entity]
    st.dataframe(selected_rows, use_container_width=True, hide_index=True)
    st.caption(
        "Les références DEMO-* sont fictives. Les événements de Sandbox, les données rapprochées "
        "et les écritures comptabilisées devront rester des catégories distinctes."
    )

    with st.expander("Architecture et règles de sécurité"):
        st.markdown(
            "- Un sous-registre logique distinct par entité, propriétaire et devise.\n"
            "- Aucun cumul entre EUR et USD sans conversion documentée, datée et sourcée.\n"
            "- Séparation stricte entre événement prestataire, rapprochement, écriture comptabilisée et scénario.\n"
            "- Remboursements rattachés à la capture d'origine, dans la même devise et sous plafond cumulé.\n"
            "- Accès selon le rôle et l'entité ; journal d'audit immuable ; moindre privilège.\n"
            "- Les décisions sensibles restent soumises à validation humaine explicite."
        )

    st.info(
        "Étape suivante avant toute donnée réelle : achever les tests RLS à deux utilisateurs "
        "dans un projet Supabase isolé, puis faire valider le modèle d'accès et les rapprochements."
    )
