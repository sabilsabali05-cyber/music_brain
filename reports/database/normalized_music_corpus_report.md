# Normalized Music Corpus Report

- total rows: `2497`
- accepted rows: `152`
- review-required rows: `2345`
- rejected rows: `0`
- training-eligible rows: `0`
- validation-eligible rows: `0`
- retrieval-only rows: `2497`
- policy-missing rows: `2417`
- label-missing rows: `2497`
- duplicate rows: `2520`
- schema drift resolved count: `2497`

## Notes
- Missing policy fields default training_allowed to false.
- Missing authorization_status and review_status default to review_required.
- Splice/production-only entries are retrieval-only unless explicitly overridden.
- Generated MIDI rows remain non-training unless explicitly reviewed and allowed.
