# MIDI-GPT Local Setup

This project keeps MIDI-GPT optional and disabled by default.

## Safety and Scope

- No audio processing is required for this setup.
- No model download is triggered by setup checkers.
- No model training is performed by setup checkers or smoke tests.
- No fake MIDI generation is produced by the MIDI-GPT scaffold.

## Local Config

1. Copy `config/model_integrations/model_integrations.example.json` to:
   `config/model_integrations/model_integrations.local.json`
2. Update `models.midigpt` fields in your local config:
   - `enabled: true`
   - `repo_path`: existing local MIDI-GPT repository path
   - `model_path`: existing local model file/folder path
   - `tokenizer_path`: existing local tokenizer path
   - `device`: local runtime device (for example `cpu`)
   - `smoke_test_enabled: true`
3. Keep local config untracked (`config/model_integrations/*.local.json` is gitignored).

## Validation Commands

Run these from repo root:

```powershell
scripts\dev.cmd check-midigpt-setup
scripts\dev.cmd run-midigpt-smoke-test
scripts\dev.cmd generate-midigpt-variation-scaffold
```

## Expected Default (No Local Config)

- `midigpt_configured=false`
- `midigpt_available=false`
- `smoke_test_passed=false`
- `model_training_has_occurred=false`
- variation scaffold status is `unavailable` with `no_fake_generation=true`
