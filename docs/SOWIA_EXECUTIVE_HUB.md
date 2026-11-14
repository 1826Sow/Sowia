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

## Worldwide market expansion

The worldwide-development workspace includes a global market strategy panel. Initial focus markets explicitly include China, Singapore, Malaysia, Taiwan, South Korea, Senegal, the United Arab Emirates (with Dubai as a commercial hub), the Netherlands, Brazil, the Bahamas and Switzerland. English-speaking markets are also a dedicated segment. The country input remains open so the list does not restrict expansion to named markets.

The inclusion principle is to research emerging and lower-/middle-income economies as potential partner and customer markets, not exclude them based only on national income. Each market receives a research checklist for local partners, demand, regulation, privacy/data transfers, tax, payments, language, sanctions and intellectual property. The indicative market score is based on user-entered ratings, not automatically sourced economic statistics.

The feature prepares research and prospecting leads only. It does not automatically contact businesses, register companies, launch campaigns, or make legal determinations. Market coverage is a strategic objective; complete country-by-country localization and compliance verification remain ongoing work.


## Worldwide opportunity radar

The international-development workspace includes an on-demand public-signal radar. It searches separately for public tenders and procurement, innovation/funding programmes, partnerships/business expansions, and professional events/networks. Separate short queries respect the configured search provider's per-query limits.

Results are normalized, deduplicated by URL where available, and sorted by a transparent heuristic relevance score. The score is a triage aid only: every result remains labelled "À vérifier". The radar does not prove that a call is open, that SOWIA is eligible, or that a source is authoritative. Users must check the original source, deadlines, eligibility, budget, legal requirements and contact details.

The radar search itself is on-demand and does not run in the background or cover every country automatically. Saved findings can now be retained in the separate opportunity register described below. The radar does not contact organizations, submit applications, or spend money. Scheduled monitoring remains future work.


## Persistent opportunity register and deadline follow-up

The radar findings can be saved into a per-user, professional-workspace opportunity register. Records include country, category, source URL, summary, optional partner, deadline, priority, status and next action. Users can add opportunities manually, update progress and review overdue deadlines or deadlines within the next 14 days.

The Supabase migration is `supabase_opportunity_register.sql`. It creates user-scoped row-level security policies; records are isolated by authenticated user and professional workspace. Until the migration is applied, the UI may keep entries in Streamlit session state only, with an explicit warning that this is temporary.

Deadline indicators are shown when the user opens the application. They are not push notifications, emails or background monitoring. No opportunity is submitted and no partner is contacted automatically. The register currently supports up to 200 records per user view; a future stage can add pagination, reminders and partner CRM linking.

## Visual command center — November 2026

The Hub landing view now uses the approved midnight-blue and cyan visual identity and foregrounds the "Mes échanges & projets" entry point. It links to the existing conversation history, assistant, private document library, PDF analysis workspace and SOWIA NIGHT EXCHANGE. It also exposes the existing FINAL TEC protocol documentation.

The four project states (En cours, À tester, Validé, Terminé) are now supported by a persistent project register in `public.sowia_projects`. The register is scoped by authenticated user and workspace through RLS and application-level filters. Users can create projects, edit their title/description/status, associate a known conversation session ID, add deliverable references and archive projects without deleting them. The Hub exposes the dedicated `Mes échanges & projets` screen.

The project register does not automatically import all historical conversations or discover every file already stored by other modules. Conversation resumption works only when a project has a valid session ID associated with it. The deliverables index contains references entered into the register; it is not yet a complete cross-module file inventory. Apply `supabase/migrations/20261114000100_sowia_project_register.sql` before expecting persistent cloud storage.
