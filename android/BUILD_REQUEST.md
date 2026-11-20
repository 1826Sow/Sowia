# SOW IA Android build request

This request triggers the existing Android prototype CI workflow to produce installable debug APKs for the current and parallel application IDs. It does not modify application code, Gradle configuration, signing material, credentials, or release identity.

The parallel package is a separate installation target and does not overwrite the Google Play package. Debug signing is for preview/testing only; it is not a production release signature.

Build request refreshed on 2026-11-20. Preserve the registered application identity and signing certificate; do not generate or replace signing material.
