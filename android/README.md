# SOW IA — prototype Android

This is a **native Android companion app** to the existing Streamlit web app. It is not yet at full web-suite feature parity.

## Included
- Kotlin + Jetpack Compose application shell
- Midnight-blue / cyan visual foundation
- Home screen with the initial SOW IA sections
- Visible in-app Back control and Android system Back handling
- Explicit placeholder state: no private data or live service is connected

## Not included yet
- Authorization Code + PKCE sign-in (the current client uses email/password token grant)
- Full parity with all SOW IA web-suite modules and native web search
- A verified signed release build and physical-device test evidence

Partially implemented in source: Supabase email/password sign-in and encrypted session storage, conversations/projects, assistant calls through the production `mobile-chat` function, and private PDF storage with local extraction/OCR. See [the parity audit](../docs/ANDROID_PARITY_AUDIT_2026-11-19.md) for verified scope and remaining gaps.

No server secrets belong in this Android project. The existing Streamlit application remains unchanged.

## Build
Open the `android/` folder in Android Studio with JDK 17 and Android SDK 35 installed. Let Gradle sync, then run the `app` configuration on an emulator or Android device.

This scaffold must pass a real Android build and device tests before it is considered installable or release-ready.

## Native integration contract

Before connecting authentication or private data, follow [`docs/ANDROID_NATIVE_INTEGRATION_CONTRACT.md`](../docs/ANDROID_NATIVE_INTEGRATION_CONTRACT.md). It defines the Supabase PKCE, RLS, server-side AI, PDF, and Play Store security boundaries. Proposed API paths in that document are design contracts only; they are not deployed endpoints.
