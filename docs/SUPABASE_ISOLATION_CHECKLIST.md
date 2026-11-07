# SOW IA — Supabase isolation validation

This checklist is for the final security gate before merging the private-storage
work. It must be run against a **separate Supabase test project**, never against
the live project as a first test.

## Safety prerequisites

- Create or select a disposable Supabase project dedicated to testing.
- Do not copy production service-role keys into GitHub, chat, source files or a
  client-side environment.
- Create two distinct test users, A and B, through the normal Supabase Auth
  signup/login flow. Record their UUIDs; do not share passwords or access tokens.
- Configure a temporary test deployment using the test project's URL and anon
  key, with `SOWIA_REQUIRE_AUTH=true`.
- Confirm the test deployment authenticates A and B independently.
- Run `supabase/schema.sql` once in the isolated project's SQL Editor. It also
  creates the private PDF bucket and its policies. Do not run this against
  production as part of this checklist. Then run the read-only inspection queries
  in `supabase/verify_security.sql` to review RLS, grants, policies and bucket settings.

## Account A / Account B test matrix

Use the application itself for the end-to-end checks below. Sign out completely
between accounts and verify the displayed signed-in identity after each login.

| Feature | Account A | Account B expected result |
|---|---|---|
| Conversation history | Create a uniquely named test conversation | A's conversation is absent |
| Memory | Save a unique test memory | A's memory is absent |
| Private PDF | Upload a harmless test PDF | A's filename is absent; direct download is denied |
| Deletion | Delete A's test PDF while signed in as A | B cannot delete A's object |
| Premium entitlement | Read own entitlement | Cannot read A's entitlement or change its status |

For each feature, also create a separate item as B and confirm A cannot see it.
Do not use real personal documents or payment data.

## Storage-specific negative checks

- A can upload and download a PDF under the path prefix `<A-UUID>/...`.
- B cannot list, download or delete that object.
- B cannot upload an object under A's UUID prefix.
- A cannot access an object under B's UUID prefix.
- An unauthenticated request cannot read private objects.
- The bucket remains private, limited to 10 MiB and `application/pdf`.

## SQL privilege checks

In the isolated project's SQL Editor, inspect the table grants and RLS policies
for `public.sowia_messages`, `public.sowia_memory_items`,
`public.sowia_entitlements` and `storage.objects`.

Expected contract:

- Messages and memory: authenticated users can select/insert/delete only rows
  whose `user_id` equals `auth.uid()`; client update is not granted.
- Entitlements: authenticated users have select only, scoped to their own UUID.
  Client insert/update/delete is not granted.
- Storage: authenticated users can select/insert/delete only objects in the
  private bucket whose first folder is their own UUID.
- Anonymous users have no access to these private records or objects.

## Completion record

Record only pass/fail and the test project's identifier (never keys, passwords,
tokens or personal document contents). Any failed check blocks merge and
production deployment until corrected and retested.

This checklist does not itself execute the migration or prove RLS behavior. The
automated repository tests inspect source definitions; this isolated project
test is the required runtime verification.
