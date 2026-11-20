# SOW IA Android build request

This file records the request to run the existing Android CI workflows. It does not modify application code, Gradle configuration, signing material, credentials, or release identity.

The CI workflow is responsible for building the debug APK and, when the registered upload-key secrets are present and verified, the signed release APKs.

Build request refreshed on 2026-11-20 to trigger the repository's existing Android build workflows. Preserve the registered application identity and signing certificate; do not generate or replace signing material.
