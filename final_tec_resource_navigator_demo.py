"""Démo locale hors ligne de FINAL TEC Resource Navigator.

Toutes les ressources et mesures de cette page sont fictives et servent uniquement
à illustrer le moteur de sélection. Aucun réseau, fournisseur, workload ou paiement.
Lancer avec : streamlit run final_tec_resource_navigator_demo.py
"""
from __future__ import annotations

from datetime import datetime, timezone
import json

import streamlit as st

from final_tec_edge_engine import select_edge_resources


st.set_page_config(page_title="FINAL TEC Resource Navigator — DEMO", page_icon="🧭", layout="wide")
st.title("🧭 FINAL TEC Resource Navigator")
st.caption("Prototype de démonstration hors ligne — données entièrement fictives")

st.warning(
    "MODE DÉMONSTRATION : les ressources, mesures, tarifs et scores affichés ci-dessous "
    "sont des exemples inventés pour tester l'interface. Ils ne décrivent aucune capacité "
    "réelle, aucun fournisseur disponible et aucune performance de FINAL TEC."
)

DEMO_NOW = datetime.now(timezone.utc).isoformat()
DEMO_CANDIDATES = [
    {
        "resource_id": "DEMO-EDGE-01",
        "authorized": True,
        "features": ["gpu", "low-latency", "eu-data"],
        "benchmark": {
            "benchmark_id": "DEMO-BENCH-001", "workload_type": "inference",
            "region": "eu-west", "ended_at": DEMO_NOW,
            "latency_summary_ms": {"p95_nearest_rank": 42.0},
            "availability": {"success_rate": 0.992},
            "cost": {"amount": 1.25, "currency": "EUR", "basis": "per_1000_requests"},
            "evidence_status": "demo_only", "publication_state": "demo_only",
        },
    },
    {
        "resource_id": "DEMO-CLOUD-02",
        "authorized": True,
        "features": ["gpu", "eu-data"],
        "benchmark": {
            "benchmark_id": "DEMO-BENCH-002", "workload_type": "inference",
            "region": "eu-west", "ended_at": DEMO_NOW,
            "latency_summary_ms": {"p95_nearest_rank": 68.0},
            "availability": {"success_rate": 0.999},
            "cost": {"amount": 0.85, "currency": "EUR", "basis": "per_1000_requests"},
            "evidence_status": "demo_only", "publication_state": "demo_only",
        },
    },
    {
        "resource_id": "DEMO-UNVERIFIED-03",
        "authorized": True,
        "features": ["gpu", "low-latency", "eu-data"],
        "benchmark": {
            "benchmark_id": "DEMO-BENCH-003", "workload_type": "inference",
            "region": "eu-west", "ended_at": DEMO_NOW,
            "latency_summary_ms": {"p95_nearest_rank": 25.0},
            "availability": {"success_rate": 1.0},
            "cost": {"amount": 0.50, "currency": "EUR", "basis": "per_1000_requests"},
            "evidence_status": "pending", "publication_state": "draft",
        },
    },
    {
        "resource_id": "DEMO-NOT-AUTHORIZED-04",
        "authorized": False,
        "features": ["gpu", "low-latency", "eu-data"],
        "benchmark": {
            "benchmark_id": "DEMO-BENCH-004", "workload_type": "inference",
            "region": "eu-west", "ended_at": DEMO_NOW,
            "latency_summary_ms": {"p95_nearest_rank": 30.0},
            "availability": {"success_rate": 0.999},
            "cost": {"amount": 0.70, "currency": "EUR", "basis": "per_1000_requests"},
            "evidence_status": "demo_only", "publication_state": "demo_only",
        },
    },
]

st.subheader("1. Définir le besoin")
left, right = st.columns(2)
with left:
    workload = st.selectbox("Type de charge", ["inference", "embedding", "batch", "edge_inference"])
    region = st.selectbox("Région", ["eu-west", "eu-central", "us-east"])
    max_latency = st.number_input("Latence p95 maximale (ms)", min_value=1.0, max_value=10000.0, value=100.0)
with right:
    min_success = st.slider("Taux de succès minimal", min_value=0.50, max_value=1.00, value=0.98, step=0.001)
    max_cost = st.number_input("Budget maximal (EUR / 1 000 requêtes)", min_value=0.01, max_value=1000.0, value=2.0)
    required_features = st.multiselect("Fonctions requises", ["gpu", "low-latency", "eu-data"], default=["gpu"])

st.subheader("2. Pondération du classement")
w1, w2, w3 = st.columns(3)
with w1:
    latency_weight = st.slider("Latence", 0, 100, 40)
with w2:
    availability_weight = st.slider("Disponibilité", 0, 100, 35)
with w3:
    cost_weight = st.slider("Coût", 0, 100, 25)

weight_total = latency_weight + availability_weight + cost_weight
if weight_total == 0:
    st.error("Au moins un poids doit être supérieur à zéro.")
    st.stop()

profile = {
    "workload_type": workload,
    "region": region,
    "max_latency_ms": max_latency,
    "min_success_rate": min_success,
    "max_cost_amount": max_cost,
    "currency": "EUR",
    "cost_basis": "per_1000_requests",
    "required_features": required_features,
}
weights = {
    "latency": latency_weight,
    "availability": availability_weight,
    "cost": cost_weight,
}

st.subheader("3. Comparer les ressources fictives")
if st.button("Lancer la simulation locale", type="primary", use_container_width=True):
    try:
        result = select_edge_resources(
            profile, DEMO_CANDIDATES, now=DEMO_NOW, max_age_seconds=86400,
            weights=weights, allow_demo_evidence=True
        )
        st.session_state["final_tec_demo_result"] = result
        st.session_state["final_tec_demo_profile_signature"] = json.dumps(
            {"profile": profile, "weights": weights}, sort_keys=True
        )
    except Exception as exc:
        st.error(f"Simulation impossible : {exc}")

current_signature = json.dumps({"profile": profile, "weights": weights}, sort_keys=True)
saved_signature = st.session_state.get("final_tec_demo_profile_signature")
result = (
    st.session_state.get("final_tec_demo_result")
    if saved_signature == current_signature
    else None
)
if saved_signature is not None and saved_signature != current_signature:
    st.info("Les paramètres ont changé. Relancez la simulation pour obtenir un résultat correspondant aux nouveaux critères.")

if result:
    st.divider()
    if result["selected_resource_id"]:
        st.success(f"Recommandation simulée : {result['selected_resource_id']}")
    else:
        st.error("Aucune ressource fictive ne satisfait les contraintes.")

    st.caption("Le score est un indice pédagogique normalisé selon les poids choisis ; ce n'est pas une mesure de performance réelle.")
    if result["ranking"]:
        st.markdown("#### Ressources admissibles — classement simulé")
        rows = []
        for item in result["ranking"]:
            rows.append({
                "Ressource DEMO": item["resource_id"],
                "Score simulé": item["score"],
                "Latence p95 fictive (ms)": item["measured_p95_ms"],
                "Taux de succès fictif": item["measured_success_rate"],
                "Coût fictif (EUR)": item["measured_cost"]["amount"],
                "ID de preuve DEMO": item["benchmark_id"],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    if result["excluded"]:
        st.markdown("#### Ressources exclues")
        for item in result["excluded"]:
            with st.expander(f"{item['resource_id']} — exclue"):
                st.write("Motifs :", ", ".join(item["exclusion_reasons"]))

    st.markdown("#### Traçabilité de la simulation")
    st.json({
        "mode": result["mode"],
        "decision": result["decision"],
        "weights": result["weights"],
        "side_effects": result["side_effects"],
    })
    st.download_button(
        "Télécharger le rapport JSON de démonstration",
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name="final_tec_resource_navigator_demo.json",
        mime="application/json",
        use_container_width=True,
    )

st.divider()
st.markdown("**Limites de cette version**")
st.write(
    "- Données fictives, codées dans ce fichier et explicitement marquées DEMO.\n"
    "- Aucune ressource réelle n'est découverte, vérifiée ou réservée.\n"
    "- Aucun fournisseur n'est contacté ; aucune charge n'est exécutée.\n"
    "- Aucun achat, paiement, appel réseau ou écriture en base de données.\n"
    "- Le prototype n'est pas intégré à l'application publique SOWIA et n'est pas déployé."
)
