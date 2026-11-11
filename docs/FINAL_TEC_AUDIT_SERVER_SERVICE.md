# FINAL TEC — Server-side audit service

SOWIA revalidates the user through Supabase Auth immediately before writing. A separate Supabase client is created only on the Streamlit server from `SUPABASE_SERVICE_ROLE_KEY`. The adapter calls only the narrow `final_tec_append_audit_event` RPC. That RPC checks the active, non-expired FINAL TEC assignment and role/action compatibility before inserting into the private schema; database triggers create timestamps and hash-chain fields.

Missing server key, identity mismatch, invalid role/action, missing receipt, or database failure prevents investor dashboard rendering.

The project owner must add `SUPABASE_SERVICE_ROLE_KEY` only to Streamlit server Secrets/environment after confirming the intended Supabase project. Never place it in GitHub, chat, source code, browser code, or session state.

SQL remains a proposal pending review and test-project validation. Tests use mocked clients; no live database/authentication integration is claimed. No migration is applied by this change.
