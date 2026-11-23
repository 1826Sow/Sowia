# SOW IA Android build request

This request triggers the existing Android CI workflows to build the current application from the latest main branch. The signed release workflow must use only the already registered upload certificate and existing GitHub secrets. No signing material, credentials, application identity, or working application code may be changed.

The parallel package is a separate installation target and does not overwrite the Google Play package. Debug signing is for preview/testing only; it is not a production release signature.

Build request refreshed on 2026-11-23. Preserve the registered application identity and signing certificate; do not generate or replace signing material.
