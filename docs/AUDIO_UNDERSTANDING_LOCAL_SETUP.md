# Audio Understanding Local Setup

This vertical slice scaffolds local setup checks for `essentia`, `muq`, and `mert` with strict safety defaults.

## Scope

- Disabled by default in example config.
- No audio processing in setup checks or smoke tests.
- No Modal calls.
- No transcription.
- No model training.
- No model weight downloads.

## Required Local Configuration

Copy:

- `config/model_integrations/model_integrations.example.json`

to:

- `config/model_integrations/model_integrations.local.json`

Then update `models.essentia`, `models.muq`, and `models.mert` with real local values and explicitly set `enabled=true` only after policy review.

## Dev Tasks

- `scripts/dev.cmd check-audio-understanding-setup`
- `scripts/dev.cmd run-audio-understanding-smoke-tests`
- `scripts/dev.cmd plan-audio-texture-embedding`

## Expected Default Outcome

In the default environment (no local config enabled):

- `essentia_configured=false`, `essentia_available=false`
- `muq_configured=false`, `muq_available=false`
- `mert_configured=false`, `mert_available=false`
- `smoke_tests_passed=false`

This is the expected safe baseline.
