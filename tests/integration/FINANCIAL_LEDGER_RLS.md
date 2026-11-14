# SOWIA financial ledger — live RLS test

Run this suite only against a dedicated, isolated Supabase test project. It uses
the public anon key and two dedicated test accounts; it never uses
`service_role`.

**Important:** the suite sends attempted INSERT, UPDATE, and DELETE requests to
verify that client-side mutations are denied. If a policy is misconfigured,
a synthetic row can be inserted, modified, or deleted. Never point these tests
at production. Re-seed the fixture after a failed mutation test before rerunning.

## Test-project preparation

1. Create two dedicated test users (A and B) in Supabase Authentication.
2. Apply the financial-ledger migration to this isolated project.
3. In the SQL Editor of the test project only, seed one synthetic row owned by
   user A. Replace the email with the dedicated test account A email:

```sql
insert into public.sowia_financial_transactions (
    user_id, provider, provider_payment_id, transaction_type,
    status, gross_amount, gross_currency, occurred_at
)
select
    id, 'paypal', 'SOWIA-RLS-OWNER-A-FIXTURE-001', 'payment',
    'manual_review', 0.01, 'EUR', now()
from auth.users
where email = 'TEST-ACCOUNT-A-EMAIL'
on conflict (provider, provider_payment_id, transaction_type) do nothing;
```

Verify that exactly one fixture row exists and belongs to A. Do not seed this
fixture in production.

## GitHub Actions secrets

Use the six dedicated test-project secrets documented in
`tests/integration/README.md`:

- `SOWIA_TEST_SUPABASE_URL`
- `SOWIA_TEST_SUPABASE_ANON_KEY`
- `SOWIA_TEST_USER_A_EMAIL`
- `SOWIA_TEST_USER_A_PASSWORD`
- `SOWIA_TEST_USER_B_EMAIL`
- `SOWIA_TEST_USER_B_PASSWORD`

Add the fixture ID secret:

- `SOWIA_TEST_FINANCIAL_FIXTURE_PAYMENT_ID` = `SOWIA-RLS-OWNER-A-FIXTURE-001`

The workflow also requires the existing
`SOWIA_TEST_PROJECT_CONFIRMATION` secret to equal
`I_CONFIRM_THIS_IS_A_DEDICATED_SOWIA_TEST_PROJECT`. This is an additional
guard against accidentally running live tests against production.

Never commit secret values or use production credentials.

## Execution

```bash
pytest -q tests/integration/test_supabase_financial_ledger_two_user_isolation.py
```

The suite checks anonymous denial, authenticated insert denial, owner A
visibility, account B invisibility, and authenticated update/delete denial.
The fixture-dependent tests are skipped if the fixture ID is absent; skipped
tests are not evidence of RLS isolation.
