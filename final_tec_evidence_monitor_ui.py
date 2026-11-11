"""FINAL TEC evidence intake and session-only monitoring interface."""
from __future__ import annotations

import json
from typing import Any

from final_tec_evidence_intake import EvidenceIntakeError
from final_tec_evidence_monitor import prepare_evidence_batch, build_evidence_monitor_snapshot


def render_evidence_monitor(st: Any) -> None:
    st.subheader("FINAL TEC — Registre de preuves & suivi")
    st.caption("Collecte contrôlée des éléments justificatifs et suivi de leur état de validation.")
    st.warning(
        "Les soumissions restent en attente et en brouillon. Elles ne sont pas vérifiées "
        "ni publiées. Les données sont conservées uniquement dans la session Streamlit : "
        "aucune écriture Supabase, aucun flux fournisseur et aucune télémétrie temps réel."
    )
    st.markdown("#### 1 · Ajouter un lot de preuves")
    example = [
        {
            "metric_key": "edge_test_latency",
            "title": "Rapport de test de latence Edge",
            "category": "ai_edge_tests",
            "metric_value": None,
            "unit": "ms",
            "source_url": "https://example.org/report",
            "observed_at": "2026-11-11T10:00:00+00:00",
            "evidence_ref": "rapport-a-verifier-001",
            "evidence_owner": "Équipe technique",
        }
    ]
    payload_text = st.text_area(
        "Soumissions JSON (liste)",
        value=json.dumps(example, ensure_ascii=False, indent=2),
        height=280,
        key="final_tec_evidence_batch_json",
        help="Chaque élément exige metric_key, title, category et evidence_owner. Les champs inconnus sont rejetés.",
    )
    if st.button("Valider le format et ajouter à la session", key="final_tec_evidence_add_batch"):
        try:
            batch = prepare_evidence_batch(json.loads(payload_text))
            existing = st.session_state.get("final_tec_evidence_session_records", [])
            existing_keys = {row.get("metric_key") for row in existing}
            duplicates = existing_keys.intersection(row["metric_key"] for row in batch)
            if duplicates:
                st.error("Identifiants déjà présents dans cette session : " + ", ".join(sorted(duplicates)))
            else:
                st.session_state["final_tec_evidence_session_records"] = existing + batch
                st.success(f"{len(batch)} soumission(s) ajoutée(s) à la session, en attente de revue.")
        except (json.JSONDecodeError, EvidenceIntakeError) as exc:
            st.error("Lot refusé : " + str(exc))

    records = st.session_state.get("final_tec_evidence_session_records", [])
    snapshot = build_evidence_monitor_snapshot(records)
    st.markdown("#### 2 · Suivi du registre")
    st.caption(snapshot["notice"])
    cols = st.columns(4)
    cols[0].metric("Soumissions", snapshot["total_submissions"])
    cols[1].metric("En attente", snapshot["pending"])
    cols[2].metric("Vérifiées", snapshot["verified"])
    cols[3].metric("Projections / démos", snapshot["projected"] + snapshot["synthetic"])

    if snapshot["by_category"]:
        st.markdown("##### Volume par catégorie")
        st.bar_chart(snapshot["by_category"])
    if snapshot["timeline"]:
        st.markdown("##### Historique des soumissions")
        st.dataframe(snapshot["timeline"], use_container_width=True, hide_index=True)
        st.download_button(
            "Exporter le registre de session (JSON)",
            data=json.dumps(records, ensure_ascii=False, indent=2),
            file_name="final_tec_evidence_session_register.json",
            mime="application/json",
        )
    else:
        st.info("Aucune preuve n'a encore été ajoutée dans cette session.")

    if st.button("Effacer le registre de cette session", key="final_tec_evidence_clear_session"):
        st.session_state["final_tec_evidence_session_records"] = []
        st.rerun()
