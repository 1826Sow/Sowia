"""Privacy-safe filtering for the SOWIA GLOBAL DIRECTORY."""

SECTORS = {
    "technology": "Technologie & logiciels",
    "ai_data": "Intelligence artificielle & données",
    "commerce": "Commerce & e-commerce",
    "finance": "Finance & fintech",
    "health_wellness": "Santé & bien-être",
    "education": "Éducation & formation",
    "food_agriculture": "Alimentation & agriculture",
    "travel_tourism": "Voyage & tourisme",
    "media_creative": "Médias & création",
    "industry_logistics": "Industrie & logistique",
    "environment_energy": "Environnement & énergie",
    "professional_services": "Services professionnels",
    "nonprofit_development": "Associations & développement",
    "other": "Autre",
}
ALLOWED_SECTORS = frozenset(SECTORS)


def _terms(values, *, max_items=12, max_length=60):
    if isinstance(values, str):
        raw = values.replace(";", ",").split(",")
    elif isinstance(values, (list, tuple, set)):
        raw = list(values)
    else:
        raw = []
    result = []
    seen = set()
    for value in raw:
        item = " ".join(str(value or "").strip().split())[:max_length]
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
        if len(result) >= max_items:
            break
    return result


def normalize_directory_profile(record):
    """Project only public directory fields and normalize list values."""
    if not isinstance(record, dict):
        return None
    if record.get("is_published") is False or record.get("verification_status") == "suspended":
        return None
    public_id = str(record.get("public_id") or "").strip()
    if not public_id.startswith("SOWIA-"):
        return None
    sectors = [s for s in _terms(record.get("professional_sectors"), max_items=14) if s in ALLOWED_SECTORS]
    return {
        "public_id": public_id,
        "display_name": str(record.get("display_name") or "").strip(),
        "app_name": str(record.get("app_name") or "").strip(),
        "organization": str(record.get("organization") or "").strip(),
        "country": str(record.get("country") or "").strip(),
        "languages": _terms(record.get("languages"), max_items=12, max_length=40),
        "website": str(record.get("website") or "").strip(),
        "short_description": str(record.get("short_description") or "").strip(),
        "professional_sectors": sectors,
        "specialties": _terms(record.get("specialties")),
        "verification_status": str(record.get("verification_status") or "unverified"),
    }


def filter_directory(records, *, country="", language="", sector="", specialty="", query="", limit=100):
    """Filter public profiles; all supplied filters are combined with AND."""
    country = str(country or "").strip().casefold()
    language = str(language or "").strip().casefold()
    sector = str(sector or "").strip()
    specialty = str(specialty or "").strip().casefold()
    query = str(query or "").strip().casefold()
    results = []
    for raw in records or []:
        item = normalize_directory_profile(raw)
        if not item:
            continue
        if country and country not in item["country"].casefold():
            continue
        if language and not any(language == value.casefold() for value in item["languages"]):
            continue
        if sector and sector not in item["professional_sectors"]:
            continue
        if specialty and not any(specialty in value.casefold() for value in item["specialties"]):
            continue
        searchable = " ".join([
            item["display_name"], item["app_name"], item["organization"],
            item["country"], item["short_description"], *item["specialties"],
        ]).casefold()
        if query and query not in searchable:
            continue
        results.append(item)
    results.sort(key=lambda row: (
        row["verification_status"] != "verified",
        (row["display_name"] or row["app_name"]).casefold(),
        row["public_id"],
    ))
    return results[:min(max(int(limit), 1), 200)]
