"""SOWIA GLOBAL PORTFOLIO CONTROL — explainable, human-supervised portfolio view."""
from datetime import date


def _country(value):
    return " ".join(str(value or "").strip().casefold().split())


def _latest_observations(rows):
    latest = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        key = str(row.get("action_plan_id") or "").strip()
        if not key:
            continue
        stamp = str(row.get("observed_at") or row.get("created_at") or "")
        if key not in latest or stamp > latest[key][0]:
            latest[key] = (stamp, row)
    return {key: value[1] for key, value in latest.items()}


def build_portfolio(plans, performance_observations, alerts, assessments, today=None):
    """Aggregate only supplied, already-authorized rows; never infer a global score."""
    today = today or date.today()
    if isinstance(today, str):
        today = date.fromisoformat(today)
    latest = _latest_observations(performance_observations)
    active_alerts = [
        row for row in (alerts or [])
        if isinstance(row, dict) and row.get("status") == "active"
    ]
    markets = {}
    for row in assessments or []:
        if isinstance(row, dict) and _country(row.get("country")):
            markets.setdefault(_country(row["country"]), []).append(row)

    country_buckets = {}
    currency_totals = {}
    plan_rows = []
    for plan in plans or []:
        if not isinstance(plan, dict):
            continue
        country = str(plan.get("country") or "Non précisé").strip()
        key = _country(country) or "non précisé"
        bucket = country_buckets.setdefault(key, {
            "country": country, "plans": 0, "overdue_plans": 0,
            "over_budget_plans": 0, "measured_plans": 0,
            "active_alerts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "market_assessments": 0, "market_scores": [],
        })
        bucket["plans"] += 1
        due = str(plan.get("due_date") or "")[:10]
        overdue = False
        try:
            overdue = due and date.fromisoformat(due) < today and plan.get("status") not in {"completed", "cancelled", "rejected"}
        except ValueError:
            overdue = False
        if overdue:
            bucket["overdue_plans"] += 1
        currency = str(plan.get("currency") or "N/A").upper()
        totals = currency_totals.setdefault(currency, {"authorized_budget": 0.0, "latest_cumulative_spend": 0.0})
        try:
            totals["authorized_budget"] += float(plan.get("budget_cap") or 0)
        except (TypeError, ValueError):
            pass
        observation = latest.get(str(plan.get("id") or ""))
        spend = None
        progress = None
        over_budget = False
        if observation:
            bucket["measured_plans"] += 1
            try:
                spend = float(observation.get("actual_spend_cumulative") or 0)
                cap = float(observation.get("budget_cap_snapshot", plan.get("budget_cap")) or 0)
                over_budget = spend > cap
            except (TypeError, ValueError):
                spend = None
            try:
                raw_progress = observation.get("progress_percent")
                progress = float(raw_progress) if raw_progress not in (None, "") else None
            except (TypeError, ValueError):
                progress = None
            if over_budget:
                bucket["over_budget_plans"] += 1
            if spend is not None:
                totals["latest_cumulative_spend"] += spend
        plan_rows.append({
            "id": str(plan.get("id") or ""),
            "title": str(plan.get("title") or "Plan sans titre"),
            "country": country,
            "status": str(plan.get("status") or "inconnu"),
            "due_date": due,
            "budget_cap": plan.get("budget_cap"),
            "currency": str(plan.get("currency") or ""),
            "overdue": bool(overdue),
            "measured": bool(observation),
            "latest_spend": spend,
            "progress_percent": progress,
            "over_budget": over_budget,
        })

    for alert in active_alerts:
        key = _country(alert.get("country"))
        if key in country_buckets:
            level = str(alert.get("level") or "low")
            if level in country_buckets[key]["active_alerts"]:
                country_buckets[key]["active_alerts"][level] += 1
    for key, rows in markets.items():
        if key not in country_buckets:
            continue
        country_buckets[key]["market_assessments"] = len(rows)
        country_buckets[key]["market_scores"] = [
            float(row["weighted_score"]) for row in rows
            if row.get("weighted_score") is not None
        ]

    countries = []
    for bucket in country_buckets.values():
        reasons = []
        if bucket["overdue_plans"]:
            reasons.append("Échéance dépassée")
        if bucket["over_budget_plans"]:
            reasons.append("Dépenses supérieures au plafond")
        if bucket["active_alerts"]["critical"] or bucket["active_alerts"]["high"]:
            reasons.append("Alerte active critique ou élevée")
        if not bucket["measured_plans"]:
            reasons.append("Aucune mesure de performance")
        if reasons[:3] and any(x in reasons for x in ("Échéance dépassée", "Dépenses supérieures au plafond", "Alerte active critique ou élevée")):
            status = "REVIEW_URGENTLY"
        elif not bucket["measured_plans"]:
            status = "INSUFFICIENT_DATA"
        elif bucket["active_alerts"]["medium"] or bucket["active_alerts"]["low"]:
            status = "MONITOR"
        else:
            status = "CONTINUE_TRACKING"
        scores = bucket.pop("market_scores")
        bucket["average_market_assessment"] = round(sum(scores) / len(scores), 1) if scores else None
        bucket["review_status"] = status
        bucket["review_reasons"] = reasons or ["Aucun signal prioritaire détecté dans les données disponibles"]
        countries.append(bucket)
    countries.sort(key=lambda row: (
        {"REVIEW_URGENTLY": 0, "INSUFFICIENT_DATA": 1, "MONITOR": 2, "CONTINUE_TRACKING": 3}[row["review_status"]],
        -row["overdue_plans"], -row["over_budget_plans"], row["country"].casefold()
    ))
    currency_breakdown = {
        currency: {
            "authorized_budget": round(values["authorized_budget"], 2),
            "latest_cumulative_spend": round(values["latest_cumulative_spend"], 2),
            "remaining_vs_cap": round(values["authorized_budget"] - values["latest_cumulative_spend"], 2),
        }
        for currency, values in currency_totals.items()
    }
    return {
        "summary": {
            "plans": len(plan_rows),
            "measured_plans": sum(row["measured"] for row in plan_rows),
            "overdue_plans": sum(row["overdue"] for row in plan_rows),
            "over_budget_plans": sum(row["over_budget"] for row in plan_rows),
            "active_alerts": len(active_alerts),
            "countries": len(country_buckets),
        },
        "countries": countries,
        "plans": plan_rows,
        "currency_breakdown": currency_breakdown,
        "methodology": [
            "Vue limitée aux plans créés par le compte connecté et aux données privées auxquelles il a accès.",
            "Aucun score global opaque : les signaux sont affichés séparément et les règles de revue sont explicites.",
            "Les alertes sont des signaux à vérifier, pas des constats juridiques ou des évaluations de risque certifiées.",
            "Les mesures financières sont des plafonds et cumuls déclarés, pas des transactions bancaires rapprochées.",
            "Les budgets restent séparés par devise ; aucune conversion ni somme inter-devises n'est effectuée.",
            "Les évaluations de marché sont indicatives et déclarées ; leur qualité n'est pas vérifiée automatiquement.",
            "Aucun budget n'est déplacé, aucun achat n'est déclenché et aucune décision n'est exécutée automatiquement.",
        ],
    }
