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
