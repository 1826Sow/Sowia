# SOW IA Android backend discovery

**Inspection date:** 2026-11-17  
**Supabase project:** `qegcopordeqjiechmbhg`

## Result

The deployed Supabase Edge Function inventory was inspected before wiring native Android features. The currently active functions are:

| Function | JWT verification | Observed purpose |
|---|---:|---|
| `paypal-one-time` | enabled | PayPal one-time payment |
| `paypal-webhook` | disabled | PayPal webhook receiver |
| `super-endpoint` | enabled | Its deployed source is a PayPal subscription webhook handler, despite the generic name |
| `swift-processor` | enabled | Its deployed source is also PayPal recurring-subscription webhook processing; its source comment refers to deployment as `paypal-webhook` |

The deployed sources inspected for `super-endpoint` and `swift-processor` contain PayPal subscription/webhook logic. They are **not** mobile chat, project-registry, or PDF APIs.

No native mobile API endpoint was identified in this inspection. The Android screens for Assistant, Mes échanges & projets, and Laboratoire PDF must therefore remain explicitly marked as awaiting service integration. Do not point them at a PayPal function or invent a URL.

## Required integration boundary

Before enabling those Android screens, implement and deploy dedicated authenticated server-side endpoints (or prove an existing endpoint with equivalent contracts):

- **Assistant:** accept a user message, derive the user identity from the verified Supabase JWT, enforce per-user and entitlement limits server-side, call the configured AI provider using server-only credentials, and persist conversation records under the authenticated user.
- **Projects:** expose only rows owned by the JWT subject; retain the database owner and workspace checks enforced by RLS.
- **PDF:** accept bounded uploads or storage references, verify ownership, enforce file-size/type limits, process server-side, and return a user-scoped result/download reference.

## Security constraints

- Android may contain only the Supabase public anon/publishable key; it is not a server secret.
- Never ship the Supabase service-role key, AI-provider credentials, PayPal credentials, webhook secrets, or signing keys in the APK/AAB or source repository.
- Every privileged operation must run server-side and authorize the user from a verified JWT. Do not trust a client-supplied user ID.
- Keep the existing Streamlit web application and its data paths intact while the native APIs are added.
- Do not mark native chat, project synchronization, or PDF processing as complete until deployed endpoint tests and real authenticated-device tests pass.

## Next implementation step

Create a dedicated mobile API function only after defining and testing its request/response contract against the existing database schema and entitlement model. Then connect one Android feature at a time, beginning with a minimal authenticated health/profile call before chat or file processing.


## First native API delivered — 2026-11-17

A dedicated `mobile-health` Edge Function is now deployed to the production Supabase project:

- Route: `GET /functions/v1/mobile-health`
- Platform JWT verification: **enabled**
- Deployment status: **ACTIVE**, version 1
- Contract: returns `ok`, `service`, and `contractVersion` only after the Supabase gateway accepts the caller's bearer JWT.
- It does not accept a client-supplied user ID, expose account data, invoke an AI provider, or use privileged credentials.

The Android account screen now includes **Tester la connexion sécurisée**. It sends the stored user access token in `Authorization: Bearer …` and the public project key in `apikey`, then validates the expected service response.

This is the first real native-to-backend integration. It proves the authenticated transport path once exercised with a configured Supabase account on a device. It does **not** yet connect chat, project synchronization, or PDF processing. Those remain separate deliverables.
