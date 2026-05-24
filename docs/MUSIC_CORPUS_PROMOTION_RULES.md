# Music Corpus Promotion Rules

Deterministic labels:

- `training_safe`
- `retrieval_only`
- `excluded`

## training_safe (all required)

- `authorization_status` is `accepted` or `authorized`.
- `training_allowed` is true.
- Policy fields are complete.
- Transcription confidence is above threshold for symbolic/audio-derived records.
- Labels are non-sparse.
- Junk penalty is below threshold.
- Overall music value is above threshold.
- Provenance is complete and redacted.

## retrieval_only

Use `retrieval_only` when record is musically useful but training is blocked, including:

- Policy or training completeness is missing.
- Authorization is `reference`, `copyrighted`, or `unknown`.
- Production-only usage.
- Sparse labels.
- Low transcription confidence but useful descriptors still exist.
- Generated MIDI without sufficient review.

## excluded

Use `excluded` when:

- Unauthorized/private/sensitive authorization.
- Explicit policy exclusion.
- Missing required provenance.
- Extremely noisy/junk content with insufficient retrieval value.
- Invalid artifact/policy state requiring hard block.

## Guardrails

- `copyrighted`, `reference`, and `unknown` authorization are never promoted to `training_safe`.
- Missing policy fields block `training_safe`.
- Missing labels block supervised training eligibility.
- Deterministic thresholds are defined in code (`PromotionThresholds`) and applied uniformly.
