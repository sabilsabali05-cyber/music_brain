# Controlled Ingestion Sprint V1

This sprint adds policy-first tooling for a small, authorized ingestion batch.

## Scope Rules

- Manifest-driven only; no mass folder ingestion.
- Maximum defaults: 5 song files and 100 sample-library items.
- Dry-run by default.
- Modal and transcription require explicit manifest opt-in.
- No model training in this sprint.

## Command Flow

1. Plan the batch from explicit manifest:
   - `scripts\dev.cmd plan-controlled-ingestion-batch config/controlled_batches/controlled_batch.example.json`
2. Run shell (dry-run by default):
   - `scripts\dev.cmd run-controlled-ingestion-batch config/controlled_batches/controlled_batch.example.json`
3. If execute mode is intentionally requested:
   - `scripts\dev.cmd run-controlled-ingestion-batch config/controlled_batches/<your>.local.json --execute`
   - Current implementation still blocks real processing until ingestion integration is added.
4. Build privacy debt scrub plan (dry-run):
   - `scripts\dev.cmd plan-historical-path-scrub`
5. Build readiness artifacts for review queue, quality, corpus, evaluation, and feedback:
   - `scripts\dev.cmd build-mass-ingestion-readiness-artifacts`
6. Re-evaluate readiness with exact blockers:
   - `scripts\dev.cmd evaluate-mass-ingestion-readiness`

## Regeneration Hook (post-batch)

After a controlled batch is actually integrated and processed, rerun:

- `scripts\dev.cmd generate-tangible-demo 180 golden_ratio climax`
- `scripts\dev.cmd export-ableton-project-v1 outputs/tangible_generation_v1`
- `scripts\dev.cmd validate-tangible-demo`
- `scripts\dev.cmd validate-ableton-project-export`

The current hook keeps `tangible_generation_v1` and Ableton export v1 paths unchanged.

## Training Source Policy

- `training_allowed` stays `false` unless explicit authorization is recorded.
- Allowed training sources are `production`, `retrieval`, and `synplant_seed`.
- Splice is never allowed for training.
