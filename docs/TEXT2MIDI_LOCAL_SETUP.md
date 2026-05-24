# Text2MIDI Local Setup (Vertical Slice)

This document describes the **local-only** Text2MIDI setup gates used by the vertical-slice scaffold.

## Scope and Constraints

- This slice is prompt-sketch scaffolding only.
- No audio processing is required.
- No model downloads are performed by setup checks.
- No training is performed.
- No fake MIDI generation or fake scoring is emitted.

## 1) Configure local model integrations

1. Copy:
   - `config/model_integrations/model_integrations.example.json`
   - to `config/model_integrations/model_integrations.local.json`
2. In `models.text2midi`, set:
   - `enabled=true`
   - `repo_path` to an existing local repository path
   - `model_path` to an existing local model path
   - `smoke_test_enabled=true` only when you are ready to run a local smoke probe

Text2MIDI remains disabled by default in the example config.

## 2) Run setup and smoke checks

- `scripts/dev.cmd check-text2midi-setup`
- `scripts/dev.cmd run-text2midi-smoke-test`

Expected unavailable-safe default (no local config):

- `text2midi_configured=False`
- `text2midi_available=False`
- `unavailable_reason=disabled_or_missing_local_config`

## 3) Generate prompt sketch scaffold report

- `scripts/dev.cmd generate-text2midi-prompt-sketch-scaffold`

Default unavailable report guarantees:

- `no_fake_generation=true`
- `sketches_generated=false`
- `scores_generated=false`
- `model_training_has_occurred=false`

## Routing role in this slice

Text2MIDI is explicitly scoped to:

- prompt sketch
- text-conditioned seed
- chord/key/tempo prompt conditioning
- user vocabulary future target
