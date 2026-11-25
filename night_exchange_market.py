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



def build_order_book_matches(buy_orders, sell_orders):
    """Build deterministic price-time-priority fills for one share class.

    Each order is a mapping with id, user_id, limit_price, remaining_quantity,
    and created_at (ISO timestamp or another consistently sortable value).
    Returns execution plans only; it never mutates balances or persists trades.
    """
    def normalize(order, side):
        if not isinstance(order, dict):
            raise ValueError("Ordre invalide.")
        order_id = order.get("id")
        user_id = order.get("user_id")
        if not order_id or not user_id:
            raise ValueError("Chaque ordre doit avoir un identifiant et un investisseur.")
        price = _decimal(order.get("limit_price"), "Prix limite")
        try:
            quantity = int(order.get("remaining_quantity"))
        except (TypeError, ValueError, OverflowError):
            raise ValueError("Quantité restante invalide.") from None
        if price <= 0 or quantity < 1:
            raise ValueError("Prix et quantité restante doivent être positifs.")
        created_at = order.get("created_at")
        if created_at is None:
            raise ValueError("Date de création manquante.")
        return {
            "id": str(order_id), "user_id": str(user_id),
            "price": price, "quantity": quantity,
            "created_at": str(created_at), "side": side,
        }

    buys = [normalize(item, "buy") for item in buy_orders]
    sells = [normalize(item, "sell") for item in sell_orders]
    buys.sort(key=lambda item: (-item["price"], item["created_at"], item["id"]))
    sells.sort(key=lambda item: (item["price"], item["created_at"], item["id"]))
    fills = []
    bi = si = 0
    while bi < len(buys) and si < len(sells):
        buy, sell = buys[bi], sells[si]
        if buy["price"] < sell["price"]:
            break
        if buy["user_id"] == sell["user_id"]:
            raise ValueError("L'auto-négociation est interdite.")
        quantity = min(buy["quantity"], sell["quantity"])
        resting_side = "buy" if buy["created_at"] <= sell["created_at"] else "sell"
        execution_price = buy["price"] if resting_side == "buy" else sell["price"]
        fills.append({
            "buy_order_id": buy["id"],
            "sell_order_id": sell["id"],
            "buyer_id": buy["user_id"],
            "seller_id": sell["user_id"],
            "quantity": quantity,
            "execution_price": execution_price.quantize(PRICE_TICK),
            "resting_side": resting_side,
        })
        buy["quantity"] -= quantity
        sell["quantity"] -= quantity
        if buy["quantity"] == 0:
            bi += 1
        if sell["quantity"] == 0:
            si += 1
    return fills
