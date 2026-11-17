# SOW IA — prototype Android

This is an **early native Android UI scaffold**, separate from the existing Streamlit web app.

## Included
- Kotlin + Jetpack Compose application shell
- Midnight-blue / cyan visual foundation
- Home screen with the initial SOW IA sections
- Visible in-app Back control and Android system Back handling
- Explicit placeholder state: no private data or live service is connected

## Not included yet
- Supabase native OAuth/PKCE sign-in or sign-out
- SOW IA API endpoints
- Conversations, project registry, PDF upload, AI or web search integration
- Production signing, APK/AAB release, Play Store submission

No server secrets belong in this Android project. The existing Streamlit application remains unchanged.

## Build
Open the `android/` folder in Android Studio with JDK 17 and Android SDK 35 installed. Let Gradle sync, then run the `app` configuration on an emulator or Android device.

This scaffold must pass a real Android build and device tests before it is considered installable or release-ready.

## Native integration contract

Before connecting authentication or private data, follow [`docs/ANDROID_NATIVE_INTEGRATION_CONTRACT.md`](../docs/ANDROID_NATIVE_INTEGRATION_CONTRACT.md). It defines the Supabase PKCE, RLS, server-side AI, PDF, and Play Store security boundaries. Proposed API paths in that document are design contracts only; they are not deployed endpoints.
