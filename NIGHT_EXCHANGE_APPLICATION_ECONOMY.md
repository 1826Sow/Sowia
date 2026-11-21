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
