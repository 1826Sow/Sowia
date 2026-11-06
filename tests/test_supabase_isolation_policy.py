"""Static regression checks for the Supabase isolation setup scripts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
OPTIONAL_SCHEMA = (ROOT / "supabase_optional_features.sql").read_text(
    encoding="utf-8"
)


def test_entitlements_are_readable_only_by_their_owner():
    assert "alter table public.sowia_entitlements enable row level security;" in BASE_SCHEMA
    assert "using ((select auth.uid()) = user_id);" in BASE_SCHEMA
    assert (
        "revoke all on public.sowia_entitlements from public, anon, authenticated;"
        in BASE_SCHEMA
    )
    assert "grant select on public.sowia_entitlements to authenticated;" in BASE_SCHEMA


def test_private_bucket_is_not_public_and_has_pdf_size_limits():
    assert "'sowia-private-documents'" in OPTIONAL_SCHEMA
    assert "false," in OPTIONAL_SCHEMA
    assert "10485760" in OPTIONAL_SCHEMA
    assert "array['application/pdf']" in OPTIONAL_SCHEMA
    assert "on conflict (id) do nothing;" in OPTIONAL_SCHEMA


def test_storage_has_restrictive_user_and_active_entitlement_guard():
    assert (
        'create policy "SOW IA enforce private PDF folder isolation"'
        in OPTIONAL_SCHEMA
    )
    assert "as restrictive for all to public" in OPTIONAL_SCHEMA
    assert "(storage.foldername(name))[1] = (select auth.uid())::text" in OPTIONAL_SCHEMA
    assert "entitlement.status = 'active'" in OPTIONAL_SCHEMA


def test_authenticated_users_get_no_entitlement_write_policy():
    policies = [
        line.lower()
        for line in OPTIONAL_SCHEMA.splitlines()
        if line.strip().lower().startswith("create policy")
        and "sowia_entitlements" in line.lower()
    ]
    assert policies == [
        'create policy "users can read own premium entitlement"'
    ]
    assert "for insert to authenticated" not in OPTIONAL_SCHEMA.lower()
    assert "for update to authenticated" not in OPTIONAL_SCHEMA.lower()
    assert "for delete to authenticated" not in OPTIONAL_SCHEMA.lower()


def test_validation_guide_requires_isolated_project_and_two_accounts():
    guide = (ROOT / "SUPABASE_ISOLATED_VALIDATION.md").read_text(
        encoding="utf-8"
    )
    assert "projet Supabase temporaire" in guide
    assert "Utilisateur A" in guide
    assert "Utilisateur B" in guide
    assert "Ne pas exécuter le SQL de cette PR sur le projet actuellement utilisé" in guide
