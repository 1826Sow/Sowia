# SOWIA NIGHT EXCHANGE

## Positioning
A timezone-aware night-session marketplace for digital applications and services. It combines app discovery, service exchange, integration opportunities, visibility placements, capped paid offers and collaboration matching. It is not a securities exchange and issues no tradable financial instruments.

## Six spaces
1. Application directory: profiles, capabilities, countries, languages, integration requirements and verification.
2. Service exchange: reciprocal offers and requests with explicit scope, deliverables, expiry and approval by both parties.
3. Paid services and visibility: priced offers, time slots and capped bids; no hidden bidding or guaranteed placement.
4. Night sessions: IANA time zones, default local window 20:00–06:00, configurable per market; show local time and UTC.
5. SOWIA matching: explainable compatibility signals, not endorsements.
6. Morning report: session outcomes, provider-confirmed spend, offers, matches and pending approvals.

## Budget controls
Each app sets daily, weekly and monthly caps. A trusted backend must reserve budgets atomically before a paid action. Stop spending when any cap is reached or payment status is uncertain. No payment, bid, subscription, integration, data transfer or campaign activates without explicit administrator approval. Itemize fees, taxes, currency conversion, refunds and chargebacks. Client-side checks alone are never sufficient.

## Trust and privacy
Verify app ownership and domain control. Review permissions before listing. Use least-privilege API scopes, signed webhooks, secret rotation and tenant isolation. Explain what data is shared, with whom, why and for how long; obtain consent. Add security review, reporting, suspension, appeal and audit logs. Do not bypass logins or platform terms.

## Operational sequence
1. App submits listing and ownership proof.
2. SOWIA reviews security, privacy, legal and technical fit.
3. Approved app configures markets, night windows, caps and allowed actions.
4. Marketplace presents compatible exchanges and paid-service offers.
5. Both sides approve scope and terms.
6. Backend reserves budget atomically; payment provider confirms the charge.
7. SOWIA records the outcome and issues the morning report.
8. Parties rate delivery or open a dispute.

## Rollout
Phase 0: concept, rules, threat model and UX.
Phase 1: closed pilot, manually verified apps, non-monetary matching and exchanges.
Phase 2: limited paid services with payment provider, atomic reservations, refunds and audit logs.
Phase 3: regional sessions, localization and partner integrations.
Phase 4: automated monitoring after legal, privacy, security and operational review.

## Current implementation boundary
The rules module provides pure helpers for timezone checks, app matching, budget-cap checks and deterministic offer selection. The Supabase migration `supabase_night_exchange_registry.sql` defines a draft-first partner app registry with row-level security; `cloud_storage.py` contains user-scoped create/list helpers. The migration is committed but must still be applied in the Supabase SQL Editor. The Streamlit listing form is still session-only and is not yet connected to these persistence functions. No live directory, admin moderation screen, payment provider, scheduler, background execution or production budget enforcement is connected. Tests are supplied but have not been executed in this work session. Run the project test suite and apply the migration before enabling persistence.


## Streamlit prototype
The professional navigation now includes a SOWIA NIGHT EXCHANGE page, gated by the existing Premium entitlement. It contains an overview, a session-only draft listing form with IANA timezone validation, a simple explainable category/service compatibility preview, and a local budget-cap configuration preview. Draft listings and budget settings are not persisted. The page does not publish apps, verify ownership, match against a live directory, create auctions, execute payments, or enforce production spending limits. The authoritative budget guard must be implemented server-side with atomic reservations before any paid workflow is enabled.


## Matching international — prototype
The Streamlit page includes an explainable matching tab. It compares a member listing with approved directory records using normalized categories and service terms, ranks candidates deterministically, and labels reciprocal exchange potential. It is advisory only: no messaging, integration, data sharing, or payment is initiated. Matching quality depends on the accuracy and specificity of submitted descriptions.


## Global coordination prototype (current code)
The rules module now includes:
- `global_session_status(record, now)`: converts an aware timestamp into each approved app's IANA timezone, checks its configured local night window and calculates its next opening in local time and UTC. It does not run a scheduler or start a session.
- `build_smart_opportunities(source, candidates)`: provides an explainable compatibility ranking with shared categories and reciprocal service signals. Scores are heuristic indicators, not forecasts or endorsements.
- `build_morning_report(events)`: summarizes only explicitly supplied event records and includes payment spend only when the provider status is `confirmed`.

The Streamlit page adds a global session table, an explainable opportunities view and a morning-report placeholder. The report event ledger is not yet connected to Supabase, so the UI intentionally does not display fabricated session counts or spending. The SQL registry migration still needs to be applied in Supabase. Automated tests have been added but have not yet been executed; production deployment has not been verified.


## Append-only activity ledger
The migration `supabase_night_exchange_events.sql` creates a user-scoped event ledger:
- Members can append only non-financial events for their own workspace and app listing.
- Members can read only their own events; the table has no client UPDATE or DELETE policy.
- Authenticated clients cannot insert `payment_confirmed`. That event type is reserved for trusted server-side payment webhooks/service-role processes.
- The Morning Report reads the current member's last seven days of events. Currency totals are kept separate; no conversion or estimate is performed.
- The UI lets a member explicitly record a meeting confirmation. This is a member declaration, not proof that a meeting took place.

Apply `supabase_night_exchange_events.sql` after the app registry migration in the Supabase SQL Editor. The new ledger is not operational until both migrations have been applied to the connected Supabase project. No live payment webhook has been connected in this implementation.

## Activity journal — explicit matching analysis
The Smart Opportunities view now offers a deliberate “Enregistrer cette analyse dans mon journal” action. It appends a `match_viewed` event scoped to the signed-in member and active workspace, with the source app and result count. Merely opening or refreshing the page does not create repeated events. The event is visible in the seven-day Morning Report. The separate meeting button remains a member declaration, not independent verification.

## SOWIA TRUST & PARTNER SCORE — evidence-based first version
The Smart Opportunities view now displays an explainable documentary-evidence index. It scores only facts present in the listing: SOWIA approval (30), dated verification (30), name (5), country (5), timezone (5), categories (5), services offered (10) and services wanted (10). The UI exposes passed and missing checks. This is a profile-completeness and verification index, not a commercial trust rating. It does not infer solvency, delivery quality, contract compliance, complaints or partner satisfaction. Those dimensions require separately designed, privacy-safe, auditable bilateral feedback and dispute workflows before they can be scored.

## SOWIA PARTNER REPUTATION — rules prototype
A separate module `sowia_partner_reputation.py` defines structured feedback rules for a future reputation workflow:
- Feedback is eligible only after both parties confirm collaboration completion.
- Three independent dimensions are rated from 1 to 5: delivery, communication and respect of agreed scope.
- Optional comments are limited to 500 characters.
- New feedback is private and pending moderation; it is not immediately public.
- Public aggregate statistics are suppressed until at least three approved reviews exist.
- Pending, rejected, malformed or unconfirmed feedback is excluded from aggregates.
- The module does not store reviews, identify participants, prove that a collaboration occurred, or connect to the Streamlit interface yet. A secure collaboration record, bilateral completion flow, database RLS, moderation and appeal process are required before collecting or publishing real reviews.

## SOWIA PARTNER CONTRACT — workflow prototype
The separate `sowia_partner_contract.py` module defines a bilateral agreement workflow:
- A proposal records the two distinct parties, title, scope, deliverables and target date; optional financial terms require both amount and three-letter currency code.
- Only the invited counterparty can accept the proposal. Acceptance locks the agreed terms in the workflow model.
- Either party may start an accepted agreement.
- Completion is reached only after both parties confirm it.
- Either party may raise a dispute while the agreement is active; the dispute reason is excluded from the public status summary.
- The public status helper does not expose the amount or private dispute details.

**Important implementation boundary:** this is a pure Python rules prototype. It is not an electronic signature, enforceable legal contract, identity verification, escrow, payment processor or persistent database workflow. Before production use, SOWIA needs authenticated party-to-app ownership mapping, server-side authorization, append-only contract version history, secure Supabase RLS/RPC, audit timestamps, notifications, moderation/mediation and jurisdiction-specific legal review. No live contract is currently created or signed through the app.

## SOWIA PARTNER PROTECTION — conservative prototype
The separate `sowia_partner_protection.py` module adds:
- Explainable listing completeness signals (missing official website/contact, unapproved or unverified profile, missing basic information). These are review prompts, never fraud findings.
- Confidential abuse-report validation with a controlled category list and bounded description length.
- Human moderation outcomes with a named reviewer and written rationale.
- A safe public status projection that never exposes the reporter identity or allegation details.

No signal automatically blocks, suspends, labels or penalizes an application. Production deployment still requires verified user-to-app ownership, secure report storage and RLS, moderator authorization, evidence handling, retention/deletion policy, anti-retaliation controls, appeal workflow, and legal/privacy review. The current module does not verify real-world identity or investigate allegations.


## SOWIA GLOBAL ID — privacy-first profile prototype
The standalone `sowia_global_id.py` module adds:
- A deterministic public alias derived from a trusted persistent UUID; email addresses, names and raw internal UUIDs are not used as public identifiers.
- An explainable six-point profile-completeness indicator.
- A strict public-profile allowlist that excludes account IDs, email addresses, phone numbers and other unapproved fields.
- Verification states (`unverified`, `pending`, `verified`, `suspended)); only an explicitly authorized admin role can change them, and a documented evidence reference is mandatory for `verified`.
- A stable HTTPS profile URL payload suitable for a future QR code. The module returns the URL only; it does not render a QR image.

**Important implementation boundary:** this is a pure Python prototype. A public ID is an alias, not proof of legal identity, domain ownership or account control. The admin-role argument is not a substitute for server-side authentication and authorization. Before production, SOWIA needs a persistent profile table with a unique public ID, authenticated owner mapping, admin-only server-side RPC, auditable evidence records, RLS, consent and profile visibility settings, data-retention/deletion rules, and an actual HTTPS profile route. The profile URL domain is not yet deployed. The interface, database and QR rendering are not connected. Tests have been added but not executed.


## SOWIA GLOBAL ID — Supabase registry and first interface
The migration `supabase_global_id.sql` defines one profile per authenticated account, generates a stable public alias from the account UUID, and keeps the source account ID private. Owner reads/writes are restricted by RLS. A separate allowlisted public view exposes only explicitly published card fields; it omits account identifiers and verification evidence. A signed-admin RPC controls verification states and requires an evidence reference for `verified`. The trigger prevents members from changing their own identifier or verification status.

The Streamlit navigation now includes a GLOBAL ID page with a profile editor, private-by-default publication checkbox, completeness indicator, card preview, published-card directory, and an administrator review panel. The card preview is available after applying the migration. No public profile URL route or QR image is deployed yet, so the interface deliberately does not display a fabricated QR or non-functional share link.

**Activation steps:** apply `supabase_global_id.sql` in the connected Supabase project's SQL Editor, then reload the app and create a profile. This migration has only been committed to GitHub; it has not been applied to Supabase. The app deployment and database behavior have not been verified in production. Tests have been added but not executed.


## SOWIA DIGITAL BUSINESS CARD
The `sowia_business_card.py` module creates a landscape PNG card, a printable PDF and a vCard contact file. The QR code embeds the vCard data so a phone can offer to save the contact; it does not point to a nonexistent public profile route. The Streamlit GLOBAL ID page provides optional email/phone fields for the export only; those contact fields are not written to the profile database. The existing profile remains private by default, and the card export is a local download initiated by the signed-in user.

**Limitations:** the QR encodes the contact details supplied at export time, not a live SOWIA profile URL. No public profile page, automatic sharing, or contact synchronization is implemented. Users should only include email/phone details they consent to share. Tests are added but not yet run in a confirmed CI result.


## SOWIA GLOBAL DIRECTORY — international professional search

The dedicated GLOBAL DIRECTORY page searches only the authenticated public view of GLOBAL ID profiles. Members can filter by country, language, professional sector, specialty and free text. Public profiles may optionally list up to 14 controlled sectors and 12 short specialties. The directory presents only profiles explicitly published by their owner and excludes suspended profiles. It does not expose account IDs, email addresses, phone numbers or verification evidence. A verified label means a documented SOWIA profile check, not a guarantee of business performance or financial reliability.

The migration `supabase_global_directory.sql` adds the sector and specialty fields, database constraints, lookup indexes and the allowlisted public view fields. Apply it only AFTER `supabase_global_id.sql`. The migration is committed to GitHub but has not been applied to Supabase in this work session. The directory requires an authenticated session and the GLOBAL ID migrations; it has not yet been verified against the live database or Streamlit deployment.


## SOWIA GLOBAL CONNECT — consent-based professional introductions

GLOBAL CONNECT lets a member with a published GLOBAL ID profile send a 10–1,000 character introduction to another published profile. The recipient can accept or decline; the sender can cancel while pending. Requests are private to their two participants under Supabase RLS. No email address, phone number, private account identifier or external contact channel is revealed automatically. Acceptance records consent to connect inside SOWIA; it does not itself transmit contact details or authorize data sharing.

Apply `supabase_global_connect.sql` AFTER `supabase_global_id.sql` and `supabase_global_directory.sql`. The migration creates the private request ledger and authenticated RPCs for sending, responding and cancelling. The app UI includes incoming and outgoing request lists. This code is committed to GitHub; the migration has not been applied to the live Supabase project and the workflow has not yet been verified in the deployed Streamlit app. Production readiness still requires live two-account RLS and RPC tests.

## SOWIA GLOBAL MESSENGER — private messaging after consent

The GLOBAL DIRECTORY workflow now includes an initial in-app messenger linked to GLOBAL CONNECT:
- A conversation is available only when the related connection request has been accepted.
- Messages are limited to 4,000 characters and trimmed before submission.
- Sending is performed through a SECURITY DEFINER RPC that checks the authenticated participant and accepted request status; direct client inserts are revoked.
- Members can read only messages belonging to a connection in which they participate. Messages are append-only from the client: no update or delete policy is provided.
- A database-side rate limit currently caps each sender at 20 messages per minute.
- The Streamlit interface shows accepted conversations and allows participants to exchange messages without automatically revealing email addresses or phone numbers.

Apply `supabase_global_messenger.sql` AFTER `supabase_global_connect.sql`. The required migration order is GLOBAL ID, GLOBAL DIRECTORY, GLOBAL CONNECT, then GLOBAL MESSENGER. All migrations are committed to GitHub; none is confirmed applied to the live Supabase database in this work session. The interface and database workflow have not yet been verified in the deployed Streamlit app. Before production use, run two-account authorization tests, abuse/reporting and retention reviews, and security review. The current rate limit is a basic technical safeguard, not a complete anti-spam or moderation system.

## SOWIA GLOBAL NOTIFICATIONS — multilingual in-app alerts

The first notification center records four event types: received GLOBAL CONNECT request, accepted or declined request, and new GLOBAL MESSENGER message. Database triggers create alerts automatically. Each member can select French, English, Spanish, Portuguese, Chinese or Arabic, enable or disable in-app alerts, mark one alert read or mark all read. The UI translates event labels locally; stored records contain only the event type, reference UUID and timestamps, not message bodies or contact details.

The notification inbox is private to its owner under RLS. Clients cannot insert or modify notification records directly; read-state changes and preference updates use authenticated server-side RPCs. Disabling in-app alerts prevents new alerts from being recorded while disabled. This first version is in-app only: it does not send email, SMS, browser push or mobile push. The supported languages apply to notification labels, not yet to all SOWIA interface content.

Apply `supabase_global_notifications.sql` AFTER `supabase_global_messenger.sql`. The full database migration order is GLOBAL ID, GLOBAL DIRECTORY, GLOBAL CONNECT, GLOBAL MESSENGER, then GLOBAL NOTIFICATIONS. The migration and application code are committed to GitHub; the migration is not confirmed applied to the live Supabase project. Automated checks and live two-account authorization tests remain to be verified before production use.

## SOWIA GLOBAL TRUST — collaboration feedback and confidential safety reports

GLOBAL TRUST adds a separate reputation and safety layer for members who have an accepted GLOBAL CONNECT relationship. Each participant may submit one 1–5 rating per accepted connection. Public profiles expose only the aggregate average and review count; individual reviewer identities and comments are not public. This first release intentionally has no public free-text reviews, reducing the risk of defamatory or personally identifying content.

Participants can also submit a confidential 10–2,000 character report about the other party in an accepted connection. Reports are visible only to SOWIA administrators through the database policy; a dedicated moderation dashboard and response workflow still need to be built. A rating is a subjective account of one collaboration and must not be presented as proof of identity, solvency, legality or overall business reliability. GLOBAL ID verification remains a separate evidence-based process.

Apply `supabase_global_trust.sql` AFTER `supabase_global_notifications.sql`. The full sequence is GLOBAL ID, GLOBAL DIRECTORY, GLOBAL CONNECT, GLOBAL MESSENGER, GLOBAL NOTIFICATIONS, then GLOBAL TRUST. Code and migration are committed to GitHub; the migration is not confirmed applied to the live Supabase project. The new page and database permissions have not yet been verified in the deployed app or with two real accounts.

## SOWIA GLOBAL ADMIN & MODERATION — restricted control center

The admin-only workspace provides three views: confidential GLOBAL TRUST reports, GLOBAL ID profile verification/suspension, and an audit history of moderation decisions. Report statuses are open, reviewing, resolved or dismissed. Profile statuses are unverified, pending, verified or suspended. A verified profile requires a documented evidence reference; suspending a profile also removes it from publication. Do not store identity-document images or sensitive evidence in internal notes: the evidence review process must use an appropriately secured channel.

All privileged mutations are performed by SECURITY DEFINER database RPCs that check the authenticated JWT app metadata for `sowia_admin=true` or `role=admin`. The UI check is only a usability guard; database authorization is authoritative. The audit table is readable only by administrators and records the actor, action, subject, status transition, note and timestamp. This MVP does not yet include automated fraud detection, appeal handling, SLA workflows, or a separate encrypted evidence vault.

Apply `supabase_global_moderation.sql` AFTER `supabase_global_trust.sql`. Full order: GLOBAL ID, GLOBAL DIRECTORY, GLOBAL CONNECT, GLOBAL MESSENGER, GLOBAL NOTIFICATIONS, GLOBAL TRUST, then GLOBAL MODERATION. The code and migration are committed; live Supabase application, real-admin authorization, and two-account isolation have not been verified.

## SOWIA GLOBAL INTELLIGENCE — private market assessment workspace

GLOBAL INTELLIGENCE provides a user-owned register of country/sector opportunities. Each assessment uses six weighted criteria: market demand (25%), strategic fit (20%), accessibility (15%), partner readiness (15%), regulatory readiness (15%), and evidence quality (10%). The resulting score is normalized to 0–100. Users classify the evidence as hypothesis, indicative, documented or verified and may preserve source notes. The interface compares saved assessments and supports deletion.

Scores are subjective decision-support inputs, not automatically gathered market statistics. The word "verified" is an evidence label selected by the user, not a SOWIA certification. The MVP does not crawl markets, independently verify sources, predict revenue, or provide legal/financial advice. Each assessment is private to its owner under Supabase RLS; no global ranking of users or companies is exposed.

Apply `supabase_global_intelligence.sql` AFTER `supabase_global_moderation.sql`. Full migration order now ends with GLOBAL TRUST, GLOBAL MODERATION, then GLOBAL INTELLIGENCE. Code and tests are committed to GitHub; the migration is not confirmed applied to the live Supabase project, and automated tests/deployment remain to be verified.



## SOWIA GLOBAL PULSE — on-demand international monitoring
The first version provides a user-triggered search across public web sources for a selected country/market, sector, topic and signal category (economy, technology, trade, regulation, competition or other). Results are normalized, deduplicated by URL, labeled according to the date/source metadata supplied by the search provider, and can be saved to a private account-scoped register. Users can open the original source or delete a saved item.

This is an on-demand research tool, not continuous background monitoring: it does not run a scheduler, poll sources, send push/email notifications or guarantee complete coverage. Search-provider results and publication dates must be independently checked before decisions. Apply `supabase_global_pulse.sql` after the existing GLOBAL INTELLIGENCE migration. The SQL migration is committed but has not been applied to the live Supabase project; production behavior and RLS are not yet verified.


## SOWIA GLOBAL ALERTS — priority queue for public signals
GLOBAL ALERTS converts a user-selected GLOBAL PULSE result into a private alert. The first classifier is deterministic and keyword-based: it suggests critical, high, medium or low priority and records the exact matched terms as its explanation. The user can review the original source, acknowledge the alert, close it or delete it. The classifier is a triage aid only; it does not establish the truth, severity or business impact of an event and must not trigger automatic decisions.

Apply `supabase_global_alerts.sql` after `supabase_global_pulse.sql`. Both migrations are committed but have not been applied to the live Supabase project. Background monitoring, push/email delivery, automatic escalation and independent fact verification are not implemented in this version.
