# FINAL TEC — Secure Audit Vault (proposal)

## Objective
Move the in-memory hash-chain concept into a dedicated, server-only PostgreSQL schema. The vault is deliberately separate from SOWIA's existing user, financial, PayPal, incident, and storage data.

## Proposed controls
- Dedicated schema: `final_tec_private`; not intended for exposure through the Supabase REST API.
- Append-only table with database-generated sequence, event UUID, server timestamp, previous hash, and SHA-256 event hash.
- Database trigger serializes concurrent appends and calculates chain fields server-side.
- RLS enabled and forced, with no client-facing policies.
- No privileges for `anon` or `authenticated`; only the trusted `service_role` receives schema usage and table select/insert.
- UPDATE, DELETE, and TRUNCATE are revoked and guarded by triggers.
- Event vocabulary and actor roles are constrained; no free-form payload, credentials, payment data, or evidence contents are stored.

## Important security boundary
Supabase `service_role` bypasses RLS. Its secret must remain exclusively on a trusted server. A server endpoint must authenticate the caller and independently verify the active FINAL TEC role assignment before writing. The proposed SQL does not implement that endpoint or prove caller identity.

## Integrity limits
A hash chain detects modifications and ordering changes when verified, but does not by itself prevent a database owner or privileged operator from rebuilding the entire chain. Production integrity needs independent backups, retention controls, restore drills, periodic verification, alerting, and a separately protected copy/checkpoint.

## Before any production use
1. Review the SQL and extension schema against the actual Supabase project configuration.
2. Apply only in a disposable test project first.
3. Test denied reads/writes for anon and authenticated users, including two distinct accounts.
4. Test concurrent inserts, sequence continuity, hash verification, and mutation rejection.
5. Review function ownership, grants, search_path, backup/restore, and operational alerting.
6. Implement and security-review the server-side authorization endpoint.
7. Obtain explicit approval before a separately reviewed migration is ever applied.

## Scope excluded
No migration was added, no SQL was executed, no Supabase data was read or changed, no service key was used, no investor access was enabled, and no audit event was published.
