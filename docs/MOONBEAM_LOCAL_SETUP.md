# Moonbeam Local Setup (Vertical Slice V1)

This guide scaffolds Moonbeam as the first vertical-slice symbolic model target.
It does **not** download weights, run long generation jobs, or train models.

## Purpose

- Treat Moonbeam as the main symbolic continuation/infill backend target.
- Keep availability-safe behavior until local config, paths, and smoke checks are valid.
- Keep all local/private paths out of public reports.

## Local Config

Create:

- `config/model_integrations/model_integrations.local.json`

Start from:

- `config/model_integrations/model_integrations.example.json`

Moonbeam fields:

- `enabled`
- `repo_path`
- `model_path`
- `tokenizer_path`
- `device`
- `smoke_test_enabled`
- `max_tokens`
- `output_dir`

Local config remains gitignored via:

- `config/model_integrations/*.local.json`

## Commands

- `scripts\dev.cmd check-moonbeam-setup`
- `scripts\dev.cmd run-moonbeam-smoke-test`

Both commands:

- avoid downloading weights
- avoid training
- avoid long generation
- redact local paths in generated public reports

## Expected Initial State

Without a local config:

- `moonbeam_configured=false`
- `moonbeam_available=false`
- `smoke_test_passed=false`
- `unavailable_reason=disabled_or_missing_local_config`

## Next Exact Setup Step

1. Copy `config/model_integrations/model_integrations.example.json` to `config/model_integrations/model_integrations.local.json`.
2. Set `models.moonbeam.enabled=true`.
3. Fill `repo_path`, `model_path`, and `tokenizer_path` with valid local paths.
4. Set `smoke_test_enabled=true`.
5. Re-run `scripts\dev.cmd run-moonbeam-smoke-test`.
