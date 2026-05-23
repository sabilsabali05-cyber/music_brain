# Source Authorization Policy

This project only allows the following `source` values when `training_allowed=true`:

- `production`
- `retrieval`
- `synplant_seed`

## Hard Rules

- `training_allowed` defaults to `false`.
- Any `source` containing `splice` is blocked for training.
- `authorization_required` must remain `true` for controlled batches.
- Use `excluded=true` for records that should never enter training exports.

## Validation Commands

- `scripts\dev.cmd plan-controlled-ingestion-batch config/controlled_batches/controlled_batch.example.json`
- `scripts\dev.cmd run-controlled-ingestion-batch config/controlled_batches/controlled_batch.example.json`
- `scripts\dev.cmd evaluate-mass-ingestion-readiness`
