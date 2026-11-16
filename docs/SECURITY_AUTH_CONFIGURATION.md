# Supabase Auth security configuration

Project: `Sowia` (`qegcopordeqjiechmbhg`)

## Leaked-password protection

Supabase Security Advisor currently reports `auth_leaked_password_protection`.

The owning Supabase organization is currently on the **Free** plan. Supabase documents leaked-password protection (Have I Been Pwned Pwned Passwords checks) as available on **Pro and above**. This is a hosted Auth project setting, not a Postgres migration.

When the project is on an eligible plan, enable it in:

1. Supabase Dashboard → Authentication → Sign In / Providers → Email.
2. Enable **Prevent use of leaked passwords**.
3. Save, then rerun Security Advisor.

The equivalent Management API setting is `password_hibp_enabled: true` on
`PATCH /v1/projects/{ref}/config/auth`. A Management API access token with the appropriate Auth configuration permission is required. Never put that token in this repository, app secrets, client code, or chat.

## Free-plan mitigation

Until the project is on an eligible plan, keep the existing authentication flow and accounts intact. Review the Email provider settings and use a minimum password length of at least 8 characters (preferably 10–12) plus the strongest available character requirements. These are separate controls and do not replace breached-password screening.

Do not change existing users' passwords automatically. Do not claim leaked-password protection is enabled while the Security Advisor still reports it.

## Verification

Completion evidence:
- The Auth Email provider setting is enabled, or the Management API returns `password_hibp_enabled: true`.
- The Security Advisor no longer reports `auth_leaked_password_protection`.

This file documents the operational requirement only; it does not change hosted Auth configuration.
