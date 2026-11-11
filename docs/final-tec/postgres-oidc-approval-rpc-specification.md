# FINAL TEC — PostgreSQL/RPC implementation specification

**Status:** pre-migration technical specification; review required.  
**Parent architecture decision:** `shared-oidc-approval-persistence-architecture.md`.  
**Baseline:** PR #263 commit `5ce5518bdd8483489605eef2a80c47dad50bfeb7`.

This document translates the architecture decision into database invariants, RPC contracts, concurrency rules and acceptance tests. It deliberately contains no executable migration and does not select or configure an identity provider.

## 1. Scope and non-goals

### In scope
- A shared, durable operation coordinator for two SOW IA application approval challenges.
- Atomic reservation/consumption of the pair in one PostgreSQL transaction.
- Durable audit and outbox insertion in that same transaction.
- Leases, fencing tokens, idempotent retries and crash recovery.
- Strict server-side authorization and RLS/privilege boundaries.

### Explicitly out of scope
- Atomic consumption of two upstream OIDC browser/provider sessions. PostgreSQL cannot transact with an independent IdP.
- Storing raw ID tokens, access tokens, refresh tokens, client secrets or private signing keys.
- Replacing the existing SQLite reference store or financial ledger.
- Claiming WORM/immutable-admin-proof storage merely because rows are append-only to application roles.
- Authorizing workload execution. This subsystem records authorization evidence only.

## 2. Trust and authority model

| Data / decision | Authority | Required property |
|---|---|---|
| OIDC token validity | Selected OIDC verifier and configured issuer trust | Signature, issuer, audience, nonce, time and authentication-context validation |
| Subject identity | Verified OIDC claims | Immutable issuer + subject pair |
| Current approval role | Explicitly selected role authority | Versioned decision with bounded staleness |
| Approval challenge | PostgreSQL operational store | Server-generated, one-time, expiring, bound to one operation |
| Pair consumption | PostgreSQL transaction | Both or neither |
| Audit event/outbox | Same PostgreSQL transaction | Durable with pair consumption |
| External audit anchor | Separately configured anchor | Independently verified signed receipt |
| Workload execution | Separate gated executor | Remains disabled unless separately approved |

The database must not infer a role from client-supplied JWT metadata unless the selected role-authority design explicitly makes that claim authoritative and defines revocation/version semantics.

## 3. Logical schema and constraints

Names below are normative for the design; physical names may change only with a reviewed mapping.

### 3.1 `final_tec_approval_operations`

- `operation_id uuid primary key`: server-generated.
- `authorization_id text not null unique`: immutable business authorization key.
- `request_digest char(64) not null`: lowercase SHA-256 hex.
- `state text not null`: constrained state enum.
- `lease_owner uuid null`, `lease_expires_at timestamptz null`.
- `fencing_token bigint not null default 0 check (fencing_token >= 0)`.
- `created_at`, `updated_at` server timestamps.
- `last_error_code text null`: bounded allowlisted code, never raw exception or token.

Invariant: an existing authorization ID can only resolve to the same operation and request digest. Rebinding is a hard failure, not an update.

### 3.2 `final_tec_approval_challenges`

- `challenge_id uuid primary key`: server-generated.
- `operation_id uuid not null references operations`.
- `issuer text not null`, `subject text not null`.
- `key_id text not null`, `role text not null`, `role_version text not null`.
- `policy_version text not null`, `request_digest char(64) not null`.
- `nonce_digest char(64) not null unique`.
- `expires_at timestamptz not null`, `revoked_at timestamptz null`.
- `reserved_by_operation uuid null`, `consumed_at timestamptz null`.
- `created_at timestamptz not null default transaction_timestamp()`.

Required uniqueness:
- Unique nonce digest globally.
- Unique challenge ID globally.
- A challenge may be attached to only one operation and consumed once.
- The pair must have distinct challenge IDs, subjects (issuer + subject), key IDs and nonce digests.
- Do not put raw nonce or bearer token into the database or logs.

The operation's immutable pair binding must be recorded when reservation succeeds. A later retry cannot substitute a different challenge.

### 3.3 `final_tec_approval_operation_events`

- Server-generated event ID and per-operation monotonic event number.
- Operation ID, prior state, next state, fencing token, event digest, server timestamp and bounded reason code.
- Unique `(operation_id, event_number)`.
- Insert-only to application roles. Updates/deletes denied by privileges and, where appropriate, defensive triggers.

### 3.4 `final_tec_approval_audit` and `final_tec_approval_outbox`

Audit and outbox must be inserted in the same transaction that consumes the pair. Outbox payload must identify the exact audit tuple: sequence, previous hash, event hash and timestamp. The payload is canonicalized before hashing; the database must not silently reserialize a different payload.

A unique constraint on operation ID in the audit/outbox prevents duplicate append on retry. The outbox status transition is one-way: pending to anchored. The receipt is stored only after independent verification of the exact tuple.

## 4. State machine

Allowed transitions:

| From | To | Preconditions |
|---|---|---|
| absent | initiated | Valid server request; operation ID generated |
| initiated | reserved | Both challenges eligible; both locked; lease acquired; pair binding persisted |
| reserved | ledger_committed | Current fencing token; both challenges still eligible; role decision valid under chosen freshness policy; audit + outbox inserted; both challenges consumed |
| ledger_committed | completed | External anchor receipt independently verified and persisted |
| any nonterminal | blocked | Integrity failure, impossible state, ambiguous external outcome or explicit security block |

The label `sessions_finalized` is **not** used for application challenges because they are already consumed in `ledger_committed`. It may only be introduced if a selected upstream IdP has a real, documented post-commit finalization operation. It must never imply that a normal OIDC login session was atomically consumed.

A lease renewal does not change the state. Lease takeover increments the fencing token. Every mutating RPC requires the current token.

## 5. RPC contracts

All RPCs are security-definer only if absolutely necessary, with a fixed safe search path, explicit caller-role validation and narrowly scoped grants. Prefer a dedicated backend database role. No direct writes from `anon` or `authenticated`.

### 5.1 `final_tec_create_operation`

Input: authorization ID, request digest.  
Output: operation ID, current state, created/reused indicator.

Rules:
- Validate nonempty bounded authorization ID and lowercase 64-hex digest.
- Insert once or return existing operation only when digest matches exactly.
- Reject a changed digest or attempt to bind an existing authorization to a different operation.
- Never return approval tokens or secrets.

### 5.2 `final_tec_register_challenge`

Input: operation ID, verified issuer/subject, key ID, role and role version, policy version, request digest, nonce digest, expiry.

Rules:
- Callable only by the trusted backend after OIDC verification; not by browser clients.
- Verify operation exists, state is initiated, request digest matches, expiry is in future and all fields are bounded.
- Enforce unique challenge/nonce and immutable binding.
- This function records a server-side approval challenge, not an upstream IdP session.
- The backend must bind the challenge to a verified authentication result; client input alone is never proof.

### 5.3 `final_tec_reserve_pair`

Input: operation ID, exactly two challenge IDs, worker ID, expected request digest, lease duration.

Transaction:
1. Lock operation row.
2. If already reserved by the same operation and exact same pair with valid lease, return idempotently.
3. Lock both challenge rows in deterministic UUID order.
4. Verify exactly two distinct rows; same operation; same request/policy; distinct issuer+subject, key IDs and nonce digests; unexpired; not revoked; not consumed; not reserved elsewhere.
5. Acquire lease and increment fencing token.
6. Persist immutable pair binding and append state event.
7. Commit all changes together.

Failure: neither challenge is reserved. Return a stable sanitized error code.

### 5.4 `final_tec_commit_pair`

Input: operation ID, fencing token, exact canonical audit event, role decision reference/version.

Transaction:
1. Lock operation and challenge rows in deterministic order.
2. Verify state reserved, current lease owner/token and lease not expired.
3. Verify pair binding and request digest unchanged.
4. Verify both challenges remain reserved by this operation, unrevoked, unconsumed and unexpired.
5. Apply the approved role-freshness rule; reject stale/revoked decisions.
6. Insert exactly one audit record and one outbox record.
7. Mark both challenges consumed.
8. Transition operation to ledger_committed and append event.
9. Commit.

Any failed check rolls back all writes. Strict success means transaction committed. An exact retry returns the original committed result. A retry with a different payload, pair, role version or digest fails closed.

### 5.5 `final_tec_record_anchor_receipt`

Input: operation ID, exact audit tuple, receipt bytes/structured receipt.

Rules:
- Verify receipt cryptographically in trusted backend code against the configured anchor trust root; SQL must not treat a nonempty JSON object as a verified receipt.
- Check receipt tuple equals the stored outbox tuple exactly.
- Update pending to anchored and operation to completed in one transaction.
- Exact retry is idempotent; changed receipt or tuple rejected.
- Do not mark completed when anchor is unavailable.

### 5.6 `final_tec_recover_operation`

Read-only response: authoritative state, current fencing token, lease expiry, pair binding fingerprints, outbox state and safe next action.

Rules:
- Must not consume, reserve, append or finalize as a side effect.
- A worker may then call the appropriate explicit RPC with the same operation ID.
- Unknown external outcome => blocked/reconciliation; never guess that an external append failed and blindly append again.

## 6. Concurrency, locking and idempotency

- Lock order is always operation row first, then challenge rows sorted by UUID, then audit/outbox rows. All code paths use the same order.
- Unique constraints are the final race-condition defense; application pre-checks are not sufficient.
- Use database server time for expiry and lease decisions.
- Lease takeover is permitted only after expiry and increments fencing token under row lock.
- A stale token is rejected even if the old worker resumes.
- No network calls occur inside the database transaction.
- External anchoring uses the durable outbox after commit and a provider-supported idempotency key derived from the immutable operation/audit tuple.
- If the anchor provider cannot safely deduplicate or query by idempotency key, uncertain outcomes enter blocked/manual reconciliation.

## 7. Role freshness decision required before migration

### 7.1 Repository authority inventory (verified at commit 5e1726f)

The existing Supabase schema does **not** provide a central, versioned FINAL TEC approval-role registry.

Observed mechanisms are narrower and must not be conflated:

- `auth.users` is the account identity source; the inspected application auth helper performs GitHub OAuth through Supabase Auth and returns the authenticated user. It does not implement FINAL TEC role assignment.
- `app_metadata.role` and `app_metadata.sowia_admin` are consulted by selected administrative SQL paths, including GLOBAL ID verification and technical-incident access. These are administrative flags, not a documented `security-approver` assignment system.
- GLOBAL Action Governance stores a per-plan `approver_id` and checks that account when transitioning a submitted plan. It is scoped to that plan workflow; it is not a global role registry, has no shared role version/revocation epoch contract, and cannot be reused as FINAL TEC authority without a separate reviewed mapping.
- Premium entitlements, PayPal subscriptions, and financial-ledger ownership describe commercial/account state, not security approval authority.
- No inspected migration establishes a protected role-assignment table, a role version, a revocation epoch, or a transactionally enforced `security-approver` role.

**Decision:** neither role-authority model A nor model B is currently implemented or proven by repository evidence. Model A is a possible future design, not an existing capability. Do not map `admin` to `security-approver`, infer approval authority from account ownership, or trust user-editable profile metadata.

Before implementation, the owner/security design must explicitly decide:
1. who may grant, revoke and inspect the `security-approver` role;
2. whether role assignments are held in a dedicated protected PostgreSQL table or an external authority;
3. how each change increments a monotonic version/revocation epoch;
4. how the commit transaction rejects stale decisions and handles concurrent revocation;
5. how two distinct approvers and separation-of-duties rules are enforced;
6. how privileged administration is audited independently.

A PostgreSQL role table can make role lookup and challenge consumption transactionally consistent only if the trusted role assignment and revocation records are themselves authoritative and protected. It cannot establish that trust merely by existing.


Choose one model and document it:

**A. Same trust domain:** current role assignments and revocation epoch live in protected PostgreSQL tables. Commit RPC locks/reads the relevant assignment and verifies its version in the same transaction.

**B. External authority:** role authority returns a signed, short-lived decision bound to issuer, subject, role, policy version, request digest and monotonic revocation/version epoch. Define maximum staleness, emergency revocation and behavior during authority outage. A boolean callback without a verifiable decision/version is insufficient.

Do not implement both paths implicitly. The selected authority and its key management must be reviewed first.

## 8. Privilege and RLS acceptance

- Enable RLS on all operational tables.
- No client-facing policies for insert/update/delete.
- Revoke all direct table privileges from `anon` and `authenticated`.
- Grant execute only on reviewed RPCs to the dedicated backend role.
- Ensure security-definer functions set `search_path` and cannot be shadowed by attacker-controlled schemas.
- Service-role credentials remain server-only and are never placed in mobile/web client bundles.
- Test with two real staging users, an ordinary authenticated role, anon and the backend role.
- Admin support access is separately logged and cannot rewrite event history without an independently detectable privileged audit trail.

RLS alone is not a defense against a leaked Supabase service-role key. Secret custody and rotation are separate acceptance gates.

## 9. Failure-injection test matrix

Run on real PostgreSQL staging with separate connections/processes; SQLite tests remain useful but cannot satisfy this gate.

| Scenario | Required assertion |
|---|---|
| Two workers reserve same pair simultaneously | Exactly one reservation; no partial pair |
| Two pairs share one challenge | At most one pair reserves/commits |
| Duplicate nonce digest | Unique constraint rejects |
| Same authorization, altered digest | Rejected; original operation unchanged |
| Same operation, altered pair | Rejected |
| Duplicate subject/key ID | Rejected |
| Revocation/expiry before reserve | Neither reserved |
| Revocation/expiry before commit | Neither consumed; transaction rolls back |
| Crash before reserve commit | No reservation persists |
| Crash after reserve commit | Recovery sees reserved state and lease |
| Lease expires; new worker takes over | Fencing token increments; old worker rejected |
| Crash during pair commit | Both consumed + audit/outbox, or none |
| Commit succeeds but response lost | Exact retry returns same committed event |
| Retry with changed payload | Rejected |
| Anchor append succeeds but response lost | Query/deduplicate by stable key; no blind duplicate append |
| Receipt does not match checkpoint tuple | Operation not completed |
| Anchor unavailable | Outbox pending; operation not completed |
| Unauthorized client calls RPC/table | Denied |
| Two real accounts read each other's records | Denied |
| Backup/restore and recovery | State, uniqueness and hash-chain invariants preserved |

Each test inspects committed database rows after fault injection; checking only RPC return values is insufficient.

## 10. Migration and rollout plan (not authorized yet)

1. Confirm selected IdP, role authority and meaning of one-time session consumption.
2. Review logical schema, RPC signatures, privilege model and threat model.
3. Write additive migration in a new timestamped file; never alter the financial ledger or existing migrations.
4. Apply only to an isolated staging Supabase project.
5. Run migration twice to verify safe idempotency where intended; verify rollback/forward-recovery strategy.
6. Run SQL unit tests, concurrent integration tests, RLS two-account tests and crash-injection tests.
7. Implement a separate production adapter and wire the engine to it only after conformance and runtime tests.
8. Keep execution disabled; require independent security review and explicit G2-B approval before any production workload.

## 11. Current implementation gap checklist

| Requirement | Current repository status at baseline |
|---|---|
| Local atomic SQLite reference | Exists; single-host only |
| Shared PostgreSQL operation schema | Not implemented |
| Challenge/session registry for approval pair | Not implemented |
| Atomic reserve-pair RPC | Not implemented |
| Atomic consume + audit + outbox RPC | Not implemented |
| Lease and fencing token | Not implemented for OIDC pair |
| Role authority freshness model | Not selected |
| Crash recovery coordinator for OIDC pair | Not implemented |
| Real PostgreSQL concurrency tests | Not run / not present as accepted evidence |
| Real two-account RLS tests | Prepared but skipped on PR |
| OIDC pair wired into runtime engine | Not implemented |
| Production IdP/KMS/HSM/anchor | Not configured |

**Decision:** architecture and database contract are now sufficiently specified for a design review, but not for a production migration. Do not create SQL or connect a live provider until the authority-model and security gates in sections 7 and 10 are resolved. **G2-B remains NO-GO / NOT_RUN.**

### 7.2 Administrative-claim and revocation boundary (verified at commit eec2013f)

The inspected SQL uses JWT `app_metadata` claims (`role=admin` and/or `sowia_admin=true`) as the authorization predicate for selected GLOBAL ID and technical-incident operations. The repository evidence inspected here does not establish a PostgreSQL-owned, versioned assignment/revocation record for those claims, nor a transactional mechanism that invalidates already-issued JWTs at the moment an administrator is revoked.

Consequences for FINAL TEC:

- A role decision based only on the current JWT can remain stale until token expiry/refresh; JWT claim presence is not proof of immediate revocation freshness.
- A PostgreSQL challenge-commit RPC cannot close that gap unless it checks a protected authoritative role record and version inside the same transaction that commits the approval pair.
- A privileged operator who can alter Auth user metadata or issue equivalent privileged tokens remains inside the trust boundary. The approval design must document and audit that administrative trust boundary; it must not claim protection against unrestricted project-owner/Supabase service-role compromise.
- Existing GLOBAL ID trigger logic lets JWT admin claims bypass owner-preserved verification fields. This is a separate existing administrative path, not an approval-role registry.
- The technical-incident RLS policy permits admin-claim users to update incident rows; the inspected migration does not add a separate append-only audit of those updates. This cannot be reused as a trusted FINAL TEC audit log.

**Required revocation rule:** role grant/revoke must increment a monotonic role version in the authoritative store. At pair reservation and again at pair commit, the server must compare both approvers' recorded role version with the current authoritative version under transactionally consistent locking. If either version changed, the operation must become blocked/restart-required; it must never silently accept the earlier decision. Any emergency revocation must also invalidate or supersede outstanding leases/reservations.

**Status:** no such authoritative versioned role store or concurrent-revocation enforcement was found in the inspected repository. Model A remains unproven; model B remains unconfigured. No executable SQL should be written against an assumed authority.


### 7.3 Privileged SQL and service-role trust boundary (repository inspection)

The inspected SQL contains at least two `SECURITY DEFINER` functions outside FINAL TEC:

- `public.sowia_admin_set_global_id_verification(uuid,text,text)` checks the caller's JWT admin claims, uses an empty search path, qualifies the target table, revokes default PUBLIC execution, and grants execution to `authenticated`. This is a comparatively explicit privilege boundary, but the admin predicate still inherits the JWT freshness/revocation gap described above.
- `public.sowia_action_transition(uuid,text,text)` performs a row-locked, state-checked transition for the plan's creator or its specifically assigned approver, then writes the corresponding audit row in the same transaction. It revokes execution from PUBLIC/anon and grants it to authenticated. It uses `SECURITY DEFINER` with `search_path = public, auth`; before any reuse or expansion, harden this to an explicitly trusted path (or fully qualify every referenced object and exclude writable schemas), and confirm the function owner and schema CREATE privileges in the live project. Its per-plan `approver_id` is not FINAL TEC security-role authority.
- The PayPal webhook Edge Function uses `SUPABASE_SERVICE_ROLE_KEY` to read the configured PayPal plan and write subscription state only after PayPal's webhook verification and server-side subscription reconciliation. This is a high-privilege credential and must remain server-side, secret-managed, narrowly deployed, and never enter Streamlit/client configuration or logs. Repository code cannot prove the live secret's access, rotation, or deployment boundary.

The canonical entitlement schema grants authenticated users SELECT only; its comments specify trusted server writes. The SQL diagnostic script `supabase_security_diagnostics.sql` is read-only and is designed to inspect effective policies, RLS/FORCE RLS flags, table/sequence grants, and private bucket configuration. It is **not evidence that those queries have been run against the live project**.

**Critical distinction:** Supabase `service_role` is a privileged server identity and can bypass ordinary RLS protections. A FINAL TEC approval RPC must not be callable by end users with a service-role credential. It must expose only narrowly scoped operations, validate caller identity where applicable, protect execution grants, and keep service credentials outside the application client. The RPC owner and any SECURITY DEFINER path must be reviewed as part of the trust boundary.

**Live verification still required:** inspect actual `pg_proc.prosecdef`, function owners, `proconfig` search paths, EXECUTE grants, schema CREATE grants, default privileges, role membership, table/sequence ACLs, RLS and FORCE RLS, Auth admin API access, Edge Function secret deployment, and key rotation. The repository inspection cannot establish any of those live project facts.

**Decision:** do not extend either existing SECURITY DEFINER function for FINAL TEC. Implement a dedicated, narrowly granted RPC set only after the role authority is selected and the live privilege inventory is captured. Keep all existing financial-ledger and PayPal functions/migrations unchanged.

### 7.4 Admin-claim issuance path and application authentication boundary

The application authentication helper `sowia_supabase_auth.py` creates a per-session Supabase client using only `SUPABASE_URL` and `SUPABASE_ANON_KEY`; its docstring explicitly excludes service-role keys. It uses GitHub OAuth through Supabase PKCE, stores only a short-lived browser-scoped PKCE verifier in SQLite, and keeps access/refresh session values in client memory. The helper contains no Auth Admin API call and no operation that writes `app_metadata`.

The inspected application code reads `current_user.app_metadata` to decide whether to display administrator functions. The inspected GLOBAL ID and technical-incident SQL policies independently check the same JWT claims. No application-side route or helper that assigns/removes `role=admin` or `sowia_admin=true` was found in the reviewed files. Repository evidence therefore points to claim issuance being an out-of-band Supabase Auth administration task (Dashboard or a separately controlled Auth Admin API operator), but the actual live operator, process, MFA, approval, and audit trail are **not verified**. Absence from the inspected application code is not proof that no external automation or dashboard process exists.

The PKCE browser scope is a locator, not an authentication credential; it is hashed before SQLite storage and cannot by itself grant a SOW IA role. This is a useful separation to preserve.

**Required control before production FINAL TEC:** document and test a break-glass/admin-claim lifecycle owned outside the end-user application: named authorized operators, MFA, dual control for grant/revoke, immutable issuance/revocation log, reason/ticket, bounded JWT lifetime, forced session refresh/revocation strategy, and independent verification of effective claims. Do not implement a self-service admin-claim endpoint in Streamlit. The FINAL TEC role authority must be separate from general SOW IA UI admin claims and must have its own version/revocation semantics.

**Current result:** no in-app admin-claim minting path was found in the reviewed authentication helper and application call sites. Actual claim issuer and live Supabase Auth controls remain **NOT_VERIFIED**.
