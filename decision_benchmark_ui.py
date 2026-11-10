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

    if "sowia_pending_decision_draft" not in st.session_state:
        st.session_state["sowia_pending_decision_draft"] = None

    with st.expander("＋ Étape 1 — enregistrer votre choix humain à l'aveugle", expanded=not rows):
        with st.form("sowia_human_choice_form", clear_on_submit=True):
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
            option_names = [
                st.text_input(f"Option {index + 1}", max_chars=120, key=f"blind_option_name_{index}")
                for index in range(4)
            ]
            valid_names = [name.strip() for name in option_names if name.strip()]
            human_choice = st.selectbox(
                "Votre choix humain — SOW IA ne révèle pas encore son classement",
                valid_names if valid_names else ["Renseignez d'abord les options"],
            )
            save_human = st.form_submit_button("Verrouiller mon choix humain", type="primary")
        if save_human:
            try:
                if not title.strip() or not question.strip() or len(valid_names) < 2:
                    raise ValueError("Renseignez le titre, la question et au moins deux options.")
                if len({name.casefold() for name in valid_names}) != len(valid_names):
                    raise ValueError("Les noms des options doivent être uniques.")
                if human_choice not in valid_names:
                    raise ValueError("Sélectionnez une option valide.")
                st.session_state["sowia_pending_decision_draft"] = {
                    "title": title.strip(), "question": question.strip(),
                    "category": category, "context": context.strip(),
                    "option_names": valid_names, "human_choice": human_choice,
                }
                st.success("Votre choix humain est verrouillé dans cette session. Passez à l'évaluation séparée de SOW IA.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    draft = st.session_state.get("sowia_pending_decision_draft")
    if draft:
        st.markdown("### Étape 2 — évaluation structurée de SOW IA")
        st.write("**Décision :**", draft["title"])
        st.write("**Choix humain déjà verrouillé :**", draft["human_choice"])
        st.caption(
            "Le choix SOW IA est calculé seulement maintenant. Les critères ci-dessous "
            "constituent une évaluation structurée des options, et non une vérification "
            "automatique de faits externes."
        )
        with st.form("sowia_ai_evaluation_form"):
            options = []
            for index, name in enumerate(draft["option_names"]):
                st.markdown(f"**{name}**")
                scores = {}
                columns = st.columns(2)
                for score_index, criterion in enumerate(CRITERIA):
                    with columns[score_index % 2]:
                        scores[criterion] = st.slider(
                            f"{CRITERIA_LABELS[criterion]} · {name}",
                            min_value=0.0, max_value=5.0, value=3.0, step=0.5,
                            key=f"blind_score_{index}_{criterion}",
                        )
                legal = st.selectbox(
                    f"État juridique · {name}",
                    ["review_required", "verified", "prohibited"],
                    format_func=lambda value: {
                        "review_required": "À vérifier",
                        "verified": "Vérifié pour le périmètre étudié",
                        "prohibited": "Interdit / non autorisé",
                    }[value],
                    key=f"blind_legal_{index}",
                )
                risk = st.selectbox(
                    f"Niveau de risque · {name}",
                    ["low", "medium", "high", "critical"],
                    format_func=lambda value: {
                        "low": "Faible", "medium": "Modéré",
                        "high": "Élevé", "critical": "Critique",
                    }[value],
                    key=f"blind_risk_{index}",
                )
                options.append({
                    "name": name, "scores": scores,
                    "legal_state": legal, "risk_level": risk,
                })
            save_both = st.form_submit_button("Calculer et enregistrer le choix SOW IA", type="primary")
        if save_both:
            try:
                record = create_decision_record(
                    title=draft["title"], question=draft["question"],
                    context=draft["context"], human_choice=draft["human_choice"],
                    options=options, workspace_id=workspace_id,
                )
                payload = {
                    "user_id": str(current_user.id),
                    "workspace_id": workspace_id,
                    "title": record["title"], "question": record["question"],
                    "context": record["context"], "category": draft["category"],
                    "human_choice": record["human_choice"],
                    "ai_choice": record["ai_choice"],
                    "ai_rationale": record["ai_rationale"],
                    "options": record["options"],
                    "decision_hash": record["decision_hash"],
                    "decided_at": record["decided_at"],
                }
                supabase_client.table("sowia_decision_trials").insert(payload).execute()
                st.session_state["sowia_pending_decision_draft"] = None
                st.success("Les choix humain et SOW IA sont enregistrés séparément dans votre espace privé.")
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
