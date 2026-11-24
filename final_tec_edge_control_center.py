"""Admin-only FINAL TEC EDGE control center; offline simulation, no persistence."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from final_tec_edge_engine import EdgeSelectionError, select_edge_resources


def parse_edge_inputs(profile_text: str, candidates_text: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Parse user-supplied JSON without reading files, secrets, or external sources."""
    try:
        profile = json.loads(profile_text)
        candidates = json.loads(candidates_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise EdgeSelectionError("Le profil et les ressources doivent être des JSON valides.") from exc
    if not isinstance(profile, dict):
        raise EdgeSelectionError("Le profil de tâche doit être un objet JSON.")
    if not isinstance(candidates, list):
        raise EdgeSelectionError("Les ressources candidates doivent être une liste JSON.")
    return profile, candidates


def render_control_center(st: Any) -> None:
    st.subheader("FINAL TEC EDGE — Centre de contrôle")
    st.caption(
        "Console de simulation hors ligne : comparaison des ressources explicitement "
        "autorisées, de leurs benchmarks publiés et de leurs contraintes."
    )
    st.warning(
        "Aucune donnée réelle n'est préchargée. Les données saisies restent dans cette "
        "session et ne sont pas enregistrées. Aucun fournisseur n'est contacté, aucune "
        "charge n'est exécutée et aucune dépense n'est déclenchée."
    )
    st.markdown("#### 1 · Définir le profil de la tâche")
    profile_text = st.text_area(
        "Profil JSON",
        value="{}",
        height=190,
        key="final_tec_edge_profile_json",
        help="Champs requis : workload_type, region, max_latency_ms, min_success_rate, "
             "max_cost_amount, currency, cost_basis. required_features est facultatif.",
    )
    st.markdown("#### 2 · Fournir les ressources autorisées")
    candidates_text = st.text_area(
        "Inventaire JSON des ressources",
        value="[]",
        height=260,
        key="final_tec_edge_candidates_json",
        help="Chaque ressource doit contenir resource_id, authorized=true, features et "
             "un benchmark verified/published avec mesures, source et date.",
    )
    max_age_hours = st.number_input(
        "Fraîcheur maximale des benchmarks (heures)",
        min_value=1,
        max_value=8760,
        value=24,
        step=1,
        key="final_tec_edge_max_age_hours",
    )
    if st.button("Lancer la simulation de sélection", type="primary", key="run_final_tec_edge_simulation"):
        try:
            profile, candidates = parse_edge_inputs(profile_text, candidates_text)
            result = select_edge_resources(
                profile,
                candidates,
                now=datetime.now(timezone.utc).isoformat(),
                max_age_seconds=int(max_age_hours) * 3600,
            )
        except EdgeSelectionError as exc:
            st.error(str(exc))
            return
        except Exception as exc:
            st.error("Simulation interrompue : " + type(exc).__name__)
            return

        st.markdown("#### 3 · Résultat")
        if result["decision"] == "recommendation":
            st.success("Ressource recommandée par la simulation : " + str(result["selected_resource_id"]))
        else:
            st.info("Aucune ressource ne satisfait toutes les contraintes.")
        st.caption(result["notice"])
        st.metric("Ressources évaluées", len(result["ranking"]) + len(result["excluded"]))
        st.metric("Ressources admissibles", len(result["ranking"]))
        st.metric("Ressources exclues", len(result["excluded"]))
        if result["ranking"]:
            st.markdown("##### Classement et scores explicables")
            st.dataframe(result["ranking"], use_container_width=True, hide_index=True)
        if result["excluded"]:
            st.markdown("##### Ressources écartées et motifs")
            st.dataframe(result["excluded"], use_container_width=True, hide_index=True)
        st.markdown("##### Garde-fous d'exécution")
        st.json(result["side_effects"])
        st.download_button(
            "Exporter le rapport JSON",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name="final_tec_edge_simulation_report.json",
            mime="application/json",
        )
