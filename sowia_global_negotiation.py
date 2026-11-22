"""Human-approved commercial negotiation workflow for SOW IA.

Prepares replies and non-binding proposal drafts. It never sends, signs,
accepts binding terms, or commits funds.
"""
from decimal import Decimal, InvalidOperation
from urllib.parse import urlparse

STAGES = (
    "À qualifier", "Premier échange", "Besoin confirmé", "Proposition envoyée",
    "Négociation", "Accord de principe", "Contrat à valider",
    "Finalisé", "Refusé", "En pause",
)
MAX_TEXT = 4000


def validate_case(partner, country, objective, incoming_message, boundaries=""):
    values = {
        "partner": str(partner or "").strip(),
        "country": str(country or "").strip(),
        "objective": str(objective or "").strip(),
        "incoming_message": str(incoming_message or "").strip(),
        "boundaries": str(boundaries or "").strip(),
    }
    limits = {"partner": 160, "country": 100, "objective": 500,
              "incoming_message": MAX_TEXT, "boundaries": 1200}
    for key, value in values.items():
        if not value and key in {"partner", "objective", "incoming_message"}:
            raise ValueError("Renseignez le partenaire, l'objectif et le dernier message reçu.")
        if len(value) > limits[key]:
            raise ValueError(f"Le champ {key} dépasse la limite de {limits[key]} caractères.")
    return values


def detect_negotiation_signals(message):
    text = str(message or "").casefold()
    groups = {
        "Prix ou budget": ("prix", "tarif", "budget", "coût", "discount", "price", "cost"),
        "Délais": ("délai", "date", "livraison", "timeline", "deadline"),
        "Conditions contractuelles": ("contrat", "clause", "exclusivité", "responsabilité", "contract", "terms"),
        "Paiement": ("paiement", "facture", "acompte", "payment", "invoice"),
        "Démonstration ou preuves": ("démo", "démonstration", "référence", "preuve", "demo", "case study"),
        "Refus ou réserve": ("pas intéressé", "trop cher", "impossible", "not interested", "too expensive"),
    }
    found = [label for label, terms in groups.items() if any(term in text for term in terms)]
    return found or ["Clarification du besoin"]


def build_reply_draft(case, language="Français"):
    case = validate_case(**case)
    signals = detect_negotiation_signals(case["incoming_message"])
    objective = case["objective"]
    boundaries = case["boundaries"] or "Les conditions commerciales restent à définir ensemble."
    if language == "English":
        return (
            f"Subject: Follow-up on our discussion\n\nHello {case['partner']},\n\n"
            f"Thank you for your message and for considering a collaboration with SOW IA. "
            f"Our objective is: {objective}. I noted the following points: {', '.join(signals)}. "
            "To prepare a relevant proposal, could you confirm your expectations, decision process "
            f"and any applicable requirements?\n\nOur current discussion boundaries are: {boundaries} "
            "No commercial term is confirmed at this stage; any offer will be subject to written approval.\n\n"
            "Kind regards,\nSOW IA"
        )
    return (
        f"Objet : Suite à notre échange\n\nBonjour {case['partner']},\n\n"
        "Merci pour votre retour et pour l'intérêt porté à SOW IA. "
        f"Notre objectif est le suivant : {objective}. "
        f"J'ai relevé plusieurs points à traiter : {', '.join(signals)}.\n\n"
        "Afin de préparer une proposition adaptée, pourriez-vous préciser vos attentes, "
        "votre calendrier de décision et les conditions à prendre en compte ?\n\n"
        f"Nos limites et points de vigilance actuels : {boundaries} "
        "Aucune condition commerciale n'est confirmée à ce stade. Toute offre définitive "
        "devra faire l'objet d'une validation écrite préalable.\n\n"
        "Bien cordialement,\nSOW IA"
    )


def build_nonbinding_offer(partner, country, objective, scope, deliverables,
                           currency, price, timeline, payment_terms, validity_days):
    """Build a proposal only from explicit user-entered commercial terms."""
    fields = {
        "partner": (partner, 160), "country": (country, 100),
        "objective": (objective, 500), "scope": (scope, 1200),
        "deliverables": (deliverables, 1200), "timeline": (timeline, 300),
        "payment_terms": (payment_terms, 500),
    }
    clean = {}
    for key, (value, maximum) in fields.items():
        value = str(value or "").strip()
        if not value:
            raise ValueError(f"Le champ {key} est obligatoire.")
        if len(value) > maximum:
            raise ValueError(f"Le champ {key} dépasse {maximum} caractères.")
        clean[key] = value
    currency = str(currency or "").strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("Utilisez un code devise ISO à trois lettres, par exemple EUR.")
    try:
        amount = Decimal(str(price)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        raise ValueError("Montant invalide.") from None
    if not amount.is_finite() or amount < 0:
        raise ValueError("Le montant doit être positif ou nul.")
    if not isinstance(validity_days, int) or not 1 <= validity_days <= 90:
        raise ValueError("La validité doit être comprise entre 1 et 90 jours.")
    return (
        "PROPOSITION COMMERCIALE — PROJET NON CONTRACTUEL\n\n"
        f"Destinataire : {clean['partner']} ({clean['country']})\n"
        f"Objectif : {clean['objective']}\n\n"
        f"Périmètre proposé\n{clean['scope']}\n\n"
        f"Livrables envisagés\n{clean['deliverables']}\n\n"
        f"Calendrier indicatif\n{clean['timeline']}\n\n"
        f"Budget proposé : {amount:.2f} {currency}\n"
        f"Modalités de paiement proposées : {clean['payment_terms']}\n"
        f"Durée de validité souhaitée : {validity_days} jours\n\n"
        "IMPORTANT — BROUILLON À VALIDER : cette proposition est préparatoire et non "
        "contractuelle. Elle ne constitue ni une offre ferme, ni une acceptation, ni un "
        "engagement de SOW IA. Les montants, taxes, délais, obligations, droits, garanties "
        "et clauses doivent être vérifiés et approuvés par une personne habilitée avant tout envoi."
    )


def validate_stage(stage):
    if stage not in STAGES:
        raise ValueError("Étape de négociation inconnue.")
    return stage


def validate_finalization(checklist):
    required = ("identity_verified", "scope_confirmed", "price_approved",
                "legal_review", "authorized_signatory")
    if not isinstance(checklist, dict):
        raise ValueError("Liste de validation invalide.")
    missing = [key for key in required if checklist.get(key) is not True]
    return {"ready_for_human_review": not missing, "missing": missing,
            "can_auto_sign": False, "can_auto_accept": False}


def build_case_memory_entry(case):
    """Create a compact, durable memory note for a negotiation case."""
    if not isinstance(case, dict):
        raise ValueError("Dossier de négociation invalide.")
    partner = str(case.get("partner") or "").strip()
    country = str(case.get("country") or "À préciser").strip()
    objective = str(case.get("objective") or "").strip()
    stage = validate_stage(case.get("stage"))
    if not partner or not objective:
        raise ValueError("Le partenaire et l'objectif sont obligatoires pour archiver le dossier.")
    incoming = " ".join(str(case.get("incoming_message") or "").split())
    draft = " ".join(str(case.get("draft") or "").split())
    signals = case.get("signals") or []
    signal_text = ", ".join(str(item) for item in signals[:8]) or "Aucun signal détecté"
    entry = (
        f"SOW IA — DOSSIER DE NÉGOCIATION\nPartenaire : {partner}\nPays : {country}\n"
        f"Objectif : {objective}\nÉtape : {stage}\nSignaux : {signal_text}\n"
        f"Dernier échange : {incoming}\nRéponse préparée (non envoyée) : {draft}"
    )
    return entry[:1000]
