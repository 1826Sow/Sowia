# FINAL TEC — architecture decision: shared OIDC approval persistence

**Status:** design decision for review; not an implementation or production approval.  
**Reviewed baseline:** PR #263, commit `5004d85aaf7958e034a5787c11b8a941871597a3`.

## Decision

Use a shared PostgreSQL transaction boundary as the preferred persistence design candidate for FINAL TEC approval operations. Supabase PostgreSQL is a candidate because the repository already uses Supabase migrations, RLS and server-side functions. This is not a provider selection or authorization to provision, migrate, deploy or connect production credentials.

Do not reuse `sowia_financial_transactions`, `sowia_subscriptions` or `sowia_technical_incidents` as an OIDC session or approval-operation store. They have different data ownership, retention and access semantics.

The local `SQLiteAtomicApprovalStore` remains a single-host reference/test implementation. It is not a shared production store.

## Critical boundary: identity-provider sessions vs application approval sessions

An external OIDC provider's browser/login session is not generally part of the application's PostgreSQL transaction. Therefore a PostgreSQL RPC cannot truthfully promise to atomically consume two sessions held by an independent identity provider.

The safe design is to distinguish:

1. **OIDC authentication:** validate issuer, audience, signature, nonce, ACR/AMR, authentication age and subject; query current role authority.
2. **Application approval challenge:** after successful authentication, create a short-lived, server-side, one-time approval record in the shared store. Bind it to the verified subject, role, authorization, request digest, OIDC issuer, authentication context and a random challenge nonce. Never accept a session ID or nonce supplied by the approval manifest as authoritative.
3. **Pair finalization:** atomically reserve/consume both application approval records and write the approval audit event plus anchor outbox in one database transaction.

This makes the pair atomic within the application's shared persistence domain. It does **not** make upstream OIDC login sessions atomic. If policy requires upstream IdP sessions themselves to be consumed exactly once as a pair, the chosen identity provider must explicitly support that primitive; otherwise that requirement is technically unmet and G2-B remains NO-GO.

## Proposed persistence model (logical schema, not yet a migration)

### `final_tec_approval_operations`

- `operation_id` UUID primary key, generated once by the server.
- `authorization_id` unique and immutable.
- `request_digest` fixed 64-character SHA-256 hex digest.
- `state` constrained to `initiated | reserved | ledger_committed | sessions_finalized | completed | blocked`.
- `lease_owner`, `lease_expires_at`, monotonically increasing `fencing_token`.
- `created_at`, `updated_at`, `last_error_code` (sanitized code only).
- Immutable binding to the two approval-record IDs, subjects, key IDs, nonce digests and policy version.

### `final_tec_approval_sessions`

- Opaque server-generated session ID; never store raw bearer ID tokens.
- Subject, issuer, client/audience, role, policy version and authentication context.
- Nonce digest (not plaintext nonce), request digest and authorization binding.
- Expiry, revocation timestamp, consumption timestamp and associated operation ID.
- Unique constraints preventing nonce reuse and session reuse.
- No client INSERT/UPDATE/DELETE. Access only through narrowly scoped server-side functions.

### `final_tec_approval_operation_events`

Append-only transition journal: operation ID, prior/new state, fencing token, event digest, timestamp and sanitized reason. Enforce allowed transitions in database functions; ordinary application roles cannot update or delete prior events.

### Outbox

Persist the audit event and external-anchor outbox record in the same transaction as pair finalization. External anchoring remains asynchronous and idempotent. A pending anchor is not a completed operation.

## Required server-side transaction API

Expose narrow database functions (names illustrative; do not implement until provider and migration review):

- `create_approval_operation(...)`: idempotently create or return the same operation for the same authorization and request digest; reject rebinding.
- `register_approval_session(...)`: insert one verified application approval challenge; reject duplicate nonce/session IDs and mismatched operation bindings.
- `reserve_approval_pair(operation_id, session_a, session_b, expected_digest, worker_id)`: lock operation and both session rows in a deterministic order; verify exactly two distinct subjects/sessions/nonces, current state, expiry, revocation, request binding and lease; increment fencing token; reserve both or neither.
- `commit_approval_pair(operation_id, fencing_token, audit_event)`: verify current lease/token and both reservations; in one transaction mark both records consumed, append the audit event and outbox row, and transition to `ledger_committed`. Exact retry returns the original result; changed payload or stale token fails closed.
- `finalize_approval_operation(operation_id, fencing_token, verified_anchor_receipt)`: verify the receipt against the exact checkpoint tuple and advance to `completed`; otherwise remain pending or become `blocked`.
- `recover_approval_operation(operation_id)`: read authoritative state and return the next safe action; never blindly consume or replay an external side effect.

All functions must use fixed `search_path`, explicit role checks, strict argument validation, row locks, unique constraints and transaction rollback on any failed invariant. Revoke direct table writes from `anon` and `authenticated`; grant execution only to a dedicated server-side role. Do not expose service-role credentials to clients.

## State and recovery invariants

- `initiated`: operation and immutable request binding are durable.
- `reserved`: both application approval sessions are reserved together under one live lease and fencing token; never one only.
- `ledger_committed`: both sessions are consumed and audit plus outbox are durable in one PostgreSQL transaction.
- `sessions_finalized`: reserved for a design that has a separately justified finalization step; do not use it to imply upstream IdP session consumption unless that actually occurred.
- `completed`: required external anchor receipt is independently verified and linked to the exact audit checkpoint.
- `blocked`: ambiguity, impossible state, expired lease with uncertain external outcome, or failed integrity check; manual reconciliation required.

A stale worker must be unable to commit after lease takeover: every mutating call checks the current fencing token. Lease expiry alone never authorizes a retry of an external side effect. Retries use the same operation ID and immutable payload. Conflicting payloads, missing rows, partial pairs and unknown outcomes fail closed.

## Role freshness

A role check performed against an external directory cannot be made atomic with a PostgreSQL commit unless that authority participates in the same transaction protocol. Before implementation, choose and document one of these policies:

- authoritative role assignments and revocation versions are maintained in the same protected PostgreSQL trust domain, so the transaction can check them under lock; or
- an external directory issues a signed, short-lived authorization decision with a monotonic version/revocation epoch, and the accepted staleness bound and emergency-revocation procedure are explicitly approved.

A plain boolean callback immediately before the database transaction is not sufficient evidence of role freshness at commit time.

## Required failure and concurrency tests

Test against real PostgreSQL/Supabase staging (not SQLite-only fakes):

- two workers reserve the same pair concurrently: exactly one wins;
- one session is reused across two different pairs: at most one wins;
- same authorization with changed request digest: rejected;
- duplicate subjects, sessions or nonce digests: rejected;
- revoke/expire one member before reservation and before commit: pair rejected or safely released;
- worker crash before reservation, after reservation, during commit, after commit before response, and after external append before receipt persistence;
- lease expiry and takeover: stale fencing token rejected;
- exact retry: same operation/checkpoint returned without duplicate consumption or audit;
- payload-changing retry: rejected;
- multiple application instances and database connections;
- restore/recovery from backup and audit/outbox integrity checks;
- RLS tests using two distinct real test accounts plus an unauthorized role.

Tests must assert durable database state after each fault, not only returned booleans. Keep real-account tests isolated from pull-request code and secrets as currently designed.

## Acceptance gates

No migration, provider adapter, secret provisioning, production connection or workload is authorized by this design note. Implementation may begin only after:
1. the identity provider and role-authority model are explicitly selected;
2. it is confirmed whether the policy requires upstream IdP session consumption or application challenge consumption;
3. the PostgreSQL transaction/RPC and privilege model is reviewed;
4. the migration and rollback plan are reviewed;
5. tests can run in an isolated staging project with dedicated credentials.

Until those gates and independent security review pass: **G2-B = NO-GO / NOT_RUN**.
