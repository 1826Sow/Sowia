"""Streamlit interface for the human-vs-SOW IA decision benchmark."""
from __future__ import annotations

import streamlit as st

from decision_lab import create_decision_record, evaluate_decision_outcomes, CRITERIA
from decision_statistics import summarize_decisions

CRITERIA_LABELS = {
    "strategic_fit": "Alignement stratégique",
    "customer_value": "Valeur client",
    "feasibility": "Faisabilité",
    "economic_value": "Valeur économique",
    "resilience": "Résilience",
    "evidence_quality": "Qualité des preuves",
    "reversibility": "Réversibilité",
}


def render_decision_benchmark(supabase_client, current_user, workspace_id: str) -> None:
    st.subheader("⚖️ Décisions humaines vs SOW IA")
    st.caption(
        "Un laboratoire de comparaison : le choix humain est enregistré avec le choix "
        "structuré de SOW IA, puis les résultats réels sont évalués ultérieurement."
    )
    st.info(
        "Transparence : dans cette première version, SOW IA classe les notes et les "
        "informations saisies selon une pondération explicite. Ce n'est pas encore une "
        "analyse autonome de preuves externes. Les décisions à risque élevé ou dont la "
        "conformité n'est pas vérifiée sont exclues du choix IA."
    )
    if supabase_client is None or current_user is None:
        st.warning(
            "Connectez-vous à votre compte sécurisé pour enregistrer les décisions. "
            "Le stockage durable et les statistiques multi-sessions nécessitent Supabase."
        )
        return

    try:
        rows = (
            supabase_client.table("sowia_decision_trials")
            .select("*")
            .eq("user_id", str(current_user.id))
            .eq("workspace_id", workspace_id)
            .order("decided_at", desc=True)
            .limit(200)
            .execute()
            .data or []
        )
    except Exception:
        st.error(
            "Le laboratoire n'est pas encore relié à la base. "
            "La migration supabase_decision_trials.sql doit être appliquée dans Supabase."
        )
        return

    with st.expander("＋ Enregistrer une nouvelle décision", expanded=not rows):
        with st.form("sowia_human_ai_decision_form", clear_on_submit=True):
            title = st.text_input("Titre de la décision", max_chars=160)
            question = st.text_area("Question stratégique", max_chars=500)
            category = st.selectbox(
                "Domaine", [
                    "Stratégie d'entreprise", "Finance", "Commercial / marketing",
                    "Technologie", "Ressources humaines", "Partenariat",
                    "Opérations", "Autre",
                ],
            )
            context = st.text_area(
                "Contexte et éléments connus (sans données personnelles sensibles)",
                max_chars=4000,
            )
            st.markdown("**Présentez de 2 à 4 options**")
            option_names = []
            option_scores = []
            option_controls = []
            for index in range(4):
                st.markdown(f"**Option {index + 1}**")
                name = st.text_input(
                    f"Nom de l'option {index + 1}",
                    max_chars=120,
                    key=f"decision_option_name_{index}",
                )
                option_names.append(name.strip())
                scores = {}
                columns = st.columns(2)
                for score_index, criterion in enumerate(CRITERIA):
                    with columns[score_index % 2]:
                        scores[criterion] = st.slider(
                            f"{CRITERIA_LABELS[criterion]} · option {index + 1}",
                            min_value=0.0, max_value=5.0, value=3.0, step=0.5,
                            key=f"decision_{index}_{criterion}",
                        )
                legal = st.selectbox(
                    f"Vérification juridique · option {index + 1}",
                    ["review_required", "verified", "prohibited"],
                    format_func=lambda value: {
                        "review_required": "À vérifier",
                        "verified": "Vérifiée pour ce périmètre",
                        "prohibited": "Interdite / non autorisée",
                    }[value],
                    key=f"decision_legal_{index}",
                )
                risk = st.selectbox(
                    f"Niveau de risque · option {index + 1}",
                    ["low", "medium", "high", "critical"],
                    format_func=lambda value: {
                        "low": "Faible", "medium": "Modéré",
                        "high": "Élevé", "critical": "Critique",
                    }[value],
                    key=f"decision_risk_{index}",
                )
                option_scores.append({"name": name.strip(), "scores": scores,
                                      "legal_state": legal, "risk_level": risk})
                option_controls.append((legal, risk))
            valid_names = [name for name in option_names if name]
            human_choice = st.selectbox(
                "Votre choix humain (enregistré avant affichage du choix IA)",
                valid_names if valid_names else ["Renseignez d'abord les options"],
            )
            submit = st.form_submit_button("Enregistrer les deux décisions", type="primary")

        if submit:
            try:
                options = [item for item in option_scores if item["name"]]
                if len(options) < 2:
                    raise ValueError("Renseignez au moins deux options nommées.")
                record = create_decision_record(
                    title=title, question=question, context=context,
                    human_choice=human_choice, options=options,
                    workspace_id=workspace_id,
                )
                payload = {
                    "user_id": str(current_user.id),
                    "workspace_id": workspace_id,
                    "title": record["title"],
                    "question": record["question"],
                    "context": record["context"],
                    "category": category,
                    "human_choice": record["human_choice"],
                    "ai_choice": record["ai_choice"],
                    "ai_rationale": record["ai_rationale"],
                    "options": record["options"],
                    "decision_hash": record["decision_hash"],
                    "decided_at": record["decided_at"],
                }
                supabase_client.table("sowia_decision_trials").insert(payload).execute()
                st.success("Les deux décisions ont été enregistrées dans votre espace privé.")
                st.rerun()
            except Exception as exc:
                st.error(f"Enregistrement impossible : {type(exc).__name__} — {exc}")

    st.markdown("### Résultats des décisions enregistrées")
    if not rows:
        st.info("Aucune décision enregistrée pour le moment.")
        return

    stats = summarize_decisions(rows)
    overall = stats["overall"]
    metric_cols = st.columns(4)
    metric_cols[0].metric("Décisions évaluées", overall["sample_size"])
    metric_cols[1].metric("Victoires humaines", overall["human_wins"])
    metric_cols[2].metric("Victoires SOW IA", overall["ai_wins"])
    metric_cols[3].metric("Égalités", overall["ties"])
    st.caption(
        f"{stats['excluded_incomplete']} décision(s) exclue(s) des statistiques "
        "car leur résultat réel n'est pas encore renseigné."
    )
    if stats["by_category"]:
        st.markdown("**Statistiques par domaine**")
        st.dataframe(
            [{
                "Domaine": name, "Échantillon": item["sample_size"],
                "Humain (%)": item["human_win_rate_pct"],
                "SOW IA (%)": item["ai_win_rate_pct"],
                "Égalités (%)": item["tie_rate_pct"],
                "Écart moyen IA - humain": item["mean_ai_minus_human"],
            } for name, item in stats["by_category"].items()],
            use_container_width=True, hide_index=True,
        )
    st.caption(stats["interpretation"])

    pending = [row for row in rows if not row.get("evaluated_at")]
    if pending:
        st.markdown("### Évaluer les résultats réels")
        st.caption(
            "Saisissez une note de résultat de 0 à 100 pour chaque option, selon "
            "une même méthode et après un délai suffisant. Les notes ne sont pas des prédictions."
        )
        for row in pending[:20]:
            with st.expander(f"{row.get('title', 'Décision')} · {row.get('decided_at', '')[:10]}"):
                st.write("**Question :**", row.get("question"))
                st.write("**Choix humain :**", row.get("human_choice"))
                st.write("**Choix SOW IA :**", row.get("ai_choice") or "Aucun choix éligible")
                st.write("**Motif SOW IA :**", row.get("ai_rationale"))
                with st.form(f"decision_outcome_{row['id']}"):
                    outcome_scores = {}
                    for option in row.get("options", []):
                        outcome_scores[option["name"]] = st.slider(
                            f"Résultat réel — {option['name']}",
                            min_value=0.0, max_value=100.0, value=50.0, step=1.0,
                            key=f"outcome_{row['id']}_{option['name']}",
                        )
                    save_outcome = st.form_submit_button("Enregistrer l'évaluation réelle")
                if save_outcome:
                    try:
                        result = evaluate_decision_outcomes(row, outcome_scores)
                        supabase_client.table("sowia_decision_trials").update({
                            "outcomes": result["outcomes"],
                            "human_outcome": result["human_outcome"],
                            "ai_outcome": result["ai_outcome"],
                            "winner": result["winner"],
                            "outcome_difference": result["difference"],
                            "evaluated_at": result["evaluated_at"],
                        }).eq("id", row["id"]).eq("user_id", str(current_user.id)).is_("evaluated_at", "null").execute()
                        st.success("Résultat réel enregistré. La décision initiale reste verrouillée.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Évaluation impossible : {type(exc).__name__} — {exc}")

    st.markdown("### Historique des décisions")
    st.dataframe(
        [{
            "Date": row.get("decided_at", "")[:10],
            "Décision": row.get("title"),
            "Domaine": row.get("category", "Non classé"),
            "Humain": row.get("human_choice"),
            "SOW IA": row.get("ai_choice") or "Aucun choix éligible",
            "Résultat": row.get("winner") or "En attente",
        } for row in rows],
        use_container_width=True, hide_index=True,
    )
