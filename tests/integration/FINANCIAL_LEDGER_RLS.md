# SOWIA financial ledger — live RLS test

These checks must run only against a dedicated Supabase test project. They use
the public anon key and two dedicated authenticated test accounts. They never
use `service_role` and never write to, update, or delete ledger records.

## Test-project preparation

1. Create two dedicated test users (A and B) in Supabase Authentication.
2. Apply the financial ledger migration to this isolated project.
3. In the SQL Editor of the test project only, seed one synthetic row owned by
   user A. Replace the email with the dedicated test account A email:

```sql
insert into public.sowia_financial_transactions (
    user_id,
    provider,
    provider_payment_id,
    transaction_type,
    status,
    gross_amount,
    gross_currency,
    occurred_at
)
select
    id,
    'paypal',
    'SOWIA-RLS-OWNER-A-FIXTURE-001',
    'payment',
    'manual_review',
    0.01,
    'EUR',
    now()
from auth.users
where email = 'TEST-ACCOUNT-A-EMAIL'
on conflict (provider, provider_payment_id, transaction_type) do nothing;
```

Verify that exactly one fixture row exists and belongs to A. Do not seed this
fixture in production. The row is intentionally left untouched by the tests;
remove it manually from the isolated test project after the test campaign.

## GitHub Actions secrets

Use the six existing dedicated test-project secrets documented in
`tests/integration/README.md`:

- `SOWIA_TEST_SUPABASE_URL`
- `SOWIA_TEST_SUPABASE_ANON_KEY`
- `SOWIA_TEST_USER_A_EMAIL`
- `SOWIA_TEST_USER_A_PASSWORD`
- `SOWIA_TEST_USER_B_EMAIL`
- `SOWIA_TEST_USER_B_PASSWORD`

Add one additional Actions secret:

- `SOWIA_TEST_FINANCIAL_FIXTURE_PAYMENT_ID` = `SOWIA-RLS-OWNER-A-FIXTURE-001`

Never commit secret values or use production credentials.

## Execution

```bash
pytest -q tests/integration/test_supabase_financial_ledger_two_user_isolation.py
```

The suite checks anonymous denial, client-side insert denial, owner A visibility,
account B invisibility, and authenticated update/delete denial. It then confirms
that the seeded row remains unchanged. The two-user visibility and mutation
checks are skipped if the fixture ID is not configured; a skipped test is not
evidence of RLS isolation.
