"""Pure arithmetic helpers for the NIGHT EXCHANGE global simulation engine."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


def _amount(value, label):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{label} invalide.") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"{label} invalide.")
    return result


def reserve_buy_order(quantity, limit_price, fee_rate="0.02"):
    try:
        count = int(quantity)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Quantité invalide.") from None
    price = _amount(limit_price, "Prix limite")
    rate = _amount(fee_rate, "Commission")
    if count < 1 or count > 1_000_000_000 or price <= 0 or rate > Decimal("0.10"):
        raise ValueError("Paramètres de réservation invalides.")
    return (Decimal(count) * price * (Decimal("1") + rate)).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_trade_settlement(quantity, execution_price, fee_rate="0.02",
                               sowia_share="0.60", reserve_share="0.25"):
    try:
        count = int(quantity)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Quantité invalide.") from None
    price = _amount(execution_price, "Cours exécuté")
    rate = _amount(fee_rate, "Commission")
    sowia = _amount(sowia_share, "Part SOW IA")
    reserve = _amount(reserve_share, "Part réserve")
    ecosystem = Decimal("1") - sowia - reserve
    if count < 1 or price <= 0 or rate > Decimal("0.10") or ecosystem < 0:
        raise ValueError("Paramètres de règlement invalides.")
    gross = (Decimal(count) * price).quantize(CENT, rounding=ROUND_HALF_UP)
    fee = (gross * rate).quantize(CENT, rounding=ROUND_HALF_UP)
    sowia_fee = (fee * sowia).quantize(CENT, rounding=ROUND_HALF_UP)
    reserve_fee = (fee * reserve).quantize(CENT, rounding=ROUND_HALF_UP)
    ecosystem_fee = fee - sowia_fee - reserve_fee
    return {
        "gross": gross,
        "buyer_debit": gross + fee,
        "seller_credit": gross,
        "fee": fee,
        "sowia_revenue": sowia_fee,
        "market_reserve": reserve_fee,
        "ecosystem_fund": ecosystem_fee,
    }
