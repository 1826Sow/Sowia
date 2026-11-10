"""International expansion framework for SOW IA.

Priority markets are strategic starting points, not a closed country list.
Any country can be entered; local legal, language, tax and payment checks remain
mandatory before commercial launch.
"""
from __future__ import annotations

PRIORITY_MARKETS = {
    "China": {"region": "Asie de l'Est", "focus": "partenariats technologiques, entreprises, localisation"},
    "Singapour": {"region": "Asie du Sud-Est", "focus": "hub régional, finance, technologies, sièges régionaux"},
    "Malaisie": {"region": "Asie du Sud-Est", "focus": "PME, commerce, services numériques"},
    "Taïwan": {"region": "Asie de l'Est", "focus": "technologie, industrie, innovation"},
    "Corée du Sud": {"region": "Asie de l'Est", "focus": "technologie, entreprises, contenus localisés"},
    "Sénégal": {"region": "Afrique de l'Ouest", "focus": "entrepreneuriat, PME, services accessibles"},
    "Émirats arabes unis (Dubaï)": {"region": "Moyen-Orient", "focus": "partenariats internationaux, entreprises, hub régional"},
    "Pays-Bas": {"region": "Europe", "focus": "innovation, PME, commerce international"},
    "Brésil": {"region": "Amérique latine", "focus": "marché lusophone, PME, services numériques"},
    "Bahamas": {"region": "Caraïbes", "focus": "tourisme, services, entreprises et partenariats"},
    "Suisse": {"region": "Europe", "focus": "finance, industrie, services, partenariats à forte valeur"},
}

ANGLOPHONE_MARKETS = (
    "Afrique du Sud", "Australie", "Bahamas", "Barbade", "Botswana", "Canada",
    "États-Unis", "Gambie", "Ghana", "Irlande", "Jamaïque", "Kenya", "Liberia",
    "Malte", "Nigéria", "Nouvelle-Zélande", "Ouganda", "Royaume-Uni", "Rwanda",
    "Sierra Leone", "Singapour", "Tanzanie", "Trinité-et-Tobago", "Zambie", "Zimbabwe",
)

GLOBAL_REGIONS = (
    "Afrique du Nord", "Afrique de l'Ouest", "Afrique centrale", "Afrique de l'Est",
    "Afrique australe", "Asie de l'Est", "Asie du Sud-Est", "Asie du Sud",
    "Asie centrale", "Moyen-Orient", "Europe", "Amérique du Nord",
    "Amérique centrale", "Amérique du Sud", "Caraïbes", "Océanie",
)

INCLUSION_PRINCIPLE = (
    "Inclure les pays à revenu faible ou intermédiaire et les marchés émergents "
    "dans la prospection, sans les écarter sur le seul critère du revenu national."
)


def normalize_market(country: str) -> dict[str, str]:
    name = str(country or "").strip()
    if not name or len(name) > 100:
        raise ValueError("Indiquez un pays ou marché valide (1 à 100 caractères).")
    for market, profile in PRIORITY_MARKETS.items():
        if name.casefold() == market.casefold():
            return {"country": market, **profile, "segment": "Marché prioritaire"}
    if name.casefold() in {item.casefold() for item in ANGLOPHONE_MARKETS}:
        return {
            "country": name, "region": "À préciser",
            "focus": "partenariats et adaptation anglophone",
            "segment": "Marché anglophone",
        }
    return {
        "country": name, "region": "À qualifier",
        "focus": "étude locale, partenaires et adaptation du service",
        "segment": "Ouverture mondiale / marché à qualifier",
    }


def build_market_research_queries(country: str, offer: str) -> list[str]:
    profile = normalize_market(country)
    clean_offer = str(offer or "").strip()
    if not clean_offer or len(clean_offer) > 240:
        raise ValueError("La présentation de SOWIA doit contenir entre 1 et 240 caractères.")
    name = profile["country"]
    return [
        f'"{name}" entreprises PME partenaires solutions IA {clean_offer}',
        f'"{name}" réglementation données personnelles IA services numériques entreprises',
        f'"{name}" moyens de paiement numériques fiscalité création entreprise partenaires',
        f'"{name}" associations professionnelles incubateurs chambres de commerce technologies',
    ]


def score_market(*, demand: float, accessibility: float, partner_readiness: float,
                 affordability: float, risk_control: float) -> float:
    """Score only user-entered assessments; no live market data is inferred."""
    values = {
        "demande": demand, "accessibilité": accessibility,
        "partenaires": partner_readiness, "accessibilité économique": affordability,
        "maîtrise des risques": risk_control,
    }
    normalized = {}
    for label, value in values.items():
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Note invalide : {label}.") from exc
        if not 0 <= numeric <= 5:
            raise ValueError(f"La note {label} doit être comprise entre 0 et 5.")
        normalized[label] = numeric
    return round((
        normalized["demande"] * .25
        + normalized["accessibilité"] * .15
        + normalized["partenaires"] * .20
        + normalized["accessibilité économique"] * .20
        + normalized["maîtrise des risques"] * .20
    ) * 20, 1)
