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
The rules module provides pure helpers for timezone checks, app matching, budget-cap checks and deterministic offer selection. Tests are supplied. It is not wired into Streamlit or Supabase. No payment provider, scheduler, app-verification workflow, background execution or production budget enforcement is connected. Run the project test suite before deployment.


## Streamlit prototype
The professional navigation now includes a SOWIA NIGHT EXCHANGE page, gated by the existing Premium entitlement. It contains an overview, a session-only draft listing form with IANA timezone validation, a simple explainable category/service compatibility preview, and a local budget-cap configuration preview. Draft listings and budget settings are not persisted. The page does not publish apps, verify ownership, match against a live directory, create auctions, execute payments, or enforce production spending limits. The authoritative budget guard must be implemented server-side with atomic reservations before any paid workflow is enabled.


def test_night_exchange_listing_validation_accepts_global_timezone():
    from cloud_storage import _validate_night_exchange_listing
    listing = _validate_night_exchange_listing(
        "App partenaire", "Singapour", "Asia/Singapore",
        ["Productivité"], "API de traduction", "Paiements", "21:00", "05:00"
    )
    assert listing["timezone"] == "Asia/Singapore"
    assert listing["night_start"] == "21:00"
    assert listing["night_end"] == "05:00"


def test_night_exchange_listing_validation_rejects_unknown_timezone():
    from cloud_storage import _validate_night_exchange_listing
    with pytest.raises(ValueError):
        _validate_night_exchange_listing(
            "App partenaire", "France", "Mars/Imaginary", ["Productivité"]
        )


def test_night_exchange_listing_validation_requires_category():
    from cloud_storage import _validate_night_exchange_listing
    with pytest.raises(ValueError):
        _validate_night_exchange_listing(
            "App partenaire", "France", "Europe/Paris", []
        )
