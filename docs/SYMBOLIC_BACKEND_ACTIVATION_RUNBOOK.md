# Symbolic Backend Activation Runbook

This runbook enables local pretrained symbolic inference gates for Text2MIDI, Moonbeam, MIDI-GPT, and MusicBERT.

## Guardrails

- Local-first workflow only; cloud calls remain disabled by default.
- Do not auto-clone repositories.
- Do not auto-download model weights.
- Do not run training or fine-tuning.
- Do not process audio.
- Keep private paths and local tokens out of committed reports.

## Manual Setup Steps

- Copy `config/model_integrations/model_integrations.example.json` to `config/model_integrations/model_integrations.local.json`.
- Run `scripts/dev.cmd bootstrap-symbolic-model-local-config` to ensure required symbolic sections exist.
- For each backend (`text2midi`, `moonbeam`, `midigpt`, `musicbert`):
  - Set `enabled=true`.
  - Set local `repo_path`, `model_path`, and `tokenizer_path` values.
  - Keep `smoke_test_enabled=true` if you want explicit extra guardrails.
- Clone model repositories manually into local-only folders ignored by git.
- Place model and tokenizer files manually into local-only weight/cache folders ignored by git.

## Validation Commands

- `scripts/dev.cmd check-text2midi-setup`
- `scripts/dev.cmd check-moonbeam-setup`
- `scripts/dev.cmd check-midigpt-setup`
- `scripts/dev.cmd check-musicbert-setup`
- `scripts/dev.cmd run-text2midi-smoke-test`
- `scripts/dev.cmd run-moonbeam-smoke-test`
- `scripts/dev.cmd run-midigpt-smoke-test`
- `scripts/dev.cmd run-musicbert-smoke-test`
- `scripts/dev.cmd check-symbolic-backend-activation`

## Fallback Guidance

- If all symbolic generation backends are unavailable, generation falls back to `example_retrieval + ruleset`.
- If MusicBERT is unavailable, candidate ranking falls back to deterministic heuristic scoring.
- Fallback usage is always reported explicitly in generation reports.

## Optional Cloud Support

- Cloud adapters are optional and not required for local activation.
- Keep cloud endpoint usage disabled by default.
- Never print cloud token values in logs or reports.
- Do not call Modal unless explicitly configured by the operator.
