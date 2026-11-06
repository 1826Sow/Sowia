"""Static regression checks for the Supabase isolation setup scripts."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_SCHEMA = (ROOT / "supabase" / "schema.sql").read_text(encoding="utf-8")
OPTIONAL_SCHEMA = (ROOT / "supabase_optional_features.sql").read_text(
    encoding="utf-8"
)


def test_messages_and_memory_tables_enable_rls_and_scope_every_policy_to_owner():
    for table in ("sowia_messages", "sowia_memory_items"):
        assert f"alter table public.{table} enable row level security;" in BASE_SCHEMA
        assert f"on public.{table} for select to authenticated" in BASE_SCHEMA
        assert f"on public.{table} for insert to authenticated" in BASE_SCHEMA
        assert f"on public.{table} for delete to authenticated" in BASE_SCHEMA
    assert BASE_SCHEMA.count("using ((select auth.uid()) = user_id);") >= 4
    assert BASE_SCHEMA.count("with check ((select auth.uid()) = user_id);") >= 2


def test_messages_and_memory_grants_are_limited_to_required_operations():
    assert (
        "revoke all on table public.sowia_messages, public.sowia_memory_items"
        in BASE_SCHEMA
    )
    assert (
        "grant select, insert, delete on public.sowia_messages to authenticated;"
        in BASE_SCHEMA
    )
    assert (
        "grant select, insert, delete on public.sowia_memory_items to authenticated;"
        in BASE_SCHEMA
    )
    assert "grant update on" not in BASE_SCHEMA.lower()


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
    entitlement_section = OPTIONAL_SCHEMA.split(
        "-- 2) Private PDF bucket", 1
    )[0].lower()
    assert 'create policy "users can read own premium entitlement"' in entitlement_section
    assert "for insert" not in entitlement_section
    assert "for update" not in entitlement_section
    assert "for delete" not in entitlement_section
    assert "revoke all on public.sowia_entitlements" in entitlement_section
    assert "grant select on public.sowia_entitlements to authenticated" in entitlement_section


def test_validation_guide_requires_isolated_project_and_two_accounts():
    guide = (ROOT / "SUPABASE_ISOLATED_VALIDATION.md").read_text(
        encoding="utf-8"
    )
    assert "projet Supabase temporaire" in guide
    assert "Utilisateur A" in guide
    assert "Utilisateur B" in guide
    assert "Ne pas exécuter le SQL de cette PR sur le projet actuellement utilisé" in guide


def test_restrictive_owner_guards_neutralize_legacy_permissive_policies():
    for table, policy in (
        ("sowia_messages", "SOW IA enforce own messages"),
        ("sowia_memory_items", "SOW IA enforce own memory"),
        ("sowia_entitlements", "SOW IA enforce own Premium entitlement"),
    ):
        assert f'drop policy if exists "{policy}" on public.{table};' in BASE_SCHEMA
        assert f'create policy "{policy}"' in BASE_SCHEMA
    assert BASE_SCHEMA.count("as restrictive for all to public") >= 3
    assert BASE_SCHEMA.count("with check ((select auth.uid()) = user_id)") >= 5
