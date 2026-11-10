"""Timezone-aware SOWIA Night Exchange rules; no payment or scheduler integration."""
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Iterable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

class NightExchangeError(ValueError):
    pass

def _money(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise NightExchangeError("Montant invalide.") from None
    if not amount.is_finite() or amount < 0:
        raise NightExchangeError("Montant positif ou nul attendu.")
    return amount

def is_local_night(now: datetime, timezone_name: str,
                   start: time = time(20, 0), end: time = time(6, 0)) -> bool:
    if now.tzinfo is None:
        raise NightExchangeError("La date doit inclure un fuseau horaire.")
    try:
        local = now.astimezone(ZoneInfo(timezone_name))
    except ZoneInfoNotFoundError:
        raise NightExchangeError("Fuseau horaire IANA inconnu.") from None
    current = local.timetz().replace(tzinfo=None)
    if start == end:
        return True
    return (start <= current < end) if start < end else (current >= start or current < end)

@dataclass(frozen=True)
class AppListing:
    app_id: str
    name: str
    country: str
    timezone_name: str
    categories: tuple[str, ...]
    services_offered: tuple[str, ...] = ()
    services_wanted: tuple[str, ...] = ()
    verified: bool = False
    approved_for_listing: bool = False

@dataclass(frozen=True)
class Match:
    app_id: str
    score: int
    shared_categories: tuple[str, ...]
    reciprocal_exchange: bool

def match_apps(source: AppListing, candidates: Iterable[AppListing]) -> list[Match]:
    matches = []
    for candidate in candidates:
        if candidate.app_id == source.app_id or not candidate.approved_for_listing:
            continue
        shared = tuple(sorted(set(source.categories) & set(candidate.categories)))
        offers_source = bool(set(source.services_wanted) & set(candidate.services_offered))
        wants_source = bool(set(candidate.services_wanted) & set(source.services_offered))
        reciprocal = offers_source and wants_source
        score = min(100, len(shared) * 15 + int(offers_source) * 25
                    + int(wants_source) * 25 + int(candidate.verified) * 10)
        if score:
            matches.append(Match(candidate.app_id, score, shared, reciprocal))
    return sorted(matches, key=lambda item: (-item.score, item.app_id))


def _split_terms(value):
    """Normalize comma/semicolon/newline-separated service descriptions."""
    if isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = str(value or "").replace(";", ",").replace("\n", ",").split(",")
    return tuple(sorted({" ".join(str(item).casefold().split()) for item in raw if str(item).strip()}))


def match_listing_records(source_record: dict, candidate_records: Iterable[dict]) -> list[Match]:
    """Rank a member listing against approved registry records only."""
    def to_listing(record, candidate=False):
        status = record.get("status")
        approved = status == "approved" if candidate else status in {"pending", "approved"}
        return AppListing(
            app_id=str(record.get("id") or record.get("app_id") or ""),
            name=str(record.get("app_name") or record.get("name") or ""),
            country=str(record.get("country") or ""),
            timezone_name=str(record.get("timezone") or record.get("timezone_name") or "UTC"),
            categories=_split_terms(record.get("categories") or ()),
            services_offered=_split_terms(record.get("services_offered") or ()),
            services_wanted=_split_terms(record.get("services_wanted") or ()),
            verified=bool(record.get("verified", False)),
            approved_for_listing=approved,
        )
    source = to_listing(source_record)
    candidates = [to_listing(row, candidate=True) for row in candidate_records]
    return match_apps(source, candidates)



@dataclass
class BudgetCap:
    currency: str
    daily_limit: Decimal
    weekly_limit: Decimal
    monthly_limit: Decimal
    spent_today: Decimal = Decimal("0.00")
    spent_week: Decimal = Decimal("0.00")
    spent_month: Decimal = Decimal("0.00")
    enabled: bool = True

    @classmethod
    def create(cls, currency, daily, weekly, monthly):
        currency = currency.upper().strip()
        if len(currency) != 3 or not currency.isalpha():
            raise NightExchangeError("Code devise ISO 4217 attendu.")
        d, w, m = _money(daily), _money(weekly), _money(monthly)
        if d > w or w > m:
            raise NightExchangeError("Respecter quotidien ≤ hebdomadaire ≤ mensuel.")
        return cls(currency, d, w, m)

    def authorize(self, amount) -> bool:
        if not self.enabled:
            return False
        value = _money(amount)
        return (self.spent_today + value <= self.daily_limit
                and self.spent_week + value <= self.weekly_limit
                and self.spent_month + value <= self.monthly_limit)

    def record_confirmed_spend(self, amount):
        value = _money(amount)
        if not self.authorize(value):
            raise NightExchangeError("Dépense refusée : plafond atteint ou budget désactivé.")
        self.spent_today += value
        self.spent_week += value
        self.spent_month += value

    def reset_period(self, period):
        fields = {"day": "spent_today", "week": "spent_week", "month": "spent_month"}
        if period not in fields:
            raise NightExchangeError("Période inconnue.")
        setattr(self, fields[period], Decimal("0.00"))

def select_budgeted_offers(offers: Iterable[dict], available_budget):
    remaining = _money(available_budget)
    valid = []
    for offer in offers:
        price = _money(offer.get("price", 0))
        score = int(offer.get("relevance_score", 0))
        if not 0 <= score <= 100:
            raise NightExchangeError("Score attendu entre 0 et 100.")
        valid.append((score, str(offer.get("offer_id", "")), price, offer))
    selected = []
    for _, _, price, offer in sorted(valid, key=lambda row: (-row[0], row[1])):
        if price <= remaining:
            selected.append(offer)
            remaining -= price
    return selected


def _parse_clock(value, default):
    if isinstance(value, time):
        return value.replace(tzinfo=None)
    raw = str(value or default).strip()
    try:
        parts = raw.split(":")
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError, TypeError):
        raise NightExchangeError("Heure locale invalide (format HH:MM attendu).") from None


def global_session_status(record: dict, now: datetime) -> dict:
    """Return a timezone-safe local session status and the next opening."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise NightExchangeError("La date doit inclure un fuseau horaire.")
    zone_name = str(record.get("timezone") or record.get("timezone_name") or "UTC")
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        raise NightExchangeError("Fuseau horaire IANA inconnu.") from None
    start = _parse_clock(record.get("night_start"), "20:00")
    end = _parse_clock(record.get("night_end"), "06:00")
    local_now = now.astimezone(zone)
    active = is_local_night(now, zone_name, start, end)
    next_open = None
    # Search upcoming local calendar dates; round-trip validation skips
    # nonexistent wall-clock times during spring DST transitions.
    for offset in range(0, 5):
        day = local_now.date()
        from datetime import timedelta
        candidate_day = day + timedelta(days=offset)
        candidate = datetime.combine(candidate_day, start).replace(tzinfo=zone, fold=0)
        round_trip = candidate.astimezone(timezone.utc).astimezone(zone)
        if round_trip.replace(tzinfo=None) != candidate.replace(tzinfo=None):
            continue
        if candidate.astimezone(timezone.utc) > now.astimezone(timezone.utc):
            next_open = candidate
            break
    if active:
        next_open = None
    return {
        "is_open": active,
        "timezone": zone_name,
        "local_now": local_now,
        "next_open_local": next_open,
        "next_open_utc": next_open.astimezone(timezone.utc) if next_open else None,
        "night_start": start.strftime("%H:%M"),
        "night_end": end.strftime("%H:%M"),
    }


def build_smart_opportunities(source_record: dict, candidate_records: Iterable[dict],
                              limit: int = 15) -> list[dict]:
    """Explain compatibility signals; scores are suggestions, not forecasts."""
    if not isinstance(limit, int) or limit < 1 or limit > 100:
        raise NightExchangeError("La limite doit être comprise entre 1 et 100.")
    rows = list(candidate_records)
    matches = match_listing_records(source_record, rows)
    by_id = {str(row.get("id") or row.get("app_id") or ""): row for row in rows}
    opportunities = []
    for match in matches:
        partner = by_id.get(match.app_id, {})
        source_offers = set(_split_terms(source_record.get("services_offered")))
        source_wants = set(_split_terms(source_record.get("services_wanted")))
        partner_offers = set(_split_terms(partner.get("services_offered")))
        partner_wants = set(_split_terms(partner.get("services_wanted")))
        offered_to_source = sorted(source_wants & partner_offers)
        wanted_from_source = sorted(source_offers & partner_wants)
        opportunities.append({
            "app_id": match.app_id,
            "app_name": partner.get("app_name") or partner.get("name") or "Application partenaire",
            "country": partner.get("country") or "",
            "score": match.score,
            "shared_categories": list(match.shared_categories),
            "reciprocal_exchange": match.reciprocal_exchange,
            "signals": {
                "shared_categories": list(match.shared_categories),
                "partner_services_matching_my_needs": offered_to_source,
                "my_services_matching_partner_needs": wanted_from_source,
                "partner_verified": bool(partner.get("verified", False)),
            },
            "notice": "Compatibilité indicative, sans garantie de résultat commercial.",
        })
    return opportunities[:limit]


def build_morning_report(events: Iterable[dict]) -> dict:
    """Summarize explicit event records only; never infer activity or spending."""
    rows = list(events or [])
    allowed = {"match_viewed", "meeting_confirmed", "offer_accepted",
               "integration_approved", "payment_confirmed"}
    counts = {name: 0 for name in sorted(allowed)}
    confirmed_spend = Decimal("0.00")
    currencies = set()
    spend_by_currency = {}
    for event in rows:
        payload = event.get("event_payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        event = {**payload, **event}
        event_type = str(event.get("event_type") or "")
        if event_type not in allowed:
            continue
        if event_type == "payment_confirmed":
            if event.get("payment_status") != "confirmed":
                continue
            amount = _money(event.get("amount", 0))
            currency = str(event.get("currency") or "").upper()
            if len(currency) != 3 or not currency.isalpha():
                raise NightExchangeError("Devise invalide dans un événement de paiement.")
            confirmed_spend += amount
            spend_by_currency[currency] = spend_by_currency.get(currency, Decimal("0.00")) + amount
            currencies.add(currency)
        counts[event_type] += 1
    return {
        "events_received": len(rows),
        "recognized_events": sum(counts.values()),
        "counts": counts,
        "confirmed_spend": confirmed_spend,
        "spend_currencies": sorted(currencies),
        "confirmed_spend_by_currency": spend_by_currency,
        "has_recorded_activity": bool(sum(counts.values())),
        "scope": "Synthèse des événements fournis uniquement; aucun événement manquant n'est estimé.",
    }
