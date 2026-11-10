# SOW IA Executive Hub

## Purpose
The Hub is the platform's main entry point. It groups existing features without replacing their implementations.

## Areas
- Personal: assistant, private memory, documents and web research.
- Professional: Business Club, worldwide development, opportunities, finance, strategy and technology evaluation. Access remains gated by the existing active Premium entitlement.
- Administration: visible only when the authenticated user's server-controlled `app_metadata.sowia_admin` claim is exactly `true`. It links to existing administrative modules; it does not grant new permissions by itself.

## Navigation and security
- `Hub SOWIA` is the new landing page. The legacy `Accueil` entry remains available for session compatibility and routes to the same dashboard.
- Professional shortcuts switch the workspace selector to Professionnel before navigation.
- Existing workspace isolation and Premium authorization checks remain in force.
- The Hub does not expose account data across users or make any admin action available merely by hiding/showing a button. Sensitive actions continue to be authorized by their existing server/database checks.

## Current limits
- This is a navigation and dashboard consolidation, not a new billing, brokerage, partner marketplace or fulfilment integration.
- Admin links point to existing modules. New centralized role management and cross-module analytics are separate future work.

## Global pilotage overview

The professional Hub includes a six-pillar overview. It reports live counts only for the user/workspace-scoped CRM and decision-trial reads when those reads succeed. Unavailable reads are labelled unavailable, not zero. The other pillars explicitly state when centralized indicators or live providers are not connected. This is an operational overview, not a compliance audit or proof of business performance.

## Action prioritization engine

The Hub offers a session-scoped action comparison using explicit user-entered ratings:
- expected impact: 30%;
- urgency: 25%;
- feasibility: 20%;
- cost burden (inverted to cost efficiency): 15%;
- risk exposure (inverted to safety): 10%.

The engine scores each action from 0 to 100 and explains mandatory gates. A prohibited action is blocked; unverified compliance or high risk requires human review regardless of score. Ratings are not automatically discovered facts, and the engine does not execute tasks, make investments, send messages or spend money. The comparison currently lives only in the active Streamlit session; durable account-level storage is not yet connected.
