"""Read-only portfolio analytics using explicitly supplied positions and quotes.

No orders, investment recommendations, FX conversion or price fetching are performed.
All positions in one calculation must use the same valuation currency.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Iterable, Mapping

from market_data import MarketObservation


@dataclass(frozen=True)
class PortfolioLine:
    symbol: str
    quantity: float
    average_cost: float
    currency: str


@dataclass(frozen=True)
class ValuedPosition:
    symbol: str
    quantity: float
    average_cost: float
    market_price: float
    currency: str
    invested_amount: float
    market_value: float
    unrealized_pnl: float
    unrealized_return_pct: float
    portfolio_weight_pct: float


@dataclass(frozen=True)
class PortfolioSummary:
    currency: str
    invested_amount: float
    market_value: float
    unrealized_pnl: float
    unrealized_return_pct: float | None
    positions: tuple[ValuedPosition, ...]
    missing_quotes: tuple[str, ...]


def _number(value: Any, field: str, *, allow_zero: bool = True) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} doit être numérique.")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} doit être numérique.") from None
    if not math.isfinite(result) or result < 0 or (not allow_zero and result == 0):
        raise ValueError(f"{field} doit être fini et positif.")
    return result


def normalize_portfolio_line(raw: Mapping[str, Any]) -> PortfolioLine:
    if not isinstance(raw, Mapping):
        raise ValueError("Chaque position doit être un objet.")
    symbol = raw.get("symbol")
    currency = raw.get("currency")
    if not isinstance(symbol, str) or not symbol.strip() or len(symbol.strip()) > 32:
        raise ValueError("Le symbole de la position est obligatoire.")
    if not isinstance(currency, str) or len(currency.strip()) != 3 or not currency.strip().isascii() or not currency.strip().isalpha():
        raise ValueError("La devise doit être un code alphabétique ISO à 3 lettres.")
    return PortfolioLine(
        symbol=symbol.strip().upper(),
        quantity=_number(raw.get("quantity"), "La quantité", allow_zero=False),
        average_cost=_number(raw.get("average_cost"), "Le prix de revient"),
        currency=currency.strip().upper(),
    )


def analyze_portfolio(
    positions: Iterable[Mapping[str, Any] | PortfolioLine],
    quotes: Mapping[str, MarketObservation],
) -> PortfolioSummary:
    """Value positions from provided observations; never infer missing quotes."""
    lines = tuple(
        item if isinstance(item, PortfolioLine) else normalize_portfolio_line(item)
        for item in positions
    )
    if not lines:
        raise ValueError("Le portefeuille ne contient aucune position.")
    symbols = [line.symbol for line in lines]
    if len(set(symbols)) != len(symbols):
        raise ValueError("Une seule ligne par symbole est autorisée.")
    currencies = {line.currency for line in lines}
    if len(currencies) != 1:
        raise ValueError("Les positions doivent partager une devise ; aucune conversion automatique n'est appliquée.")

    currency = next(iter(currencies))
    valued = []
    missing = []
    for line in lines:
        quote = quotes.get(line.symbol)
        if quote is None:
            missing.append(line.symbol)
            continue
        if quote.currency != currency:
            raise ValueError(f"La devise de la cotation {line.symbol} ne correspond pas à celle du portefeuille.")
        invested = line.quantity * line.average_cost
        market_value = line.quantity * quote.price
        pnl = market_value - invested
        returned = (pnl / invested * 100) if invested else 0.0
        valued.append((line, quote, invested, market_value, pnl, returned))

    total_invested = sum(line.quantity * line.average_cost for line in lines)
    valued_invested = sum(item[2] for item in valued)
    total_market = sum(item[3] for item in valued)
    total_pnl = total_market - valued_invested
    total_return = (total_pnl / valued_invested * 100) if valued_invested and not missing else (0.0 if not missing else None)

    positions_out = tuple(
        ValuedPosition(
            symbol=line.symbol,
            quantity=line.quantity,
            average_cost=line.average_cost,
            market_price=quote.price,
            currency=currency,
            invested_amount=invested,
            market_value=market,
            unrealized_pnl=pnl,
            unrealized_return_pct=returned,
            portfolio_weight_pct=(market / total_market * 100) if total_market else 0.0,
        )
        for line, quote, invested, market, pnl, returned in valued
    )
    return PortfolioSummary(
        currency=currency,
        invested_amount=total_invested,
        market_value=total_market,
        unrealized_pnl=total_pnl,
        unrealized_return_pct=total_return,
        positions=positions_out,
        missing_quotes=tuple(missing),
    )
