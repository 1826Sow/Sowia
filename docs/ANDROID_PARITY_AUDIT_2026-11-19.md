# SOW IA Android parity audit — 19 November 2026

## Scope and safety

This audit compares the Android source in `main`, the existing Supabase production project, and the isolated SOWIA TEST project. The Streamlit web app and production Supabase project were not modified during this work. No keys, certificates, signing material, or production secrets were read or changed.

## Verified Android capabilities in source

- Native Jetpack Compose interface with Personal and Professional workspace selection.
- Email/password sign-in against Supabase Auth; access and refresh tokens are stored encrypted with Android Keystore AES-GCM.
- Session refresh and sign-out.
- Conversation and project list retrieval through Supabase REST, scoped to the authenticated user and workspace.
- Conversation history retrieval and assistant requests through `mobile-chat`.
- Private PDF upload/list/download/delete in the `sowia-files` bucket; 10 MiB upload cap.
- Local PDF text extraction with PDFBox and OCR fallback with ML Kit (up to 10 pages); extracted text is sent to the assistant for analysis.
- Android Back handling and visible in-app Back control.

## Verified production backend

Production Supabase project `Sowia` is healthy. Its Edge Functions include:
- `mobile-health` (active, JWT verification enabled)
- `mobile-chat` (active, JWT verification enabled)
- Existing payment and application functions.

The production `mobile-chat` function verifies the bearer token with Supabase Auth, derives the user ID from the verified user, applies user/workspace scoping, loads conversation history and memory, calls the configured AI provider server-side, and persists messages. Provider keys are not embedded in the Android source.

RLS is enabled on the checked tables `sowia_messages`, `sowia_memory_items`, `sowia_projects`, and `sowia_conversations`. Policies scope records to `auth.uid()`; professional workspace access is additionally gated by `sowia_has_professional_access()`.

## Gaps against the full SOW IA web suite

- The Android home screen remains a limited shell with four primary sections.
- No native web-search workflow was found in the Android source inspected.
- The full set of professional/business modules from the web suite is not represented in Android navigation.
- Native sign-in currently uses the password grant; the architecture contract calls for Authorization Code + PKCE. This must be reconciled before a public Play release.
- The current source does not establish that the installed APK was built from the latest commit or that a signed release build passed on a physical device.
- Android PDF analysis uses local extraction/OCR plus the assistant; it is not a full equivalent of every web PDF workflow.

## Isolated test environment work

The SOWIA TEST Supabase project is healthy and contains the expected conversations, messages, projects, memory, and entitlement tables. The four checked user-data tables have RLS enabled.

An authenticated `mobile-health` Edge Function was deployed to TEST (version 1, active, `verify_jwt=true`). It is a connectivity/authentication health check only. No AI provider secret was copied to TEST, and no production Edge Function was overwritten.

The TEST project did not have `mobile-chat` before this audit. The production function must not be copied blindly: it depends on server-side AI-provider configuration and must be validated in TEST with its own secrets and test users.

## Next implementation sequence

1. Add a native PKCE sign-in flow and validate session refresh/expiry on Android.
2. Validate TEST health-check calls from the app using a real test account (never request or store the user's password in chat).
3. Configure and test a dedicated AI provider secret in TEST, then deploy the reviewed `mobile-chat` implementation there.
4. Add Android navigation and client modules for the remaining professional features and web search, reusing existing backend contracts and RLS.
5. Build, sign, install, and test a new APK/AAB on a physical Android device; only then provide a verified download/release.
6. Keep production untouched until TEST passes end-to-end and a separately reviewed release is approved.

## Status

This document records a source/backend audit and one isolated TEST deployment. It does not claim that the full Android feature set, a new APK, or a Play Store release is complete.
