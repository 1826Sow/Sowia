# SOWIA GLOBAL LEARNING ENGINE

## Purpose
The module records what happened after a decision was made. It compares the original recommendation with the option actually selected and a user-reported outcome score (1–5).

## Data integrity
- The original decision is read from `sowia_global_decisions`.
- A database trigger creates the baseline snapshot from that saved row on insert.
- The original snapshot, source decision, owner and recommendation-alignment result cannot be changed later.
- One learning observation is allowed per saved decision. The observation can be deleted by its owner.
- Outcome notes and optional evidence references are additional observations; they never rewrite the original decision.

## Interpretation limits
- Outcome scores are user-reported and may be subjective or incomplete.
- The result of the option not selected is generally unknown.
- Alignment between a recommendation and a chosen option is not proof that the recommendation caused the result.
- Summary statistics are descriptive and do not automatically retrain or modify an AI model.
- Do not make strategic, financial, legal or safety-critical decisions from these statistics alone.

## Activation
Apply `supabase_global_learning.sql` only after `supabase_global_decisions.sql` has been applied. The migration creates a private owner-scoped table with row-level security and a database-enforced immutable baseline snapshot.

## Current implementation status
The Python engine, unit tests, private storage wrappers and Streamlit page are committed to the `main` branch. The SQL migration is committed but must still be applied to the Supabase project. Live database behavior and the deployed Streamlit page have not yet been verified.
