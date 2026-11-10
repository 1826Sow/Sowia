"""Explainable matching for public SOWIA partner profiles."""
from sowia_global_directory import normalize_directory_profile


def _norm(values):
    if isinstance(values, str):
        values = values.replace(";", ",").split(",")
    if not isinstance(values, (list, tuple, set)):
        return set()
    return {" ".join(str(value).strip().casefold().split()) for value in values if str(value).strip()}


def rank_partner_matches(my_profile, public_profiles, *, limit=5):
    """Rank published public profiles using transparent overlap signals only."""
    if not isinstance(my_profile, dict) or my_profile.get("is_published") is not True:
        return []
    own_id = str(my_profile.get("public_id") or "")
    own_sectors = _norm(my_profile.get("professional_sectors"))
    own_specialties = _norm(my_profile.get("specialties"))
    own_languages = _norm(my_profile.get("languages"))
    own_country = " ".join(str(my_profile.get("country") or "").casefold().split())
    ranked = []
    for raw in public_profiles or []:
        partner = normalize_directory_profile(raw)
        if not partner or not partner["public_id"] or partner["public_id"] == own_id:
            continue
        sectors = own_sectors & _norm(partner.get("professional_sectors"))
        specialties = own_specialties & _norm(partner.get("specialties"))
        languages = own_languages & _norm(partner.get("languages"))
        partner_country = " ".join(str(partner.get("country") or "").casefold().split())
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
