# SOWIA NIGHT EXCHANGE

## Positioning
A timezone-aware international marketplace for digital applications and services. It combines an approved application directory, service discovery, compatibility matching, bilateral collaboration proposals and administrative integration review. It is not a securities exchange and issues no tradable financial instruments.

## Product areas
1. Application directory: application name, country, IANA time zone, categories, services offered and services wanted.
2. Moderation: new listings are pending by default; only approved listings appear in the public catalogue. Changes by a non-admin return a listing to pending review.
3. Night sessions: each approved application has a local session window (default 20:00–06:00); the interface displays local time and UTC without launching sessions automatically.
4. Compatibility: explainable category and service matching, plus a separate evidence checklist. Scores are indicative and are not endorsements or forecasts.
5. Collaboration: a professional application can send a proposal to another approved application. The recipient can accept or reject; accepted proposals may enter a separate administrative integration review.
6. Activity report: member-visible event history for matching consultations and member-declared meeting confirmations. Payment events are reserved for trusted server-side writers.

## Budget and payments — not production-enabled
The rules module contains pure helpers for validating currency amounts, checking daily/weekly/monthly caps and selecting offers within a budget. These helpers are not, by themselves, a production spending control. Before any paid offer, bid, visibility placement or campaign can be activated, a trusted backend must atomically reserve the budget, verify provider payment status, enforce all caps, and handle refunds and chargebacks. Client-side checks are never sufficient. No paid NIGHT EXCHANGE action should be described as live until that backend workflow and its operational controls have been implemented and verified.

## Trust and privacy
- New listings are private pending moderation; regular members cannot self-approve or self-verify.
- Public catalogue queries are limited to approved records by database policy.
- Activity records are append-only for authenticated clients. Members may submit only the allowed non-financial event types; payment-confirmed events require a trusted server process.
- Administrative moderation and integration decisions must be performed through database functions that validate the signed administrator claim.
- Ownership/domain verification, security review, dispute handling, appeals and delivery ratings require separate operational workflows; do not imply they are automated unless implemented and tested.

## Current implementation status

### Present in the application code
- The professional NIGHT EXCHANGE page and the separate Bourse aux applications catalogue are present in Streamlit.
- Listing submission, member application tracking and administrator moderation are wired to the persistent application registry functions in `cloud_storage.py`.
- The approved catalogue supports country, category and text filtering.
- IANA time-zone session status, next-opening calculations, explainable matching and partner-evidence summaries are implemented.
- The activity view reads the member's event ledger and reports only events actually recorded.
- Bilateral proposal and administrative integration-review UI calls guarded database RPCs.

### Supabase SQL assets in the repository
- `supabase_night_exchange_registry.sql` defines the application registry, row-level security, pending-by-default trigger and administrator review RPC.
- `supabase_night_exchange_events.sql` defines the append-only event ledger and member insert restrictions.
- The application code calls additional RPCs for bilateral offers and integration review. Their definitions must be retained in version-controlled migration files and deployed consistently across environments.

### Database environment comparison — read-only audit, 21 November 2026
- The SOWIA TEST project contains the base application registry and activity ledger, plus additional NIGHT EXCHANGE mission, deal, verification and proposal/integration-review objects. Its migration history includes the `sowia_nex_missions`, `night_exchange_commercial_ledger`, `night_exchange_contract_transitions`, `night_exchange_proposal_audit` and `night_exchange_deal_creation` changes.
- The production SOWIA project currently contains the base application registry and activity ledger, but the read-only schema/function inspection did not find the advanced mission/deal tables or the associated proposal, mission and deal RPCs.
- Therefore, advanced commercial workflows available in the test database must not be assumed to exist in production. The test migration SQL must be reconciled with version control, reviewed for RLS and function privileges, and tested before any production rollout.
- No production migration was applied during this audit.

### Not yet established as production capabilities
- No automatic night-session scheduler or background execution.
- No verified production deployment of advanced missions, deals, proposal audit or commercial ledger.
- No live paid marketplace, bidding, paid visibility placement or atomic budget reservation.
- No end-to-end payment/refund/chargeback workflow for NIGHT EXCHANGE.
- No ownership/domain verification automation or completed dispute/appeal operations.

## Safe rollout
1. Recover and version-control the exact migrations already exercised in the test project; do not reconstruct them from table names alone.
2. Review function security, grants, RLS policies and participant visibility for member, counterparty and administrator roles.
3. Run end-to-end tests in SOWIA TEST for listing submission, moderation, approved-only visibility, mission/deal transitions, proposal handling and audit events.
4. Compare the reviewed migration set with production and apply it only after explicit deployment approval and a verified backup/rollback plan.
5. Pilot non-monetary workflows first. Design and security-test atomic budget reservations and payment-provider confirmation before enabling any paid workflow.
6. Add localization, partner integrations and automation only after legal, privacy, security and operational review.
