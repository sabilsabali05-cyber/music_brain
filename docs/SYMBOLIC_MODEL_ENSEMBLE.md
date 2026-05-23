# Symbolic Model Ensemble

This document defines the symbolic ensemble integration for `music_brain`.

## Backend roles

- Moonbeam = main symbolic generator for composition, continuation, and infill.
- MusicBERT = symbolic understanding and evaluation backend (similarity, ranking, fit checks).
- MIDI-GPT = controllable multitrack variation backend (drums, groove, density, track-level infill).
- Text2MIDI = prompt-to-MIDI sketch backend for first-pass symbolic ideas.
- example_retrieval = fallback-only prototype when real model backends are unavailable.

## Availability and safety

- All real model backends are optional and disabled by default.
- Backends return explicit unavailable status with exact reason when configuration/dependencies/model paths/smoke checks fail.
- No silent fallback from one real backend to another.
- If all real backends are unavailable, the orchestrator can use `example_retrieval` fallback and marks:
  - `example_retrieval_fallback=true`
  - `no_real_symbolic_backend_available=true`
  - `not_model_trained_on_user_data=true`

## Configuration

- Example template: `config/symbolic_backends/symbolic_backends.example.json`
- Local machine config: `config/symbolic_backends/symbolic_backends.local.json` (gitignored)
- No model weights are committed to this repo.

## Outputs

- Ensemble generation:
  - `outputs/symbolic_ensemble_v1/ensemble_generation_report.json`
  - `outputs/symbolic_ensemble_v1/ensemble_generation_report.md`
  - `outputs/symbolic_ensemble_v1/backend_availability_report.json`
  - `outputs/symbolic_ensemble_v1/backend_availability_report.md`
  - `outputs/symbolic_ensemble_v1/generated_candidates/*`
  - `outputs/symbolic_ensemble_v1/selected_candidate.mid`
  - `outputs/symbolic_ensemble_v1/selected_candidate_ir.json`
- Availability checker:
  - `reports/symbolic_backends/backend_availability_report.json`
  - `reports/symbolic_backends/backend_availability_report.md`
- Optional Ableton scaffold export:
  - `outputs/ableton_project_symbolic_ensemble_v1/`

## Current implementation boundary

- Adapters currently implement configuration/dependency/path/smoke gating plus conversion hooks.
- Real inference hooks are intentionally left unimplemented unless local backend runtime is integrated.
- No training has happened yet in this integration.

## Future path

- Add user preference ranker for symbolic candidates.
- Use preference/ranking signals to guide generator selection and conditioning.
- Add real backend inference connectors after local runtime verification.
