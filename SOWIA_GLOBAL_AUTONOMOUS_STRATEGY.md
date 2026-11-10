# SOWIA GLOBAL AUTONOMOUS STRATEGY

This module synthesizes the authenticated user's existing private market assessments, active alerts, saved forecasts, decision comparisons and observed outcomes into a transparent priority review.

## Guardrails
- Deterministic rules; no external data is fetched and no action is executed.
- Critical/high risk signals can trigger a human review priority.
- Strong opportunity scores recommend preparing a limited pilot, not launching it.
- Missing assessments are not ranked.
- Scores and alerts are user-entered or previously captured data, not independent verification.
- Learning statistics are descriptive and do not establish causality or retrain an AI model.
- Human approval is always required; execution is explicitly disabled.

## Activation
The page reads existing records through current private Supabase helpers. It adds no new table and requires no new SQL migration. The existing migrations for GLOBAL INTELLIGENCE, ALERTS, STRATEGIC FORECAST, DECISION ENGINE and LEARNING ENGINE must still be applied before those datasets can be read.
