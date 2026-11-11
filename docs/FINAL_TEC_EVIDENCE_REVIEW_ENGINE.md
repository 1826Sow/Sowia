# FINAL TEC — Evidence Review & Approval Engine

## Purpose
Provide a controlled, auditable decision format for reviewing submitted evidence before any future publication workflow.

## Decisions
- `approve_for_publication`: review accepted; dossier may be considered by a separate publication process.
- `request_changes`: additional evidence or corrections required.
- `reject`: evidence not accepted.

## Controls
- Only explicit `final_tec_admin` and `final_tec_analyst` roles are accepted by this pure policy module.
- Submitter/reviewer separation is mandatory.
- Every decision requires a reviewer ID, rationale, and timezone-aware timestamp.
- Approval requires HTTPS source provenance, observation timestamp, evidence reference, and evidence owner.
- Only records in `pending` / `draft` may enter review.
- The source submission is never mutated.

## Important limits
This is a deterministic, side-effect-free decision builder. It does not authenticate the caller, persist an audit log, update Supabase, change evidence status in storage, or publish investor metrics. The caller must enforce identity and role server-side. The returned event explicitly keeps `publication_state=draft`, `published_at=null`, and `publication_authorized=false`. A future production workflow requires isolated FINAL TEC tables, RLS, server-side authorization, immutable audit persistence, two-user integration tests, and a separately approved publication action.
