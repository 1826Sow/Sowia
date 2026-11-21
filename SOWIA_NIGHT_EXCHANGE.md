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
- `supabase_night_exchange_registry.sql` defines the application registry, row-level security, pending-by-default trigger and administrator review RPC. Apply and verify it in the target Supabase project before relying on registry persistence.
- `supabase_night_exchange_events.sql` defines the append-only event ledger and member insert restrictions. Apply it after the registry script and verify its policies.
- The application code calls additional RPCs for bilateral offers and integration review. Their database definitions and deployment state must be checked separately in the target Supabase project; the presence of client calls does not prove that those RPCs are installed.

### Not yet established as production capabilities
- No automatic night-session scheduler or background execution.
- No ownership/domain verification automation.
- No live paid marketplace, bidding, paid visibility placement or atomic budget reservation.
- No end-to-end payment/refund/chargeback workflow for NIGHT EXCHANGE.
- No proof that the SQL assets or the additional offer/integration RPCs have been applied to the production Supabase project unless a separate deployment check confirms it.

## Safe rollout
1. Verify the registry and event SQL assets in a non-production Supabase environment, including RLS tests for member, other-member and administrator roles.
2. Run end-to-end tests for listing submission, moderation, approved-only visibility, matching, event restrictions and bilateral offers.
3. Pilot non-monetary listings and proposals with manually reviewed applications.
4. Design and security-test atomic budget reservations and payment-provider confirmation before enabling any paid workflow.
5. Add localization, partner integrations and automation only after legal, privacy, security and operational review.
