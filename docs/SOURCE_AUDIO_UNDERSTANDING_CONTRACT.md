# Source Audio Understanding Contract

## Scope

This contract defines the only allowed shape for source-understanding rows used by generation/ranking loops.

## `SourceUnderstandingRecord` Fields

- `record_id`
- `item_id`
- `source_artifact`
- `source_path_redacted`
- `source_type`
- `authorization_status`
- `training_allowed`
- `retrieval_allowed`
- `raw_audio_processing_allowed`
- `evidence_types`
- `evidence_summary`
- `confidence`
- `confidence_band`
- `confidence_reason`
- `usable_as_generation_evidence`
- `blocked_by_policy`
- `blocked_by_confidence`
- `policy_block_reasons`
- `generation_tags`
- `generation_controls`

## Confidence and Evidence Policy

- Confidence is strictly clamped to `[0.0, 1.0]`.
- `confidence_band` derives from `confidence` only: `high >= 0.8`, `medium >= 0.5`, `low < 0.5`.
- Rows with `confidence < 0.5` are automatically blocked (`blocked_by_confidence=true`).
- Rows with unauthorized or unknown authorization are automatically blocked (`blocked_by_policy=true`).
- Raw-audio sources are blocked unless local config explicitly allows raw-audio processing.
- No fake source-audio understanding is allowed: evidence must come from existing local artifacts (normalized corpus, intelligence, theory, feedback).
- No cloud calls and no fake trained-model claims are allowed in this stage.
