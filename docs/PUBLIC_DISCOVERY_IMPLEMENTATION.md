# SOW IA — Public Discovery & Guided Onboarding Blueprint

## Current architecture finding
The Streamlit entry point enforces hosted authentication before rendering the authenticated workspace. When Supabase is configured and authentication is required, an unauthenticated visitor is shown the GitHub sign-in screen and execution stops. This is a useful security boundary for private workspace data, but it currently leaves no public product-tour surface in the same entry flow.

## Recommended safe architecture
Do not weaken or bypass the existing authentication gate. Introduce a public discovery surface as a separate, deliberately public route/application surface, while keeping the existing authenticated Streamlit workspace protected.

Preferred deployment shape:
- Public marketing/discovery site at the root domain (or a dedicated public subdomain).
- Existing authenticated Streamlit workspace at a clearly named application path/subdomain.
- Explicit links between the two surfaces.
- Supabase authentication remains mandatory for all private workspace operations.

If hosting constraints require a single Streamlit deployment, implement a strictly public landing state before private initialization, but only after a security review confirms that no private client, user data, storage operation, or privileged helper is initialized or rendered in that state. The authenticated code path must remain unchanged and fail closed.

## Public visitor experience
1. Full-width SOW IA identity artwork, preserving its entire aspect ratio (no crop or stretch).
2. Clear value proposition in French first, with language-ready structure for English and other target markets.
3. Short verified product walkthrough, with captions and mobile-friendly playback.
4. Audience entry points: Personal / Professional / Partners.
5. Feature directory with descriptions and availability/access labels verified against production.
6. Calls to action: “Explorer SOW IA” and “Créer un compte”.
7. Transparent information on account requirements, plans, privacy, and support.
8. Accessible design: keyboard navigation, readable contrast, alt text, reduced-motion support, and responsive layout.

## Guided onboarding inside the protected workspace
- First-visit tour is optional, dismissible, and replayable.
- Tour steps explain navigation, the assistant, document tools, history, and professional areas only when each feature is enabled for the current user.
- Do not expose restricted destinations or imply Premium access where the user lacks entitlement.
- Add a permanent “Découvrir SOW IA” help entry.
- Measure completion using minimal aggregate events; never collect prompt text, document contents, or private messages for marketing analytics.

## Analytics funnel
Use privacy-conscious aggregate events:
- public_landing_view
- public_demo_started / public_demo_completed
- signup_cta_clicked
- auth_started / auth_completed
- onboarding_started / onboarding_completed
- first_successful_tool_action (event name only; no content)
- return_visit
- referral_link_opened / referral_signup_completed

Define retention and conversion windows before launch. Provide a privacy notice, retention period, access controls, and consent behavior appropriate to the applicable law before enabling non-essential analytics.

## Acceptance criteria
- Public pages are accessible without authentication and contain no private data.
- Private workspace routes and data remain protected by the existing authentication and authorization controls.
- RLS and entitlement checks remain authoritative; front-end visibility is not an access control.
- Mobile and desktop layouts are tested.
- All public feature claims match the deployed product.
- Every CTA destination is tested.
- No tracking payload contains prompt text, PDF contents, user email, payment data, or other personal content.
- Existing login, OAuth callback, account isolation, and private document workflows pass regression tests.

## Delivery sequence
1. Decide the public-domain/hosting arrangement and identify the source of the complete approved visual mockup.
2. Build the public landing and feature directory separately from the protected app.
3. Add the optional onboarding tour to the authenticated workspace in a separate change.
4. Add privacy-reviewed funnel analytics.
5. Test and submit each change as an isolated pull request. No merge or deployment without explicit approval.

## Out of scope
- No changes to authentication policy, Supabase RLS, billing, PayPal, entitlements, or private workspace behavior in this blueprint.
- No claim that the public site, tour, or analytics have already been implemented.
