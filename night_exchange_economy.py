"""SOW IA NIGHT EXCHANGE: application-to-application economy primitives.

This first engine is deliberately simulation-only. It models applications as
actors and service orders as offers/needs; it never calls external APIs,
moves money, executes code, or grants permissions.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable


class EconomyError(ValueError):
    """Invalid actor, order, or proposed exchange."""


def _clean_text(value, label, limit=160):
    text = " ".join(str(value or "").split())
    if not text or len(text) > limit:
        raise EconomyError(f"{label} invalide.")
    return text


def _amount(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise EconomyError("Montant invalide.") from None
    if not amount.is_finite() or amount < 0:
        raise EconomyError("Montant positif ou nul attendu.")
    return amount


@dataclass(frozen=True)
class ApplicationActor:
    """A software application acting within its owner's declared mandate."""
    app_id: str
    name: str
    owner_id: str
    capabilities: tuple[str, ...]
    services_offered: tuple[str, ...]
    services_wanted: tuple[str, ...]
    approved: bool = False
    enabled: bool = True

    def __post_init__(self):
        object.__setattr__(self, "app_id", _clean_text(self.app_id, "Identifiant application", 128))
        object.__setattr__(self, "name", _clean_text(self.name, "Nom application"))
        object.__setattr__(self, "owner_id", _clean_text(self.owner_id, "Propriétaire", 128))
        for field in ("capabilities", "services_offered", "services_wanted"):
            values = tuple(sorted({_clean_text(x, field, 120).casefold() for x in getattr(self, field)}))
            object.__setattr__(self, field, values)


@dataclass(frozen=True)
class ServiceOrder:
    """A service offer or request posted by an application, not a human."""
    order_id: str
    app_id: str
    side: str
    service: str
    quantity: Decimal
    unit_price: Decimal
    currency: str
    status: str = "open"

    def __post_init__(self):
        object.__setattr__(self, "order_id", _clean_text(self.order_id, "Ordre", 128))
        object.__setattr__(self, "app_id", _clean_text(self.app_id, "Application", 128))
        if self.side not in {"offer", "request"}:
            raise EconomyError("Un ordre doit être une offre ou une demande.")
        object.__setattr__(self, "service", _clean_text(self.service, "Service", 120).casefold())
        quantity = _amount(self.quantity)
        if quantity <= 0:
            raise EconomyError("La quantité doit être supérieure à zéro.")
        object.__setattr__(self, "quantity", quantity)
        object.__setattr__(self, "unit_price", _amount(self.unit_price))
        currency = str(self.currency or "").upper().strip()
        if len(currency) != 3 or not currency.isalpha():
            raise EconomyError("Code devise ISO à trois lettres attendu.")
        object.__setattr__(self, "currency", currency)
        if self.status not in {"open", "matched", "cancelled"}:
            raise EconomyError("Statut d'ordre invalide.")


@dataclass(frozen=True)
class ProposedExchange:
    offer_order_id: str
    request_order_id: str
    provider_app_id: str
    client_app_id: str
    service: str
    quantity: Decimal
    unit_price: Decimal
    currency: str
    total: Decimal
    state: str = "awaiting_owner_approval"
    simulation: bool = True


def discover_matches(actors: Iterable[ApplicationActor],
                     orders: Iterable[ServiceOrder]) -> list[dict]:
    """Match approved, enabled application requests with compatible offers."""
    actor_by_id = {actor.app_id: actor for actor in actors
                   if actor.approved and actor.enabled}
    offers = [o for o in orders if o.side == "offer" and o.status == "open"
              and o.app_id in actor_by_id]
    requests = [o for o in orders if o.side == "request" and o.status == "open"
                and o.app_id in actor_by_id]
    matches = []
    for request in requests:
        for offer in offers:
            if request.app_id == offer.app_id or request.service != offer.service:
                continue
            if request.currency != offer.currency:
                continue
            if not (request.service in actor_by_id[request.app_id].services_wanted
                    and request.service in actor_by_id[offer.app_id].services_offered):
                continue
            if offer.unit_price > request.unit_price:
                continue
            matches.append({
                "offer_order_id": offer.order_id,
                "request_order_id": request.order_id,
                "provider_app_id": offer.app_id,
                "client_app_id": request.app_id,
                "provider_name": actor_by_id[offer.app_id].name,
                "client_name": actor_by_id[request.app_id].name,
                "service": offer.service,
                "quantity": min(offer.quantity, request.quantity),
                "unit_price": offer.unit_price,
                "currency": offer.currency,
                "total": min(offer.quantity, request.quantity) * offer.unit_price,
            })
    return sorted(matches, key=lambda m: (
        m["service"], m["unit_price"], m["provider_app_id"], m["request_order_id"]
    ))


def propose_exchange(match: dict, *, owner_approval_required: bool = True) -> ProposedExchange:
    """Create a proposal only; it cannot accept, settle, or execute the trade."""
    required = {"offer_order_id", "request_order_id", "provider_app_id",
                "client_app_id", "service", "quantity", "unit_price",
                "currency", "total"}
    if not isinstance(match, dict) or not required.issubset(match):
        raise EconomyError("Correspondance d'ordres incomplète.")
    quantity = _amount(match["quantity"])
    unit_price = _amount(match["unit_price"])
    total = _amount(match["total"])
    if quantity <= 0 or total != quantity * unit_price:
        raise EconomyError("Total de proposition incohérent.")
    return ProposedExchange(
        offer_order_id=_clean_text(match["offer_order_id"], "Ordre offre", 128),
        request_order_id=_clean_text(match["request_order_id"], "Ordre demande", 128),
        provider_app_id=_clean_text(match["provider_app_id"], "Application fournisseur", 128),
        client_app_id=_clean_text(match["client_app_id"], "Application cliente", 128),
        service=_clean_text(match["service"], "Service", 120).casefold(),
        quantity=quantity, unit_price=unit_price,
        currency=str(match["currency"]).upper(), total=total,
        state="awaiting_owner_approval" if owner_approval_required else "proposal_only",
        simulation=True,
    )


def discover_service_partners(source_app_id: str, service: str,
                              approved_app_records: Iterable[dict]) -> list[dict]:
    """Find approved apps offering one exact service wanted by a source app.

    This is a read-only discovery preview. It does not create orders, contact
    partners, authorize integrations, or initiate payments.
    """
    source_id = _clean_text(source_app_id, "Application initiatrice", 128)
    requested_service = _clean_text(service, "Service recherché", 120).casefold()
    partners = []
    seen = set()
    for record in approved_app_records:
        if not isinstance(record, dict):
            continue
        app_id = str(record.get("id") or "").strip()
        if not app_id or app_id == source_id or app_id in seen:
            continue
        if record.get("status", "approved") != "approved":
            continue
        offered = {
            " ".join(part.casefold().split())
            for part in str(record.get("services_offered") or "").replace(";", ",").replace("\\n", ",").split(",")
            if part.strip()
        }
        if requested_service not in offered:
            continue
        seen.add(app_id)
        partners.append({
            "app_id": app_id,
            "app_name": str(record.get("app_name") or "Application sans nom"),
            "country": str(record.get("country") or ""),
            "service": requested_service,
            "match_type": "service_exact",
            "simulation": True,
        })
    return sorted(partners, key=lambda item: (item["app_name"].casefold(), item["app_id"]))
