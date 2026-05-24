# MusicBERT Local Setup (Vertical Slice V1)

This guide scaffolds MusicBERT as the symbolic understanding, evaluator, and ranking vertical slice target.
It does **not** download weights, run full evaluation inference, or train models.

## Purpose

- Treat MusicBERT as the symbolic critic/ranker target.
- Keep availability-safe behavior until local config, paths, and smoke checks are valid.
- Keep all local/private paths out of public reports.

## Local Config

Create:

- `config/model_integrations/model_integrations.local.json`

Start from:

- `config/model_integrations/model_integrations.example.json`

MusicBERT fields:

- `enabled`
- `repo_path`
- `model_path`
- `tokenizer_path`
- `device`
- `smoke_test_enabled`
- `embedding_dim`
- `output_dir`

Local config remains gitignored via:

- `config/model_integrations/*.local.json`

## Commands

- `scripts\dev.cmd check-musicbert-setup`
- `scripts\dev.cmd run-musicbert-smoke-test`
- `scripts\dev.cmd evaluate-symbolic-candidates-musicbert`

These commands:

- avoid downloading weights
- avoid training
- avoid fake scores when unavailable
- redact local paths in generated public reports

## Expected Initial State

Without a local config:

- `musicbert_configured=false`
- `musicbert_available=false`
- `smoke_test_passed=false`
- `unavailable_reason=disabled_or_missing_local_config`

Candidate evaluation scaffold default:

- `status=unavailable`
- `no_fake_evaluation=true`
- `scores_generated=false`

## Next Exact Setup Step

1. Copy `config/model_integrations/model_integrations.example.json` to `config/model_integrations/model_integrations.local.json`.
2. Set `models.musicbert.enabled=true`.
3. Fill `repo_path`, `model_path`, and `tokenizer_path` with valid local paths.
4. Set `smoke_test_enabled=true`.
5. Re-run `scripts\dev.cmd run-musicbert-smoke-test`.
