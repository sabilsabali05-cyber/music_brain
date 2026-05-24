# Transcription Witnesses Local Setup

This vertical slice adds unavailable-safe scaffolds for YourMT3 and Basic Pitch transcription witnesses.

## Guarantees

- `yourmt3_available=false` by default
- `basic_pitch_available=false` by default
- `transcription_performed=false`
- `model_training_has_occurred=false`
- `witness_policy=witness_not_truth`
- No audio processing, no model downloads, and no fake transcription outputs

## Commands

- `scripts/dev.cmd check-transcription-witnesses-setup`
- `scripts/dev.cmd run-transcription-witnesses-smoke-tests`
- `scripts/dev.cmd plan-transcription-witnesses`

## Local Opt-In (Future Work)

1. Copy `config/model_integrations/model_integrations.example.json` to `config/model_integrations/model_integrations.local.json`.
2. Keep `models.yourmt3.enabled=false` and `models.basic_pitch.enabled=false` until explicit witness execution wiring is approved.
3. Provide local paths only in local config; never commit local config files.

## Safety Notes

- Witness outputs are never treated as truth labels.
- This slice intentionally does not execute transcription.
- Any future execution path must require explicit user command plus explicit input path.
