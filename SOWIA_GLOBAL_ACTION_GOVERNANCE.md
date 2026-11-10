# SOWIA GLOBAL ACTION GOVERNANCE

A private action-plan register with budget ceilings, accountable owner labels, deadlines, measurable success criteria and explicit stop conditions.

## Approval model
- Creator creates a draft and submits it.
- A different authenticated account must approve or reject.
- Creator may complete an approved plan or cancel a plan.
- Every status transition writes an audit row.
- Direct client updates/deletes are revoked; transitions use a SECURITY DEFINER RPC.
- No payment, purchase, contract, message, or external operation is executed.

## Activation
Apply `supabase_global_action_governance.sql` after the existing SOWIA migrations. A second authenticated account is required to approve a submitted plan. Approval is an internal workflow acknowledgement, not a legal signature or proof of budget availability.
