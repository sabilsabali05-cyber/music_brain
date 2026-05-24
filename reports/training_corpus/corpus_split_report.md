# Corpus Split Report

- total input rows: `2497`
- train rows: `0`
- validation rows: `0`
- retrieval-only rows: `152`
- review-required rows: `2345`

## Top blockers
- not_accepted: `2345`
- training_not_allowed: `152`

## Rules
- Only accepted + training_allowed=true + policy complete + non-sparse labels are promoted.
- Rows with missing policy fields cannot enter train/validation.
- Sparse labels are routed to retrieval/reviewer pools.
- Deterministic hash split (80/20) is used for train/validation assignment.
- Generated MIDI rows require human review before supervised use.
