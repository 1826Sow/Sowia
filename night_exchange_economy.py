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



# Shared, versioned skill vocabulary. Unknown labels remain custom and never
# receive an inferred category or trust level.
SKILL_CATALOG_VERSION = "1.0.0"
_SKILL_DEFINITIONS = (
    ("ai.text_generation", "IA et automatisation", "ai_automation", "standard",
     ("rédaction assistée", "ai writing", "text generation")),
    ("ai.translation", "Traduction", "translation_localization", "standard",
     ("translation", "localisation", "localization")),
    ("software.api_integration", "Intégration API", "software_development", "elevated",
     ("api integration", "integration api", "connecteurs api")),
    ("software.testing", "Tests logiciels", "software_development", "standard",
     ("software testing", "tests automatisés", "automated testing")),
    ("data.analysis", "Analyse de données", "data_analytics", "elevated",
     ("data analysis", "analyse de données", "data analytics")),
    ("data.visualization", "Visualisation de données", "data_analytics", "standard",
     ("data visualization", "visualisation de données", "dashboards")),
    ("marketing.campaigns", "Campagnes marketing", "marketing_commerce", "elevated",
     ("marketing campaigns", "campagnes publicitaires", "campaign management")),
    ("creative.design", "Design graphique", "creative_production", "standard",
     ("graphic design", "design graphique", "visual design")),
    ("creative.video", "Production vidéo", "creative_production", "standard",
     ("video production", "montage vidéo", "video editing")),
    ("business.documents", "Traitement de documents", "business_operations", "elevated",
     ("document processing", "traitement documentaire", "document management")),
    ("business.reporting", "Rapports et tableaux de bord", "business_operations", "standard",
     ("business reporting", "reporting", "rapports d'activité")),
    ("research.web", "Recherche documentaire", "research_intelligence", "standard",
     ("web research", "recherche web", "recherche documentaire")),
    ("support.customer", "Assistance client", "customer_support", "elevated",
     ("customer support", "service client", "customer service")),
)
_RESTRICTED_SERVICE_LABELS = frozenset({
    "payment processing", "traitement des paiements", "money transfer",
    "transfert d'argent", "custody", "conservation de fonds", "lending",
    "credit issuance", "octroi de crédit", "investment advice",
    "conseil en investissement", "securities trading", "trading de titres",
    "gambling", "jeux d'argent",
})


def _normalize_skill_label(value):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).casefold()


def list_skill_catalog():
    """Return a detached, read-only-friendly view of the shared skill vocabulary."""
    return [
        {
            "skill_id": skill_id,
            "label_fr": label,
            "category_id": category,
            "risk_level": risk,
            "catalog_version": SKILL_CATALOG_VERSION,
            "aliases": list(aliases),
            "human_approval_required": True,
        }
        for skill_id, label, category, risk, aliases in _SKILL_DEFINITIONS
    ]


def resolve_service_skill(value):
    """Resolve a declared label to a known skill; never guess unknown labels."""
    normalized = _normalize_skill_label(value)
    if not normalized or normalized in _RESTRICTED_SERVICE_LABELS:
        return None
    for skill_id, label, category, risk, aliases in _SKILL_DEFINITIONS:
        accepted = {_normalize_skill_label(label), _normalize_skill_label(skill_id)}
        accepted.update(_normalize_skill_label(alias) for alias in aliases)
        if normalized in accepted:
            return {
                "skill_id": skill_id,
                "label_fr": label,
                "category_id": category,
                "risk_level": risk,
                "catalog_version": SKILL_CATALOG_VERSION,
                "human_approval_required": True,
            }
    return None


def _services_compatible(requested, offered):
    requested_skill = resolve_service_skill(requested)
    offered_skill = resolve_service_skill(offered)
    if requested_skill and offered_skill:
        return requested_skill["skill_id"] == offered_skill["skill_id"], "canonical_skill"
    return _normalize_skill_label(requested) == _normalize_skill_label(offered), "exact_custom"


def _service_values(value):
    """Normalize service declarations supplied as text or a list of strings."""
    if isinstance(value, str):
        raw_values = value.replace("\\n", ",").replace(";", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = list(value)
    else:
        return set()
    normalized = set()
    for item in raw_values:
        if not isinstance(item, str):
            continue
        service = " ".join(item.split()).casefold()
        if service and len(service) <= 120:
            normalized.add(service)
    return normalized


def discover_service_partners(source_app_id: str, service: str,
                              approved_app_records: Iterable[dict]) -> list[dict]:
    """Find approved, enabled apps offering one exact service.

    Fail closed: a record must explicitly have status='approved'. This is a
    read-only directory query; it does not contact partners or execute work.
    """
    source_id = _clean_text(source_app_id, "Application initiatrice", 128)
    requested_service = _clean_text(service, "Service recherché", 120).casefold()
    partners = []
    seen = set()
    for record in approved_app_records:
        if not isinstance(record, dict):
            continue
        app_id = str(record.get("id") or "").strip()
        if not app_id or len(app_id) > 128 or app_id == source_id or app_id in seen:
            continue
        # Never treat missing or unknown moderation state as approval.
        if record.get("status") != "approved" or record.get("enabled", True) is not True:
            continue
        offered = _service_values(record.get("services_offered"))
        compatible_services = [
            (candidate, *_services_compatible(requested_service, candidate))
            for candidate in offered
        ]
        compatible_services = [
            item for item in compatible_services if item[1]
        ]
        if not compatible_services:
            continue
        matched_service, _, match_type = sorted(
            compatible_services, key=lambda item: (item[2] != "canonical_skill", item[0])
        )[0]
        resolved_skill = resolve_service_skill(requested_service)
        app_name = record.get("app_name")
        if not isinstance(app_name, str) or not app_name.strip():
            app_name = "Application sans nom"
        country = record.get("country")
        if not isinstance(country, str):
            country = ""
        categories = record.get("categories")
        if not isinstance(categories, (list, tuple)):
            categories = []
        safe_categories = [
            " ".join(str(item).split())[:80]
            for item in categories
            if isinstance(item, str) and item.strip()
        ][:12]
        seen.add(app_id)
        partners.append({
            "app_id": app_id,
            "app_name": " ".join(app_name.split())[:160],
            "country": " ".join(country.split())[:100],
            "categories": safe_categories,
            "service": requested_service,
            "matched_service": matched_service,
            "match_type": match_type,
            "skill": resolved_skill,
            "match_reasons": [
                "Correspondance par compétence normalisée."
                if match_type == "canonical_skill"
                else "Correspondance exacte sur un service personnalisé."
            ],
            "listing_status": "approved",
            "verification_state": (
                "verified" if record.get("verification_status") == "verified"
                else "not_independently_verified"
            ),
            "simulation": True,
        })
    return sorted(partners, key=lambda item: (item["app_name"].casefold(), item["app_id"]))
