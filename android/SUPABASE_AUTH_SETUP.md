# Native Android Supabase authentication setup

The Android app reads the Supabase project URL and **public anon/publishable key** at build time.
It never embeds the Supabase service-role key, an AI-provider key, or a PayPal secret.

For a local Android Studio build, add these values to `android/local.properties`
(the file is ignored by Git):

```properties
SOWIA_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SOWIA_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_OR_PUBLISHABLE_KEY
```

Alternatively, provide environment variables with the same names to Gradle/CI.
The CI build intentionally compiles with empty values when no configuration is supplied;
the sign-in action remains disabled until configured.

The first native milestone supports Supabase email/password sign-in, refresh-token rotation
(via the explicit `refreshSession()` method), and sign-out. Session data is encrypted with
AES-GCM using a key held in Android Keystore. Automatic refresh scheduling is not yet wired
into the UI; authenticated service calls must refresh/validate the session before use.
Password recovery, provider OAuth/PKCE (if enabled for the account), account lifecycle,
and real-device tests remain outstanding.

Authentication alone does not connect chat, project registry, PDF processing, or AI.
Those services must be added through user-scoped RLS or authenticated server endpoints.
