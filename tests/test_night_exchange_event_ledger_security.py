from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "supabase_night_exchange_events.sql").read_text(encoding="utf-8").lower()


def test_authenticated_clients_have_append_only_table_privileges():
    normalized = " ".join(SQL.split())
    assert "revoke all on public.sowia_night_exchange_events from anon, authenticated" in normalized
    assert "grant select, insert on public.sowia_night_exchange_events to authenticated" in normalized
    assert "grant update on public.sowia_night_exchange_events to authenticated" not in normalized
    assert "grant delete on public.sowia_night_exchange_events to authenticated" not in normalized


def test_client_insert_policy_excludes_financial_and_server_only_event_types():
    normalized = " ".join(SQL.split())
    start = normalized.index('create policy "nex_events_insert_own_nonfinancial"')
    end = normalized.index(";", start)
    policy = normalized[start:end]
    assert "user_id = auth.uid()" in policy
    assert "event_type in ('match_viewed', 'meeting_confirmed')" in policy
    assert "payment_confirmed" not in policy
    assert "offer_accepted" not in policy
    assert "integration_approved" not in policy


def test_event_app_reference_must_be_visible_and_in_same_workspace():
    normalized = " ".join(SQL.split())
    start = normalized.index('create policy "nex_events_insert_own_nonfinancial"')
    end = normalized.index(";", start)
    policy = normalized[start:end]
    assert "a.id = sowia_night_exchange_events.app_id" in policy
    assert "a.workspace_id = sowia_night_exchange_events.workspace_id" in policy
    assert "(a.user_id = auth.uid() or a.status = 'approved')" in policy


def test_event_ledger_has_no_client_update_or_delete_policies():
    normalized = " ".join(SQL.split())
    assert 'for update to authenticated' not in normalized
    assert 'for delete to authenticated' not in normalized
