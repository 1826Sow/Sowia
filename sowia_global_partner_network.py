"""Explainable matching for public SOWIA partner profiles."""
import re
import unicodedata

from sowia_global_directory import normalize_directory_profile


_LANGUAGE_ALIASES = {
    "fr": "french", "francais": "french", "french": "french",
    "en": "english", "anglais": "english", "english": "english",
    "es": "spanish", "espanol": "spanish", "spanish": "spanish",
    "pt": "portuguese", "portugues": "portuguese", "portuguese": "portuguese",
    "zh": "chinese", "chinois": "chinese", "中文": "chinese", "chinese": "chinese",
    "ar": "arabic", "arabe": "arabic", "العربية": "arabic", "arabic": "arabic",
    "de": "german", "allemand": "german", "deutsch": "german", "german": "german",
    "da": "danish", "danois": "danish", "dansk": "danish", "danish": "danish",
    "nl": "dutch", "neerlandais": "dutch", "nederlands": "dutch", "dutch": "dutch",
    "fi": "finnish", "finnois": "finnish", "suomi": "finnish", "finnish": "finnish",
    "sv": "swedish", "suedois": "swedish", "svenska": "swedish", "swedish": "swedish",
    "no": "norwegian", "norvegien": "norwegian", "norsk": "norwegian", "norwegian": "norwegian",
}


def _canonical(value):
    text = str(value or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^\\w]+", " ", text, flags=re.UNICODE).split())


def _norm(values, *, language=False):
    if isinstance(values, str):
        values = values.replace(";", ",").split(",")
    if not isinstance(values, (list, tuple, set)):
        return set()
    normalized = set()
    for value in values:
        item = _canonical(value)
        if not item:
            continue
        normalized.add(_LANGUAGE_ALIASES.get(item, item) if language else item)
    return normalized


def rank_partner_matches(my_profile, public_profiles, *, limit=5):
    """Rank published public profiles using transparent overlap signals only."""
    if not isinstance(my_profile, dict) or my_profile.get("is_published") is not True:
        return []
    own_id = str(my_profile.get("public_id") or "")
    own_sectors = _norm(my_profile.get("professional_sectors"))
    own_specialties = _norm(my_profile.get("specialties"))
    own_languages = _norm(my_profile.get("languages"), language=True)
    own_country = _canonical(my_profile.get("country"))
    ranked = []
    for raw in public_profiles or []:
        partner = normalize_directory_profile(raw)
        if not partner or not partner["public_id"] or partner["public_id"] == own_id:
            continue
        sectors = own_sectors & _norm(partner.get("professional_sectors"))
        specialties = own_specialties & _norm(partner.get("specialties"))
        languages = own_languages & _norm(partner.get("languages"), language=True)
        partner_country = _canonical(partner.get("country"))
        cross_border = bool(own_country and partner_country and own_country != partner_country)
        # Scores express profile-field overlap, not commercial quality or success probability.
        score = min(100, len(sectors) * 20 + len(specialties) * 15 + len(languages) * 10 + (10 if cross_border else 0))
        reasons = []
        if sectors:
            reasons.append("Secteur(s) commun(s) : " + ", ".join(sorted(sectors)))
        if specialties:
            reasons.append("Spécialité(s) commune(s) : " + ", ".join(sorted(specialties)))
        if languages:
            reasons.append("Langue(s) commune(s) : " + ", ".join(sorted(languages)))
        if cross_border:
            reasons.append("Présence dans un autre pays")
        if not reasons:
            reasons.append("Peu de champs communs : vérifiez manuellement la complémentarité")
        ranked.append({
            **partner,
            "compatibility_score": score,
            "match_reasons": reasons,
        })
    ranked.sort(key=lambda row: (
        -row["compatibility_score"],
        row["verification_status"] != "verified",
        (row.get("display_name") or row.get("app_name")).casefold(),
        row["public_id"],
    ))
    return ranked[:min(max(int(limit), 1), 20)]
