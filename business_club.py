"""Validation and explainable matching for the opt-in SOW IA Business Club."""
from __future__ import annotations
from dataclasses import dataclass
import re
from typing import Any, Mapping
from urllib.parse import urlparse

def _clean_text(value: Any, field: str, limit: int, required: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} doit être un texte.")
    result = value.strip()
    if required and not result:
        raise ValueError(f"{field} est obligatoire.")
    if len(result) > limit:
        raise ValueError(f"{field} dépasse {limit} caractères.")
    return result

def _terms(value: Any, field: str) -> list[str]:
    if isinstance(value, str):
        items = re.split(r"[,;\n]", value)
    elif isinstance(value, (list, tuple)):
        items = value
    else:
        raise ValueError(f"{field} doit être une liste de mots-clés.")
    cleaned = list(dict.fromkeys(str(item).strip() for item in items if str(item).strip()))
    if len(cleaned) > 20 or any(len(item) > 80 for item in cleaned):
        raise ValueError(f"{field} accepte 20 éléments de 80 caractères maximum.")
    return cleaned

def validate_profile(raw: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError("Profil d'entreprise invalide.")
    profile = {
        "company_name": _clean_text(raw.get("company_name"), "Nom de l'entreprise", 180, True),
        "country": _clean_text(raw.get("country"), "Pays", 100, True),
        "sector": _clean_text(raw.get("sector"), "Secteur", 100, True),
        "description": _clean_text(raw.get("description", ""), "Présentation", 1200),
        "offers": _terms(raw.get("offers", []), "Offres"),
        "needs": _terms(raw.get("needs", []), "Besoins"),
        "objectives": _terms(raw.get("objectives", []), "Objectifs"),
        "website": _clean_text(raw.get("website", ""), "Site web", 500),
        "is_published": raw.get("is_published", False),
    }
    if not any(profile[key] for key in ("offers", "needs", "objectives")):
        raise ValueError("Indiquez au moins une offre, un besoin ou un objectif.")
    if not isinstance(profile["is_published"], bool):
        raise ValueError("Le choix de publication doit être activé ou désactivé.")
    if profile["website"]:
        parsed = urlparse(profile["website"])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Le site web doit être une URL HTTP ou HTTPS valide.")
    return profile

@dataclass(frozen=True)
class ClubMatch:
    score: int
    evidence: tuple[str, ...]
    recommendation: str

def match_profile(profile: Mapping[str, Any], candidate: Mapping[str, Any]) -> ClubMatch:
    """Compare declared offers, needs and objectives; this is not a trust score."""
    left, right = validate_profile(profile), validate_profile(candidate)
    left_offers = {item.casefold() for item in left["offers"]}
    right_offers = {item.casefold() for item in right["offers"]}
    left_needs = {item.casefold() for item in left["needs"]}
    right_needs = {item.casefold() for item in right["needs"]}
    left_goals = {item.casefold() for item in left["objectives"]}
    right_goals = {item.casefold() for item in right["objectives"]}
    offer_need = (left_offers & right_needs) | (right_offers & left_needs)
    shared_goals = left_goals & right_goals
    score = min(100, len(offer_need) * 25 + len(shared_goals) * 15)
    evidence = []
    if offer_need:
        evidence.append("Complémentarités offres/besoins : " + ", ".join(sorted(offer_need)))
    if shared_goals:
        evidence.append("Objectifs communs : " + ", ".join(sorted(shared_goals)))
    if left["country"].casefold() != right["country"].casefold():
        evidence.append("Présence dans deux pays différents : potentiel d'ouverture internationale")
    if not evidence:
        evidence.append("Aucune complémentarité déclarée détectée : échange exploratoire uniquement")
    recommendation = "Proposer une rencontre exploratoire" if score >= 25 else "Examiner le profil avant toute mise en relation"
    return ClubMatch(score, tuple(evidence), recommendation)

def validate_request(message: Any) -> str:
    return _clean_text(message, "Message de présentation", 1200, True)
