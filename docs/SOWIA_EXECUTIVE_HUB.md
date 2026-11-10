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
