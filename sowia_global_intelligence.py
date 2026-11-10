"""SOWIA GLOBAL INTELLIGENCE: transparent market/opportunity scoring.

Scores are decision-support estimates entered by the user, not verified market data.
"""
from dataclasses import dataclass, asdict

DIMENSIONS = {
    "market_demand": "Demande du marché",
    "strategic_fit": "Alignement stratégique",
    "accessibility": "Accessibilité du marché",
    "partner_readiness": "Disponibilité de partenaires",
    "regulatory_readiness": "Préparation réglementaire",
    "evidence_quality": "Qualité des preuves",
}
WEIGHTS = {
    "market_demand": 0.25,
    "strategic_fit": 0.20,
    "accessibility": 0.15,
    "partner_readiness": 0.15,
    "regulatory_readiness": 0.15,
    "evidence_quality": 0.10,
}
EVIDENCE_LEVELS = {"hypothesis", "indicative", "documented", "verified"}


def validate_assessment(name, country, sector, scores, evidence_level, source_note=""):
    clean_name = str(name or "").strip()
    clean_country = str(country or "").strip()
    clean_sector = str(sector or "").strip()
    if not clean_name or len(clean_name) > 120:
        raise ValueError("Le nom de l'opportunité doit contenir 1 à 120 caractères.")
    if not clean_country or len(clean_country) > 100:
        raise ValueError("Le pays ou marché doit contenir 1 à 100 caractères.")
    if not clean_sector or len(clean_sector) > 100:
        raise ValueError("Le secteur doit contenir 1 à 100 caractères.")
    if evidence_level not in EVIDENCE_LEVELS:
        raise ValueError("Niveau de preuve invalide.")
    if not isinstance(scores, dict) or set(scores) != set(DIMENSIONS):
        raise ValueError("Les six critères d'évaluation sont obligatoires.")
    clean_scores = {}
    for key, value in scores.items():
        try:
            score = int(value)
        except (TypeError, ValueError):
            raise ValueError("Chaque critère doit être noté de 1 à 5.")
        if score < 1 or score > 5:
            raise ValueError("Chaque critère doit être noté de 1 à 5.")
        clean_scores[key] = score
    note = str(source_note or "").strip()
    if len(note) > 1500:
        raise ValueError("La note de source est limitée à 1 500 caractères.")
    return {
        "name": clean_name, "country": clean_country, "sector": clean_sector,
        "scores": clean_scores, "evidence_level": evidence_level,
        "source_note": note,
    }


def score_assessment(scores):
    if not isinstance(scores, dict) or set(scores) != set(WEIGHTS):
        raise ValueError("Évaluation incomplète.")
    values = {}
    for key, weight in WEIGHTS.items():
        try:
            value = int(scores[key])
        except (TypeError, ValueError):
            raise ValueError("Score invalide.")
        if value < 1 or value > 5:
            raise ValueError("Les scores doivent être compris entre 1 et 5.")
        values[key] = value
    weighted = sum(values[key] * weight for key, weight in WEIGHTS.items())
    return round(weighted * 20, 1)


def classify_score(score):
    score = float(score)
    if score >= 80:
        return "Priorité à étudier"
    if score >= 65:
        return "À approfondir"
    if score >= 50:
        return "À surveiller"
    return "Faible priorité"


def safe_assessment_projection(row):
    if not isinstance(row, dict):
        return {}
    allowed = ("id", "name", "country", "sector", "scores", "weighted_score",
               "evidence_level", "source_note", "created_at", "updated_at")
    return {key: row[key] for key in allowed if key in row}
