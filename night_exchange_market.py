"""Pure calculation helpers for the NIGHT EXCHANGE virtual stock-market pilot.

All amounts are non-redeemable virtual credits (NXC), never real money.
Persistence and order execution must happen in atomic, server-side operations.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")
PRICE_TICK = Decimal("0.0001")
MAX_RATE = Decimal("0.10")


def _decimal(value, field):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} invalide.") from None
    if not result.is_finite():
        raise ValueError(f"{field} invalide.")
    return result


def validate_share_issue(total_shares, shares_float, initial_price):
    """Validate an application share issue without creating a real-world claim."""
    try:
        total = int(total_shares)
        floating = int(shares_float)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Nombre d'actions invalide.") from None
    price = _decimal(initial_price, "Prix initial")
    if total < 1 or total > 1_000_000_000_000:
        raise ValueError("Le nombre total d'actions doit être compris entre 1 et 10^12.")
    if floating < 0 or floating > total:
        raise ValueError("Le flottant doit être compris entre zéro et le total d'actions.")
    if price <= 0 or price > Decimal("1000000"):
        raise ValueError("Le prix initial doit être positif et inférieur ou égal à 1 000 000 NXC.")
    return {
        "total_shares": total,
        "shares_float": floating,
        "initial_price": price.quantize(PRICE_TICK, rounding=ROUND_HALF_UP),
        "initial_market_cap": (price * total).quantize(CENT, rounding=ROUND_HALF_UP),
    }


def calculate_fee_split(gross_value, fee_rate="0.02",
                        sowia_share="0.60", reserve_share="0.25",
                        ecosystem_share="0.15"):
    """Allocate the transaction fee; default split is 60/25/15.

    SOW IA receives 60% of the fee, 25% goes to the market reserve and
    15% to the ecosystem fund. The fee rate and allocations are explicit.
    """
    gross = _decimal(gross_value, "Montant brut")
    rate = _decimal(fee_rate, "Taux de commission")
    sowia = _decimal(sowia_share, "Part SOW IA")
    reserve = _decimal(reserve_share, "Part réserve")
    ecosystem = _decimal(ecosystem_share, "Part écosystème")
    if gross <= 0:
        raise ValueError("Le montant brut doit être positif.")
    if rate < 0 or rate > MAX_RATE:
        raise ValueError("Le taux de commission doit être compris entre 0 et 10 %.")
    if min(sowia, reserve, ecosystem) < 0 or (sowia + reserve + ecosystem) != Decimal("1"):
        raise ValueError("La répartition doit être positive et totaliser exactement 100 %.")
    fee = (gross * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    sowia_amount = (fee * sowia).quantize(CENT, rounding=ROUND_HALF_UP)
    reserve_amount = (fee * reserve).quantize(CENT, rounding=ROUND_HALF_UP)
    ecosystem_amount = fee - sowia_amount - reserve_amount
    return {
        "gross_value": gross.quantize(CENT, rounding=ROUND_HALF_UP),
        "fee_rate": rate,
        "total_fee": fee,
        "sowia_revenue": sowia_amount,
        "market_reserve": reserve_amount,
        "ecosystem_fund": ecosystem_amount,
        "seller_net": (gross - fee).quantize(CENT, rounding=ROUND_HALF_UP),
    }


def match_limit_orders(buy_limit, sell_limit, buyer_id, seller_id, resting_side="sell"):
    """Return a price-time-neutral match decision for two compatible limit orders.

    Execution price follows the resting (older) order. The caller supplies
    resting_side after comparing creation timestamps. This helper validates
    compatibility and prevents self-trading; it never persists or settles.
    """
    buy = _decimal(buy_limit, "Limite d'achat")
    sell = _decimal(sell_limit, "Limite de vente")
    if buy <= 0 or sell <= 0:
        raise ValueError("Les limites de prix doivent être positives.")
    if resting_side not in {"buy", "sell"}:
        raise ValueError("Côté de l'ordre au carnet invalide.")
    if not buyer_id or not seller_id:
        raise ValueError("Les deux investisseurs doivent être identifiés.")
    if str(buyer_id) == str(seller_id):
        raise ValueError("L'auto-négociation est interdite.")
    if buy < sell:
        return {"match": False, "reason": "price_mismatch", "execution_price": None}
    resting_price = buy if resting_side == "buy" else sell
    return {"match": True, "reason": None, "execution_price": resting_price.quantize(PRICE_TICK)}


def calculate_market_cap(last_price, total_shares):
    price = _decimal(last_price, "Dernier cours")
    try:
        shares = int(total_shares)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Nombre d'actions invalide.") from None
    if price <= 0 or shares < 1:
        raise ValueError("Cours et nombre d'actions doivent être positifs.")
    return (price * shares).quantize(CENT, rounding=ROUND_HALF_UP)
