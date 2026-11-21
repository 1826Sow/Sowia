# SOW IA NIGHT EXCHANGE — Application Economy Protocol

**Status:** architecture proposal for the next implementation milestone.  
**Implemented today:** isolated in-memory matching/proposal primitives and a read-only partner-discovery preview.  
**Not implemented:** persisted order book, live application-to-application messaging, automatic execution, or money movement.

## 1. Product principle

In NIGHT EXCHANGE, software applications are the economic participants. Each application has a verifiable identity, a human owner, declared capabilities, services it can provide, services it needs, and a permission envelope. Applications may discover compatible counterparties and prepare proposals. The owner remains the authority for identity, permissions, budgets, integrations, and any binding commitment.

This is an economy **between applications**, not a stock exchange and not a marketplace for selling shares in applications.

## 2. Proposed domain objects

| Object | Purpose | Required controls |
|---|---|---|
| Application identity | Stable app ID, owner, display name, publisher and verification state | Owner-scoped writes; moderation; immutable identity key |
| Capability declaration | Machine-readable service offered or required, version and interface contract | Explicit scope; schema validation; no arbitrary code |
| Service order | Offer or request, quantity, unit, currency, price ceiling/floor, expiry | Owner authorization; bounded values; cancellable while open |
| Match | Compatibility result between an offer and a request | Deterministic rules; explainable reasons; no commitment |
| Exchange proposal | Terms presented to both application owners | Both sides approve the same immutable terms/version |
| Permission grant | Allowed operation, target, budget, rate and expiry | Least privilege; revocable; default deny |
| Audit event | Append-only record of state transitions and approvals | Server-authenticated actor; idempotency key; no client-forged payment event |

## 3. Proposed lifecycle

1. An owner registers an application and declares its capabilities.
2. Moderation and verification approve the public listing.
3. The owner explicitly enables selected services and defines limits.
4. The application publishes a service offer or request within those limits.
5. The matching engine discovers candidates and explains why they match.
6. A proposal is created with a fixed terms hash, expiry, currency and quantity.
7. Each owner approves the exact same proposal version. Any terms change invalidates prior approvals.
8. Only after both approvals may an authorized adapter perform a permitted non-financial service action.
9. The result is recorded in an append-only audit trail. Owners can revoke permissions or suspend an application at any time.

A match is never an acceptance. A proposal is never an execution. An approval is never proof of successful delivery.

## 4. Security and trust boundaries

- **Default deny:** no capability, integration, budget or execution permission exists unless explicitly granted.
- **Human ownership:** an application cannot grant itself permissions or increase its own budget.
- **Bilateral consent:** both owners approve the same immutable terms hash; approval is invalidated by any change.
- **Least privilege:** grants are scoped to one service, counterparty, action, budget, rate and expiry.
- **Revocation:** owner revocation, application suspension and a platform kill switch block new work immediately.
- **Idempotency:** state-changing requests carry unique idempotency keys; replayed requests cannot duplicate an action.
- **Auditability:** append-only events record actor, application, proposal version, authorization and outcome. Client users cannot forge trusted server events.
- **Isolation:** RLS enforces owner access; public discovery exposes only moderated fields of approved applications.
- **No secrets in app metadata:** credentials remain in server-side secret storage and are never returned to other applications.

## 5. Money and regulated activity

The initial implementation must remain simulation-first and support non-financial service exchanges only. No autonomous payment, wallet, custody, credit, securities, or regulated financial operation is enabled by this design.

Any future payment support requires a separate reviewed integration, provider-side authorization, server-side verification/webhooks, idempotent settlement handling, fraud controls, refund/dispute handling, and jurisdiction-specific legal review. A browser/client event must never be accepted as proof of payment.

## 6. Persistence design — before migration

The existing repository already contains the SOW IA NIGHT EXCHANGE application registry and event ledger. These must be extended only after reviewing their live schema, policies, triggers, RPCs, and the current cloud storage call contracts.

Do not create duplicate application registries or event ledgers. The next schema review should determine whether separate tables are needed for service orders, proposals, permission grants and proposal approvals, and how they reference the existing app registry and audit events.

Any SQL migration must be additive, have explicit RLS policies and grants, include rollback notes, and be tested against a disposable Supabase project before anyone applies it to the production project. No migration is authorized by this document.

## 7. Acceptance criteria for the next milestone

- Existing catalogue, NIGHT EXCHANGE workflows, authentication and other SOW IA features remain unchanged.
- Only approved, enabled applications are discoverable.
- An application cannot match with itself.
- Service identifiers, versions, units and currencies are validated.
- Proposal approvals are bilateral and bound to an immutable terms hash.
- Owner permissions, budgets, expiry and revocation are checked server-side at execution time.
- Duplicate/replayed requests do not create duplicate proposals or actions.
- Every transition has an auditable event; payment events can only originate from a trusted server integration.
- Automated tests cover authorization failures, RLS boundaries, races, replay, revocation and budget limits.
- No real money moves in the initial milestone.

---

This document describes the intended architecture. It does not claim that the proposed persistence, bilateral approval workflow, autonomous agents, or execution adapters exist today.


## 8. Product vision — a trusted network of collaborating applications

NIGHT EXCHANGE is intended to become a **service economy between applications and AI agents**. It is not an exchange for shares in software companies and it is not an unrestricted autonomous-agent network.

### 8.1 Initial service families

The catalogue may progressively support these service families, subject to moderation and capability verification:

- **AI and automation:** research, summarization, translation, classification and bounded workflow automation.
- **Software and technology:** API integration, software development, testing, maintenance and technical support.
- **Marketing and commerce:** campaign production, content operations, catalogue enrichment and performance analysis.
- **Creative production:** graphic design, image and video production, and other rights-cleared creative services.
- **Business operations:** document processing, reporting, invoicing support and administrative workflows.
- **Data and analytics:** data cleaning, dashboards, statistical analysis and reporting.

Financial, payment, custody, credit, investment and other regulated services are excluded from the initial operating scope. A service label alone never grants permission to access data or execute an action.

### 8.2 Standard collaboration journey

1. **Discover:** an owner browses verified applications and their declared capabilities.
2. **Describe a need:** the owner defines the task, expected deliverable, constraints, deadline and budget ceiling.
3. **Compare:** NIGHT EXCHANGE ranks compatible providers and explains each match; it does not accept an offer.
4. **Propose:** the parties receive the same versioned proposal, including scope, price, data access, duration and cancellation terms.
5. **Approve:** each application owner explicitly approves that exact proposal version. A changed term invalidates previous approvals.
6. **Authorize:** narrowly scoped, time-limited permissions are issued for the approved task only.
7. **Deliver:** an approved connector performs only the permitted operation; the task can be stopped or revoked.
8. **Validate:** the requester reviews the deliverable against agreed acceptance criteria.
9. **Close and review:** the outcome, approvals, revocations and disputes are recorded for both owners.

A provider must never be able to approve its own proposal on behalf of the requester. No match, recommendation, message or proposal is itself an authorization.

### 8.3 Trust and control model

- Verified application identity and accountable human owner.
- Moderated public profile; private credentials and customer data are never exposed in discovery.
- Explicit consent before sharing task data with another application.
- Least-privilege permissions, with target, action, data scope, budget, rate and expiry.
- Separate approval for sensitive data, external publication, account changes and any financial operation.
- Immutable proposal version/hash and bilateral approval bound to that version.
- Server-side authorization on every state-changing operation; never trust a client-side success message.
- Idempotency, replay protection, rate limits, abuse detection and a platform-wide emergency stop.
- Append-only audit trail, clear cancellation, incident reporting and dispute handling.
- Owner-controlled suspension and immediate permission revocation.

### 8.4 Delivery roadmap and release gates

**Phase A — Catalogue and discovery (safe foundation).** Improve service taxonomy, capability schemas, provider verification, search filters and explainable read-only matching. No external execution and no money movement.

**Phase B — Orders and proposals.** Add persistent, owner-scoped service requests and offers; immutable proposal versions; expiry and cancellation; bilateral approval records. Requires schema review, additive migration design, RLS review and tests in a disposable Supabase project before production consideration.

**Phase C — Controlled non-financial delivery.** Introduce a small allowlist of reviewed connectors and sandboxed tasks. Enforce per-task permissions, data minimization, quotas, timeouts, revocation, idempotency and server-authenticated audit events. Begin with low-risk tasks and explicit human confirmation.

**Phase D — Quality, reputation and disputes.** Add evidence-based delivery reviews, service-level indicators, complaint handling, moderation and abuse response. Reputation must distinguish verified delivery from unverified claims and must provide an appeal path.

**Phase E — Optional payment integration (separate authorization).** Consider only after legal and security review, provider approval, server-side webhook verification, refunds, disputes, fraud controls and reconciliation are designed and tested. This phase is not part of the initial launch and must not be activated by a documentation or catalogue change.

### 8.5 Measures of quality

Track, at minimum: verified-provider coverage; match relevance; proposal acceptance and expiry rates; delivery success against agreed criteria; median completion time; cancellation and dispute rates; permission-denial and revocation events; replay/duplicate prevention; security incidents; and owner satisfaction. Metrics must not reward unsafe automation or unnecessary data collection.

### 8.6 Current implementation boundary

This section records the approved product direction, not a claim of deployed functionality. The current code remains limited to in-memory matching/proposal primitives and read-only discovery. The phases above require separate implementation, tests and release approval. Existing SOW IA functionality, secrets and Supabase configuration must remain untouched unless a specific change is separately authorized.


## 9. Phase A implementation notes — partner discovery hardening

The current read-only discovery path now applies these additional safeguards:

- A candidate must explicitly carry the `approved` moderation status; missing or unknown status fails closed.
- A candidate explicitly marked disabled is excluded.
- Declared services may be supplied as comma/semicolon-separated text or as a list; matching remains exact after whitespace normalization and case folding.
- Results include the exact matched service and a human-readable reason for the match.
- Moderation approval is not presented as independent identity verification. Unless a separate verified state is actually supplied, the result explicitly says that independent verification is unconfirmed.
- The approved directory query includes the moderation status needed by the discovery gate.
- The SOW IA discovery panel displays the matched service, why the partner appeared, and the verification caveat.

These changes remain read-only. They do not contact partner applications, publish orders, share user documents, authorize integrations, execute tasks or initiate payments. Automated CI status for this latest change has not yet been reported; the implementation must be treated as pending test validation until the repository checks complete.


## 10. Phase A — shared skill vocabulary

The first versioned skill vocabulary is `1.0.0`. It defines canonical identifiers, French display labels, domain categories, aliases and a risk tier for a deliberately limited set of common capabilities. Matching resolves known aliases to the same canonical skill identifier; unknown custom services are matched only by exact normalized text and are never guessed into a category.

Every catalogue entry requires human approval before any future execution. The initial catalogue excludes regulated or high-risk financial services such as payment processing, money transfers, custody, lending, investment advice, securities trading and gambling. The catalogue is a code-level, read-only vocabulary at this stage; it does not change database schemas or grant a capability to any application. The partner results show the normalized skill and its declared control tier when a known skill is matched.


The discovery matcher also rejects explicitly restricted service labels rather than allowing them to fall through as exact custom services. This prevents excluded payment, money-transfer, custody, lending, investment-advice, securities-trading and gambling labels from entering the initial partner matching flow.


## 11. Anti-malicious application admission policy

NIGHT EXCHANGE must not admit an application into partner discovery solely because a profile exists or a moderator marked its listing approved. The admission policy is fail-closed and requires all of the following independent evidence:

1. Listing moderation approval.
2. Verified identity of the accountable owner or publisher.
3. Verified control of the submitted application and its declared publisher identity.
4. A passed security review of the application package, permissions and declared endpoints.
5. A verified publisher signature and integrity check for the submitted build.
6. The application is enabled and not security-suspended.

Missing, unknown, expired or failed evidence means the application is excluded from discovery. A security suspension immediately makes it ineligible. Re-verification is required after a material application update or a change in publisher identity, signing key or requested permissions.

The admission evaluator added to the code is a fail-closed policy gate only. It does not itself verify a real-world identity, inspect binaries, validate a cryptographic signature, scan for malware or prove runtime safety. Those checks require a trusted onboarding service, isolated package-analysis infrastructure, a controlled signing/attestation process, server-side enforcement and operational security review. Until those systems exist and their evidence is stored and independently verified, applications cannot be represented as security-cleared. This is intentionally safer than trusting self-declared metadata.

Additional planned controls before any connector execution: sandboxing, strict network egress allowlists, least-privilege short-lived credentials, per-task scopes, secret isolation, runtime monitoring, revocation, incident response and a platform-wide kill switch. No connector execution or payments are enabled by this policy change.

## 12. Go-to-market strategy — earn market share through measurable value

The commercial objective is for SOW IA to become a leading, trusted provider inside NIGHT EXCHANGE, while the platform itself earns sustainable revenue. Market share must be earned through completed, accepted outcomes—not inflated profile counts, artificial rankings, spam or self-awarded reviews.

### 12.1 Win a focused initial segment

Start with a narrow set of low-risk, demonstrable services where SOW IA can deliver repeatable value:
- document and PDF analysis with clear source references and privacy boundaries;
- research, summarization and multilingual translation;
- structured reports, data transformation and workflow assistance;
- software testing and bounded technical support only when a reviewed connector and safe execution environment exist.

Do not advertise a service as available until its implementation, permissions, quality checks and delivery path have been verified. Keep high-risk and regulated financial services out of the initial marketplace.

### 12.2 Build a defensible provider profile

SOW IA's public provider profile should show verified capabilities, service scope, sample deliverables that contain no customer data, transparent indicative pricing, availability, supported languages, response targets and explicit limitations. Every claim must be backed by evidence. Security verification must be independent; paid placement must never look like a security certification.

### 12.3 Compete on outcomes and trust

Rank providers primarily on relevance to the request, verified delivery quality, on-time completion, repeat-client satisfaction, transparent pricing and security posture. Explain ranking factors. Prevent review manipulation, duplicate accounts, fake orders and retaliation; provide dispute and appeal processes. Clearly disclose when SOW IA is both marketplace operator and a competing service provider, and keep ranking and fee rules auditable.

### 12.4 Revenue model — transparent and staged

Potential revenue streams, each requiring separate implementation and authorization:
- fees for SOW IA services actually delivered and accepted;
- a clearly disclosed marketplace commission on completed paid transactions;
- optional professional subscriptions for additional platform capabilities;
- metered API access to verified SOW IA capabilities.

Never charge for a security pass, never sell access to private customer data, and never collect a commission on a merely proposed or failed mission. Fees, taxes, refunds, disputes and settlement rules must be disclosed before acceptance. Payment processing remains disabled until the separate legal, provider, security and reconciliation gates in Phase E are satisfied.

### 12.5 Market-share scorecard

Establish a baseline before claiming market share. Track:
- qualified requests received and share of eligible requests won by SOW IA;
- completed and requester-accepted missions, plus repeat-client rate;
- delivery quality, on-time rate, cancellation and dispute rates;
- net revenue and contribution margin per completed mission, once payments are legitimately enabled;
- customer acquisition source, conversion and retention;
- verified competitor coverage and match relevance across each service category.

Do not publish a market-share percentage until the denominator, geography, time window and eligible service category are defined and supported by reliable marketplace data. Optimize for retained, profitable customers and safe delivery—not raw transaction volume.

### 12.6 Rollout gates

1. **Prepare:** define SOW IA's genuinely available services, evidence, pricing logic and quality criteria.
2. **Prove demand:** use read-only discovery and owner-approved pilot requests; do not imply that a real paid marketplace is live.
3. **Prove delivery:** run controlled, non-financial pilots only after the relevant identity, security, permissions and sandbox controls exist.
4. **Prove economics:** measure acquisition cost, delivery cost, repeat use and contribution margin before scaling.
5. **Monetize carefully:** activate commissions, subscriptions or API billing only through separately reviewed, authorized and tested implementations.

This is a product and commercial strategy, not a claim that these capabilities, payments, customer demand or revenue are currently live.

## 13. Commercial mission lifecycle — domain prototype

A first pure-Python domain module now defines a bounded, non-financial mission lifecycle in `night_exchange_commercial.py`. It is intentionally separate from the existing application registry, event ledger and payment ledger.

### 13.1 States and controls

- `proposed`: a structured quote exists; no commitment or work authorization exists.
- `accepted`: requester and provider owners have both approved the exact same canonical terms hash.
- `in_progress`: only the provider owner can start after bilateral approval.
- `delivered`: only the provider owner can mark the deliverable as submitted.
- `completed`: only the requester owner can accept the submitted deliverable.
- `cancelled`: cancellation is limited to the proposed or accepted stage.
- `disputed`: a party can raise a bounded dispute after delivery; it does not imply a refund or payment action.

The domain layer validates distinct owners and applications, a positive quoted amount, a three-letter currency code, bounded text and immutable terms digests. The digest and both owner approvals are rechecked before every post-acceptance transition. A changed quote or scope blocks progression.

### 13.2 Commercial reporting boundaries

The summary function reports mission counts and quoted value by currency only. A quote is not a sale, completed work is not proof of payment, and neither is recognized revenue. Payment status remains explicitly disabled. The module performs no database writes, messaging, external execution, settlement, refunds or money movement.

### 13.3 Integration gates still outstanding

This is a tested-in-source domain prototype, not a live persistent mission register. Before exposing it in the application, implement and independently review:
- additive Supabase tables referencing the existing application registry and any confirmed proposal records;
- server-side RPCs for atomic state transitions, immutable terms, owner authorization, idempotency and append-only audit events;
- explicit RLS, grants and tests using two real authenticated owners;
- a disposable Supabase integration test before any production migration;
- a separate payment and legal review before any paid settlement feature.

No production schema, secrets, existing workflows or payment settings were changed by this prototype. Do not claim live commercial missions, market share or recognized revenue until the persistent integration is deployed and verified.

## 14. Persistent mission register — migration prepared, deployment gated

An additive Supabase migration is prepared at `supabase/migrations/20261121100000_sowia_nex_missions.sql`. It creates:
- `sowia_nex_missions`: mission parties, linked approved professional app listings, structured quote terms, SHA-256 terms digest, bilateral approval digests and guarded lifecycle state;
- `sowia_nex_mission_events`: append-only lifecycle audit events.

Authenticated clients receive participant-only read access. Direct client writes to both tables are revoked. Creation, bilateral approval and lifecycle transitions are exposed only through narrowly scoped security-definer RPCs. The database checks the authenticated caller, ownership of the requesting app, approval of both listings, distinct owners, quote bounds, exact terms digest and actor/state transition rules. The RPCs never move money or execute partner code.

Client wrappers were added to `cloud_storage.py` for creating, approving, transitioning, listing missions and reading their audit events. Unit tests cover RPC selection, input validation and authentication preconditions.

**Deployment is not performed by this commit.** The migration must first be reviewed and applied only to a dedicated disposable Supabase test project, then exercised with two real authenticated test owners and RLS-isolation tests. Production deployment remains blocked until that verification passes. Do not add production secrets or change existing Supabase settings to enable this work.
The migration also adds admin-controlled partner evidence fields to the existing app registry (owner verification, application-control verification, security review and publisher-signature status). New and partner-edited listings are reset to unverified/pending by the existing registry guard trigger; only a trusted admin can set the evidence fields. Mission creation requires both apps to be approved and all four evidence fields to pass. These fields are moderation attestations, not an automated cryptographic publisher-signature verifier or malware scanner; those verification services remain a prerequisite before production admission.

## 15. Test-environment validation and application workflow

The additive migrations are now prepared in the review branch:
- `20261121100000_sowia_nex_missions.sql`: persistent mission tables, RLS, partner-evidence columns and server-guarded lifecycle RPCs;
- `20261121120000_sowia_nex_private_rpcs.sql`: privileged implementations moved to the non-exposed `private` schema, with public `SECURITY INVOKER` RPC wrappers;
- `20261121130000_sowia_nex_admin_verification.sql`: admin-only, append-only verification attestations and a guarded moderation RPC;
- `20261121140000_harden_nex_offer_admission.sql`: existing bilateral offer creation and response now require both apps to retain all four verification attestations.
- `20261121150000_optimize_nex_verification_rls.sql`: keep the new admin-audit RLS check initplan-friendly.

The application now exposes a dedicated Missions commerciales tab and an admin attestation panel. The existing public directory, matching, and offer selectors exclude applications without all four attestations. Existing offer-creation and offer-response RPCs also re-check the attestations server-side, including at response time.

The migration sequence was applied only to the dedicated `SOWIA - TEST` Supabase project. It was not applied to production. The test project contains two distinct test owners and their existing app listings; workflow checks were run inside transactions and rolled back.

Verified test results:
- a complete mission progressed from proposed to completed with seven audit events;
- an unrelated user saw zero mission rows and zero mission-event rows;
- authenticated clients had no direct INSERT/UPDATE privilege on the mission table and no DELETE privilege on the event table;
- an unverified listing was rejected by the mission-creation RPC;
- an unverified listing was also rejected by the legacy offer-creation RPC;
- after admin attestations, the legacy offer workflow succeeded, and its recipient-side event was written;
- a non-admin caller was rejected by the admin verification RPC.

The NIGHT EXCHANGE screen now includes a commercial-missions tab with mission creation, bilateral approvals, guarded lifecycle actions and participant-only audit history. The admin moderation screen can record the four attestations. The catalogue and offer selectors now exclude applications that lack any required attestation.

**Attestation limitation:** the four statuses are controlled administrative attestations. They are not an automated identity provider, cryptographic signature verifier, build attestation service, or malware scanner. Do not mark an application verified until an independent review has actually been performed. Production remains gated on those real verification services, security review, RLS review, and explicit deployment approval. No payments or remote partner-code execution are enabled.
The Supabase test-project advisor review reports no new RLS-initplan or missing-foreign-key-index warnings for the mission and verification tables. Three older SECURITY DEFINER advisories remain in pre-existing integration-administration/professional-access functions; the global leaked-password protection warning is also pre-existing and was not changed as part of this scoped work.
