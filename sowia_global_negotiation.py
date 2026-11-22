"""Human-approved commercial negotiation workflow for SOW IA.

This module prepares replies and tracks negotiation stages. It never sends,
signs, accepts binding terms, or commits funds.
"""
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
        if not value:
            if key in {"partner", "objective", "incoming_message"}:
                raise ValueError("Renseignez le partenaire, l'objectif et le dernier message reçu.")
            continue
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
    """Prepare a non-binding reply; all commercial terms remain subject to approval."""
    case = validate_case(**case)
    signals = detect_negotiation_signals(case["incoming_message"])
    objective = case["objective"]
    boundaries = case["boundaries"] or "Les conditions commerciales restent à définir ensemble."
    if language == "English":
        return (
            f"Subject: Follow-up on our discussion\n\nHello {case['partner']},\n\n"
            f"Thank you for your message and for considering a collaboration with SOW IA. "
            f"Our objective is: {objective}. I noted the following points: {', '.join(signals)}. "
            f"To prepare a relevant proposal, could you confirm your expectations, decision process "
            f"and any applicable requirements?\n\n"
            f"Our current discussion boundaries are: {boundaries} "
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
