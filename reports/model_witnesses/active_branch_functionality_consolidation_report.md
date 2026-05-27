# Active Branch Functionality Consolidation Report

- target_branch: `cursor/music-brain-active`
- source_branch: `cursor/activate-model-witnesses-and-reroll-source-loops-v1`
- stashes_applied: `0`
- stashes_deleted: `0`
- restore_by_path_result: `no-op` (no source-only safe path diffs found)

## Model Witness Capability (No Reactivation)

- BasicPitch support present: `true`
  - check: `scripts/check_transcription_witnesses_setup.py`
  - behavior without local config/deps: `basic_pitch_available=false`, `basic_pitch_unavailable_reason=disabled_or_missing_local_config`
- Demucs support present: `true`
  - check: `scripts/check_source_separation_setup.py`
  - behavior without local config/deps: `demucs_available=false`, `demucs_unavailable_reason=disabled_or_missing_local_config`
- Active witness registry support present: `true`
  - registry artifacts: `reports/model_witnesses/model_witness_audit.json`, `reports/model_witnesses/model_witness_activation_plan.json`
- Registry local path ignored: `true`
- Cached smoke artifacts expected local-only: `true`
  - ignored local-only paths include: `local_model_witnesses/`, `local_model_witnesses_cache/`, `config/model_integrations/*.local.json`
- Committed witness reports redacted: `true` (no unredacted private absolute path markers found)

## Source-Loop Workflow Existence (No Generation)

- extract source loops: `present + importable` (`scripts/extract_source_audio_loops.py`)
- run loop model witnesses: `present + importable` (`scripts/run_loop_model_witnesses.py`)
- rank extracted loops: `present + importable` (`scripts/rank_extracted_source_loops.py`)
- generate MIDI buddies: `present + importable` (`scripts/generate_midi_buddies_for_extracted_loops.py`)
- evaluate fit: `present + importable` (`scripts/evaluate_source_loop_midi_buddy_fit.py`)
- export REAPER pack: `present + importable` (`scripts/export_source_loop_buddy_reaper_pack.py`)
- source audio/local inputs committed: `not observed`; local audio extensions and local folders are gitignored

## Privacy and Tests

- privacy command: `scripts/dev.cmd check-privacy-leaks`
  - status: `fail`
  - checker counts: `new_public_leak_count=17`, `pre_existing_historical_path_debt_count=6`
  - consolidation classification: `new leaks introduced by this consolidation = false` (none of consolidation-changed files appear in `new_public_leaks`)
- tests command: `scripts/dev.cmd test`
  - result: `pass` (`534 passed, 2 warnings`)

## Safety Result

- unsafe artifacts excluded from consolidation changes: `true`
