# Integration Decision Log

- **complete_song_orchestrator** decision=`keep/wire`; rationale=`required one-command local pipeline with truthful statuses`; evidence=`scripts/generate_complete_song_wav.py`, `scripts/dev.ps1`.
- **deterministic_stem_generation** decision=`keep/wire`; rationale=`already local and deterministic`; evidence=`scripts/generate_chordpotion_ready_skeleton.py`.
- **chordpotion_optional_path** decision=`keep/wire`; rationale=`optional branch with explicit missing-config fallback`; evidence=`scripts/build_chordpotion_transform_plan.py`, `scripts/audition_chordpotion_presets.py`, `scripts/render_chordpotion_with_reaper.py`.
- **trained_preset_selector_usage** decision=`local-only`; rationale=`only true when local model artifact and training report both confirm`; evidence=`artifacts/model_training/chordpotion_preset_selector/model.json`, `reports/model_training/chordpotion_preset_selector_training_report.md`.
- **automatic_training** decision=`retire`; rationale=`complete command must not train automatically`; evidence=`scripts/generate_complete_song_wav.py` training gate.
- **reaper_cli_auto_render** decision=`experimental`; rationale=`backend remains mostly planned execution`; evidence=`features/local_rendering/reaper_backend.py`.
- **assisted_pack_fallback** decision=`keep/wire`; rationale=`needed when local render cannot be verified`; evidence=`features/local_rendering/ableton_backend.py`, `scripts/export_ableton_render_pack.py`.
- **local_config_reporting** decision=`keep/wire`; rationale=`booleans and blocker labels only, no private path leaks`; evidence=`reports/integration/local_config_blockers.*`.
- **cloud_activation_tasks** decision=`postpone`; rationale=`no cloud calls allowed in this integration`; evidence=`scripts/dev.ps1` cloud tasks.
- **tracked_generated_outputs_growth** decision=`retire`; rationale=`avoid committing additional rendered/raw outputs`; evidence=`docs/GENERATED_ARTIFACT_POLICY.md`.
