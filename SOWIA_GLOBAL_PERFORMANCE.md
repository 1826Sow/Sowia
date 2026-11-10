# SOWIA GLOBAL PERFORMANCE & IMPACT

## Purpose
Measure the progress and observed outcomes of approved SOWIA action plans without inventing a global impact score.

## Data recorded
Each append-only observation is linked to an approved or completed action plan and records:
- cumulative spend to date (not the sum of successive snapshots);
- completion percentage;
- one optional operational outcome indicator and unit;
- separate social and environmental impact notes;
- a user-declared evidence level, reference, timestamp and commentary.

The database trigger copies the plan title, country, approved budget and currency into the observation so the reference values remain stable if the plan is later edited.

## Dashboard rules
- Only the latest cumulative-spend snapshot per plan is used for the current portfolio view.
- Budget variance is calculated per plan from the approved budget cap and latest cumulative spend.
- Totals across plans may mix currencies; the interface warns that they are not a consolidated monetary total.
- Social and environmental observations are counted and displayed separately.
- No ROI, causal attribution, independent verification, or combined ESG score is inferred.

## Security and limits
- Supabase row-level security restricts measurements to the plan creator.
- Only the creator can add measurements for plans in approved or completed status.
- Measurements are append-only for authenticated clients; update and delete privileges are revoked.
- Evidence levels are declarations, not automatic SOWIA verification.
- Apply `supabase_global_performance.sql` after `supabase_global_action_governance.sql`.
