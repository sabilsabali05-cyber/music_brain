# Branchless Active Witness Recovery Report

- branch: `cursor/music-brain-active`
- mode: branchless recovery without reroll/regeneration/model activation reruns
- stashes found: `19`
- stashes applied: `0`

## Recovery Scope

- Preserved branchless workflow and left all historical stashes intact.
- Recovered safety hardening in `.gitignore` for local witness/config paths:
  - `config/model_witnesses.local.json`
  - `local_model_witnesses/`
  - `local_model_witnesses_cache/`
- Added stash inventory and active witness recovery reports only; no raw audio/local config/model cache/private path content was restored.

## Must-Preserve Functionality Check

- BasicPitch persistent witness reporting: present (`reports/model_witnesses/model_witness_audit.json`, `reports/model_witnesses/model_witness_activation_plan.json`).
- Demucs persistent witness reporting: present (`reports/model_witnesses/model_witness_audit.json`, source separation witness reports).
- Model activation matrix: present (`reports/activation/full_model_activation_plan.json`).
- Source loop extraction pipeline: present (`features/source_loop_extraction`, `scripts/extract_source_audio_loops.py`).
- Exact source-loop MIDI buddy generation: present (`scripts/generate_midi_buddies_for_extracted_loops.py`).
- REAPER pack/export reporting: present (`scripts/export_source_loop_buddy_reaper_pack.py`, `reports/source_loop_midi_buddies/reaper_pack_report.*`).

## Local Validation (No Reruns)

- BasicPitch import works: `true`
- Cached BasicPitch smoke MIDI exists: `false`
- Cached BasicPitch smoke MIDI parses: `false`
- Demucs import works: `true`
- Cached Demucs stems exist: `false`
- Local active witness registry exists (intended report-level registry): `true`
  - `reports/model_witnesses/model_witness_audit.json`
  - `reports/model_witnesses/model_witness_activation_plan.json`
- Reports fully redacted from absolute paths: `false` (pre-existing privacy debt remains)

## Command Results

- `scripts/dev.cmd test`: `pass` (`534 passed, 2 warnings`)
- `scripts/dev.cmd check-privacy-leaks`: `fail`
  - `NEW_PUBLIC_LEAK_COUNT=11`
  - `PRE_EXISTING_HISTORICAL_PATH_DEBT_COUNT=6`

## Selective-Apply Decisions

- No stash was auto-applied to avoid restoring mixed/unsafe historical artifacts.
- `stash@{11}` marked unsafe and excluded due to local config/audio/model-cache/private-path risk.
- Mixed stashes with generated MIDI or large untracked payloads were left untouched for manual review.
