from sowia_global_directory import filter_directory, normalize_directory_profile


def profile(**overrides):
    row = {
        "public_id": "SOWIA-ABCDEF0123456789ABCD",
        "display_name": "Sowkeys",
        "app_name": "SOWIA",
        "organization": "Sowkeys Group",
        "country": "France",
        "languages": ["fr", "en"],
        "short_description": "Plateforme d'intelligence artificielle",
        "professional_sectors": ["technology", "ai_data"],
        "specialties": ["automatisation", "analyse de données"],
        "verification_status": "verified",
    }
    row.update(overrides)
    return row


def test_filters_combine_country_language_sector_specialty_and_query():
    rows = [profile(), profile(public_id="SOWIA-OTHER", country="Senegal")]
    result = filter_directory(
        rows, country="fran", language="fr", sector="ai_data",
        specialty="données", query="intelligence",
    )
    assert len(result) == 1
    assert result[0]["display_name"] == "Sowkeys"


def test_suspended_or_invalid_public_profiles_are_excluded():
    assert normalize_directory_profile(profile(verification_status="suspended")) is None
    assert normalize_directory_profile({"display_name": "Private"}) is None


def test_directory_projection_excludes_private_fields_and_normalizes_lists():
    result = normalize_directory_profile(profile(
        email="private@example.com", phone="+33000000000",
        user_id="secret", specialties=[" IA ", "IA", "Data"],
    ))
    assert result["specialties"] == ["IA", "Data"]
    assert "email" not in result and "phone" not in result and "user_id" not in result


def test_only_public_records_are_filtered_and_results_are_bounded():
    rows = [profile(is_published=False), profile(public_id="SOWIA-2")]
    result = filter_directory(rows, limit=1)
    assert len(result) == 1
    assert result[0]["public_id"] == "SOWIA-2"
