# FINAL TEC — Audit Trail

## Scope
A minimal, append-only event format for tracking evidence submissions, reviews, access changes, and future publication actions. Events are linked by SHA-256 hashes over canonical JSON.

## Event fields
Actor ID and explicit role, action, resource type/ID, outcome, timezone-aware timestamp, controlled reason code, previous hash, and event hash. The schema intentionally excludes passwords, tokens, private evidence contents, free-form payloads, and payment details.

## Integrity properties
- Each event commits to the preceding event hash.
- Reordering, removal from the middle, or modification is detectable when the chain is verified.
- Appending returns a new list and does not mutate the caller's existing list.
- Summaries are produced only for a valid chain.

## Critical limitations
This implementation is in-memory only. A hash chain does not itself prevent a privileged operator from rebuilding the entire chain, prove actor identity, provide trusted timestamps, or guarantee retention. It is not immutable storage and is not yet a production audit log.

## Production requirements before external/investor use
1. Dedicated FINAL TEC audit table, separate from SOWIA private and financial tables.
2. Server-side actor authentication and role/assignment verification on every write.
3. Insert-only database permissions, deny client update/delete, and restrictive RLS.
4. Trusted server timestamps and database-generated sequence numbers.
5. Persist event hashes and verify chain continuity in server-side transactions.
6. Independent backup/retention controls and alerting on integrity failures.
7. Two-account integration tests and security review before deployment.
8. No investor-visible audit details until an explicit publication policy is approved.

No migration, database write, external access, publication, or deployment is included in this PR.
