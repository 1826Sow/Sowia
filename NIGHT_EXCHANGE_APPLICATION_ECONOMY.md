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
