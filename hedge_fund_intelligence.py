"""Read-only hedge-fund profile validation and performance risk analytics.

This module does not fetch market data, recommend investments, rank funds, or place
orders. Performance inputs must be explicitly supplied monthly net returns in
decimal form (for example, 0.02 means +2%). Assets under management are never
summed across currencies.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from statistics import stdev
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse


SUPPORTED_STRATEGIES = frozenset({
    "long_short_equity",
    "global_macro",
    "event_driven",
    "relative_value",
    "managed_futures",
    "multi_strategy",
    "quantitative",
    "credit",
    "other",
})


@dataclass(frozen=True)
class HedgeFundProfile:
    fund_id: str
    name: str
    manager: str
    strategy: str
    domicile: str
    base_currency: str
    aum: float | None
    aum_as_of: date | None
    source_url: str | None
    source_verified: bool


@dataclass(frozen=True)
class HedgeFundPerformance:
    observations: int
    first_month: date
    last_month: date
    cumulative_return_pct: float
    annualized_return_pct: float
    annualized_volatility_pct: float | None
    maximum_drawdown_pct: float
    sharpe_ratio: float | None
    risk_free_rate_annual_pct: float


def _text(raw: Mapping[str, Any], key: str, *, limit: int = 160) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{key} doit être renseigné et respecter la longueur autorisée.")
    return value.strip()


def normalize_hedge_fund_profile(raw: Mapping[str, Any]) -> HedgeFundProfile:
    """Validate one fund profile while retaining explicit source confidence."""
    if not isinstance(raw, Mapping):
        raise ValueError("Le profil du fonds doit être un objet.")
    fund_id = _text(raw, "fund_id", limit=64)
    name = _text(raw, "name")
    manager = _text(raw, "manager")
    strategy = _text(raw, "strategy", limit=40).lower()
    if strategy not in SUPPORTED_STRATEGIES:
        raise ValueError("Stratégie de fonds non reconnue.")
    domicile = _text(raw, "domicile", limit=80)
    currency = _text(raw, "base_currency", limit=3).upper()
    if len(currency) != 3 or not currency.isascii() or not currency.isalpha():
        raise ValueError("La devise de base doit être un code alphabétique ISO à 3 lettres.")

    aum_raw = raw.get("aum")
    if aum_raw in (None, ""):
        aum = None
    else:
        if isinstance(aum_raw, bool):
            raise ValueError("L'encours sous gestion doit être numérique.")
        try:
            aum = float(aum_raw)
        except (TypeError, ValueError):
            raise ValueError("L'encours sous gestion doit être numérique.") from None
        if not math.isfinite(aum) or aum < 0:
            raise ValueError("L'encours sous gestion doit être fini et positif ou nul.")

    as_of_raw = raw.get("aum_as_of")
    if as_of_raw in (None, ""):
        aum_as_of = None
    else:
        if not isinstance(as_of_raw, str):
            raise ValueError("La date de référence de l'encours doit être au format AAAA-MM-JJ.")
        try:
            aum_as_of = date.fromisoformat(as_of_raw)
        except ValueError:
            raise ValueError("La date de référence de l'encours doit être au format AAAA-MM-JJ.") from None
    if aum is not None and aum_as_of is None:
        raise ValueError("La date de référence de l'encours est obligatoire.")

    source_url_raw = raw.get("source_url")
    if source_url_raw in (None, ""):
        source_url = None
    else:
        if not isinstance(source_url_raw, str):
            raise ValueError("L'URL source est invalide.")
        parsed = urlparse(source_url_raw.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("La source doit être une URL HTTPS.")
        source_url = source_url_raw.strip()

    verified_raw = raw.get("source_verified", False)
    if not isinstance(verified_raw, bool):
        raise ValueError("Le statut de vérification de la source doit être booléen.")
    if verified_raw and source_url is None:
        raise ValueError("Une source vérifiée doit comporter une URL.")

    return HedgeFundProfile(
        fund_id=fund_id,
        name=name,
        manager=manager,
        strategy=strategy,
        domicile=domicile,
        base_currency=currency,
        aum=aum,
        aum_as_of=aum_as_of,
        source_url=source_url,
        source_verified=verified_raw,
    )


def analyze_monthly_net_returns(
    observations: Iterable[Mapping[str, Any]],
    *,
    risk_free_rate_annual_pct: float = 0.0,
) -> HedgeFundPerformance:
    """Calculate descriptive statistics from a complete monthly return series.

    Each observation has an ISO date (YYYY-MM-DD) identifying the month and a
    decimal net return. No missing month is imputed and no benchmark is inferred.
    """
    if isinstance(risk_free_rate_annual_pct, bool):
        raise ValueError("Le taux sans risque doit être numérique.")
    try:
        risk_free = float(risk_free_rate_annual_pct)
    except (TypeError, ValueError):
        raise ValueError("Le taux sans risque doit être numérique.") from None
    if not math.isfinite(risk_free) or risk_free <= -100:
        raise ValueError("Le taux sans risque annuel doit être supérieur à -100 %.")

    rows = []
    for item in observations:
        if not isinstance(item, Mapping):
            raise ValueError("Chaque rendement doit être un objet.")
        month_raw = item.get("month")
        if not isinstance(month_raw, str):
            raise ValueError("Chaque rendement doit comporter un mois au format AAAA-MM-JJ.")
        try:
            month = date.fromisoformat(month_raw)
        except ValueError:
            raise ValueError("Chaque rendement doit comporter un mois au format AAAA-MM-JJ.") from None
        value = item.get("net_return")
        if isinstance(value, bool):
            raise ValueError("Le rendement net doit être numérique.")
        try:
            monthly_return = float(value)
        except (TypeError, ValueError):
            raise ValueError("Le rendement net doit être numérique.") from None
        if not math.isfinite(monthly_return) or monthly_return <= -1:
            raise ValueError("Le rendement mensuel doit être fini et supérieur à -100 %.")
        rows.append((month, monthly_return))

    if not rows:
        raise ValueError("Aucun rendement mensuel fourni.")
    rows.sort(key=lambda row: row[0])
    months = [row[0] for row in rows]
    if len(set(months)) != len(months):
        raise ValueError("Un seul rendement par mois est autorisé.")
    # Ensure a contiguous monthly series; missing data must not be silently filled.
    for previous, current in zip(months, months[1:]):
        expected_year = previous.year + (1 if previous.month == 12 else 0)
        expected_month = 1 if previous.month == 12 else previous.month + 1
        if (current.year, current.month) != (expected_year, expected_month):
            raise ValueError("La série mensuelle comporte un mois manquant.")

    returns = [row[1] for row in rows]
    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for monthly_return in returns:
        wealth *= 1.0 + monthly_return
        peak = max(peak, wealth)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - wealth) / peak)

    cumulative = wealth - 1.0
    periods = len(returns)
    annualized = wealth ** (12.0 / periods) - 1.0
    volatility = stdev(returns) * math.sqrt(12.0) if periods > 1 else None
    monthly_rf = (1.0 + risk_free / 100.0) ** (1.0 / 12.0) - 1.0
    excess = [value - monthly_rf for value in returns]
    sharpe = (sum(excess) / periods) / (stdev(returns) if periods > 1 and stdev(returns) > 0 else 0) * math.sqrt(12.0) if periods > 1 and stdev(returns) > 0 else None

    return HedgeFundPerformance(
        observations=periods,
        first_month=months[0],
        last_month=months[-1],
        cumulative_return_pct=cumulative * 100.0,
        annualized_return_pct=annualized * 100.0,
        annualized_volatility_pct=volatility * 100.0 if volatility is not None else None,
        maximum_drawdown_pct=max_drawdown * 100.0,
        sharpe_ratio=sharpe,
        risk_free_rate_annual_pct=risk_free,
    )
