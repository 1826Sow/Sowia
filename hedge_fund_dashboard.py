"""Streamlit presentation for the read-only SOWIA Hedge Funds workspace."""
from __future__ import annotations

import json
import math
import streamlit as st

from hedge_fund_intelligence import analyze_monthly_net_returns, normalize_hedge_fund_profile


def render_hedge_fund_dashboard(st_module=st):
    st_module.title("🏛️ SOWIA Hedge Funds")
    st_module.caption(
        "Espace analytique en lecture seule. Les données saisies ici restent dans la session "
        "et ne sont ni envoyées à PayPal ni enregistrées dans le registre financier."
    )
    st_module.info(
        "Aucune donnée de fonds n'est préchargée. Les exemples et résultats doivent provenir "
        "de documents ou de sources que vous avez vérifiés."
    )

    with st_module.expander("1 · Fiche descriptive d'un fonds", expanded=True):
        with st_module.form("sowia_hedge_fund_profile_form"):
            left, right = st_module.columns(2)
            with left:
                fund_id = st_module.text_input("Identifiant interne")
                fund_name = st_module.text_input("Nom du fonds")
                manager = st_module.text_input("Société de gestion")
                strategy = st_module.selectbox(
                    "Stratégie",
                    ["long_short_equity", "global_macro", "event_driven", "relative_value",
                     "managed_futures", "multi_strategy", "quantitative", "credit", "other"],
                )
            with right:
                domicile = st_module.text_input("Domiciliation")
                currency = st_module.text_input("Devise de base (ex. USD)", max_chars=3)
                aum = st_module.number_input("Encours sous gestion (facultatif)", min_value=0.0, value=0.0)
                aum_date = st_module.text_input("Date de référence de l'encours (AAAA-MM-JJ)")
            source_url = st_module.text_input("URL HTTPS de la source")
            source_verified = st_module.checkbox("J'ai vérifié cette source")
            submitted = st_module.form_submit_button("Valider la fiche")
        if submitted:
            raw = {
                "fund_id": fund_id, "name": fund_name, "manager": manager,
                "strategy": strategy, "domicile": domicile, "base_currency": currency,
                "aum": aum if aum > 0 else None, "aum_as_of": aum_date or None,
                "source_url": source_url or None, "source_verified": source_verified,
            }
            try:
                profile = normalize_hedge_fund_profile(raw)
                st_module.session_state["sowia_hedge_fund_profile_preview"] = profile
                st_module.success("Fiche validée pour cette session. Elle n'a pas été enregistrée dans une base.")
            except ValueError as exc:
                st_module.error(str(exc))
        profile = st_module.session_state.get("sowia_hedge_fund_profile_preview")
        if profile:
            st_module.write({
                "Fonds": profile.name, "Gestionnaire": profile.manager,
                "Stratégie": profile.strategy, "Domiciliation": profile.domicile,
                "Devise": profile.base_currency, "Encours": profile.aum,
                "Source vérifiée": profile.source_verified,
            })

    with st_module.expander("2 · Analyse des rendements mensuels nets", expanded=True):
        st_module.caption(
            "Saisissez une série mensuelle complète en JSON. Exemple : "
            '[{"month":"2026-01-01","net_return":0.01},{"month":"2026-02-01","net_return":-0.005}]'
        )
        payload = st_module.text_area(
            "Série mensuelle (rendements en décimal)",
            key="sowia_hedge_fund_returns_json",
            height=130,
            placeholder='[{"month":"2026-01-01","net_return":0.01}]',
        )
        risk_free = st_module.number_input(
            "Taux sans risque annuel (%)", value=0.0, min_value=-99.9, max_value=100.0,
            step=0.25, key="sowia_hedge_fund_risk_free",
        )
        if st_module.button("Calculer les indicateurs", key="sowia_hedge_fund_calculate"):
            try:
                rows = json.loads(payload)
                if not isinstance(rows, list):
                    raise ValueError("La série doit être une liste JSON.")
                result = analyze_monthly_net_returns(
                    rows, risk_free_rate_annual_pct=risk_free
                )
                st_module.session_state["sowia_hedge_fund_metrics_preview"] = result
            except (json.JSONDecodeError, ValueError) as exc:
                st_module.error(f"Série non exploitable : {exc}")
        result = st_module.session_state.get("sowia_hedge_fund_metrics_preview")
        if result:
            st_module.caption(
                f"{result.observations} mois · du {result.first_month.isoformat()} "
                f"au {result.last_month.isoformat()}"
            )
            metrics = st_module.columns(3)
            metrics[0].metric("Rendement cumulé", f"{result.cumulative_return_pct:.2f} %")
            metrics[1].metric("Rendement annualisé", f"{result.annualized_return_pct:.2f} %")
            metrics[2].metric(
                "Drawdown maximal", f"{result.maximum_drawdown_pct:.2f} %"
            )
            risk = st_module.columns(2)
            risk[0].metric(
                "Volatilité annualisée",
                "Non calculable" if result.annualized_volatility_pct is None
                else f"{result.annualized_volatility_pct:.2f} %",
            )
            risk[1].metric(
                "Ratio de Sharpe indicatif",
                "Non calculable" if result.sharpe_ratio is None
                else f"{result.sharpe_ratio:.2f}",
            )
            st_module.warning(
                "Statistiques descriptives sur les rendements saisis. Elles ne constituent "
                "ni une prévision, ni une recommandation, ni une validation indépendante des données."
            )

    st_module.divider()
    st_module.subheader("3 · Prochaines extensions")
    st_module.markdown(
        "- Comparaison de stratégies et d'indices de référence avec devises explicites.\n"
        "- Contrôles de liquidité, levier, concentration et risque de contrepartie.\n"
        "- Sources documentées, datées et vérifiables avant toute donnée de marché.\n"
        "- Accès réservé et journalisation avant toute connexion à une base."
    )
