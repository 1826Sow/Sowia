"""Explainable matching of two or more companies for potential cooperation.

This module ranks opportunities from information explicitly supplied or verified
by the user. It does not infer trustworthiness, contact companies or make offers.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

TOKEN_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9][a-zA-ZÀ-ÿ0-9+.#-]{1,}")


@dataclass(frozen=True)
class Company:
    name: str
    country: str
    sector: str
    offers: tuple[str, ...]
    needs: tuple[str, ...]
    objectives: tuple[str, ...]
    website: str | None


@dataclass(frozen=True)
class CollaborationMatch:
    companies: tuple[Company, ...]
    score: float
    evidence: tuple[str, ...]
    suggested_model: str
    next_steps: tuple[str, ...]


def _terms(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, str):
        values = [part.strip() for part in re.split(r"[,;\n]", value) if part.strip()]
    elif isinstance(value, (list, tuple)):
        values = [str(part).strip() for part in value if str(part).strip()]
    else:
        raise ValueError(f"{field} doit contenir une liste de mots-clés.")
    if len(values) > 20 or any(len(part) > 80 for part in values):
        raise ValueError(f"{field} est trop long (20 éléments de 80 caractères maximum).")
    return tuple(dict.fromkeys(values))


def normalize_company(raw: Mapping[str, Any]) -> Company:
    if not isinstance(raw, Mapping):
        raise ValueError("Chaque entreprise doit être un objet.")
    def required(key: str, limit: int) -> str:
        value = raw.get(key)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
            raise ValueError(f"{key} est obligatoire (maximum {limit} caractères).")
        return value.strip()
    website = str(raw.get("website") or "").strip()
    if website:
        parsed = urlparse(website)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Le site web doit être une URL HTTP ou HTTPS valide.")
    offers = _terms(raw.get("offers", []), "Les offres")
    needs = _terms(raw.get("needs", []), "Les besoins")
    objectives = _terms(raw.get("objectives", []), "Les objectifs")
    if not offers and not needs:
        raise ValueError("Renseignez au moins une offre ou un besoin.")
    return Company(
        name=required("name", 160),
        country=required("country", 100),
        sector=required("sector", 120),
        offers=offers, needs=needs, objectives=objectives,
        website=website or None,
    )


def _tokens(values: Iterable[str]) -> set[str]:
    return {token.casefold() for value in values for token in TOKEN_RE.findall(value)}


def _overlap(left: Iterable[str], right: Iterable[str]) -> set[str]:
    return _tokens(left) & _tokens(right)


def match_companies(companies: Iterable[Company | Mapping[str, Any]]) -> CollaborationMatch:
    normalized = tuple(item if isinstance(item, Company) else normalize_company(item) for item in companies)
    if len(normalized) < 2:
        raise ValueError("Une collaboration nécessite au moins deux entreprises.")
    if len(normalized) > 8:
        raise ValueError("Limite de 8 entreprises par proposition.")
    if len({company.name.casefold() for company in normalized}) != len(normalized):
        raise ValueError("Chaque entreprise doit être distincte.")

    evidence = []
    directional_pairs = 0
    matched_terms = set()
    for i, source in enumerate(normalized):
        for target in normalized[i + 1:]:
            forward = _overlap(source.offers, target.needs)
            backward = _overlap(target.offers, source.needs)
            if forward:
                directional_pairs += 1
                matched_terms.update(forward)
                evidence.append(f"{source.name} propose des éléments correspondant aux besoins déclarés de {target.name} : {', '.join(sorted(forward))}.")
            if backward:
                directional_pairs += 1
                matched_terms.update(backward)
                evidence.append(f"{target.name} propose des éléments correspondant aux besoins déclarés de {source.name} : {', '.join(sorted(backward))}.")
    common_objectives = set.intersection(*[_tokens(company.objectives) for company in normalized]) if all(company.objectives for company in normalized) else set()
    if common_objectives:
        evidence.append("Objectifs déclarés communs : " + ", ".join(sorted(common_objectives)) + ".")
    sectors = sorted({company.sector for company in normalized}, key=str.casefold)
    countries = sorted({company.country for company in normalized}, key=str.casefold)
    if len(sectors) > 1:
        evidence.append("Plusieurs secteurs sont représentés : " + ", ".join(sectors) + ".")
    if len(countries) > 1:
        evidence.append("Une dimension internationale est possible : " + ", ".join(countries) + ".")

    pair_count = len(normalized) * (len(normalized) - 1) // 2
    directional_coverage = min(1.0, directional_pairs / max(1, pair_count * 2))
    objective_score = min(1.0, len(common_objectives) / 3)
    sector_bonus = 0.1 if len(sectors) > 1 else 0.0
    score = round(min(100.0, directional_coverage * 75 + objective_score * 15 + sector_bonus * 100), 1)
    if not evidence:
        evidence.append("Aucune complémentarité textuelle claire n'a été détectée ; les informations déclarées sont insuffisantes pour recommander cette mise en relation.")
    model = "Consortium ou projet commun à plusieurs partenaires" if len(normalized) > 2 else "Partenariat bilatéral ou projet pilote commun"
    steps = (
        "Vérifier l'identité juridique, les représentants et les informations publiques de chaque entreprise.",
        "Confirmer directement les besoins, capacités, disponibilités et objectifs avec chaque entreprise.",
        "Définir le périmètre, les rôles, les coûts, la propriété intellectuelle, la confidentialité et les indicateurs de réussite.",
        "Faire valider un protocole d'accord ou un contrat par les représentants habilités.",
    )
    return CollaborationMatch(normalized, score, tuple(evidence), model, steps)
