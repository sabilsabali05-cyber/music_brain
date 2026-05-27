# Functionality Diff From Activation Branch

- target_branch: `cursor/music-brain-active`
- source_branch: `cursor/activate-model-witnesses-and-reroll-source-loops-v1`
- comparison: `git diff --name-status cursor/music-brain-active..cursor/activate-model-witnesses-and-reroll-source-loops-v1`
- safe_functionality_path_diff: `empty` (no files to restore by path)

## Category Buckets

- safe_code
  - `.gitignore`
- tests
  - none
- redacted_reports
  - `reports/integration/complete_song_pipeline_status.json`
  - `reports/integration/complete_song_pipeline_status.md`
  - `reports/integration/music_understanding_loop_status.json`
  - `reports/local_rendering/ableton_render_report.md`
  - `reports/local_rendering/chordpotion_reaper_render_report.json`
  - `reports/local_rendering/chordpotion_reaper_render_report.md`
  - `reports/local_rendering/chordpotion_transform_plan_report.md`
  - `reports/local_rendering/reaper_project_creation.json`
  - `reports/local_rendering/reaper_project_creation.md`
  - `reports/local_rendering/reaper_render_report.json`
  - `reports/local_rendering/reaper_render_report.md`
  - `reports/local_rendering/synplant_render_status.json`
  - `reports/local_rendering/synplant_render_status.md`
  - `reports/ratio_understanding/ratio_controlled_generation_v2_eval.json`
  - `reports/ratio_understanding/ratio_understanding_report.json`
  - `reports/ratio_understanding/ratio_understanding_report.md`
  - `reports/source_understanding/source_understanding_report.json`
  - `reports/taste_learning/feedback_ingestion_report.json`
  - `reports/taste_learning/feedback_ingestion_report.md`
  - `reports/taste_learning/ranked_midi_candidates_report.json`
- generated_midi_outputs
  - `outputs/reaper_projects/complete_song_v1/complete_song_v1.RPP`
- generated_json_outputs
  - `outputs/chordpotion_generation_v1/chordpotion_transform_plan.json`
  - `outputs/chordpotion_generation_v1/chordpotion_transform_plan.md`
  - `outputs/chordpotion_generation_v1/chordpotion_transform_plan_report.json`
  - `outputs/chordpotion_generation_v1/render_result.json`
  - `outputs/complete_song_v1/pipeline_execution_log.json`
  - `outputs/complete_song_v1/render_plan.json`
  - `outputs/complete_song_v1/render_plan.md`
  - `outputs/generated_wav_v1/render_plan.json`
  - `outputs/generated_wav_v1/render_plan.md`
  - `outputs/generated_wav_v1/render_result.json`
  - `outputs/music_understanding_loop_v1/generation_report.json`
  - `outputs/music_understanding_loop_v1/loop_status.json`
  - `outputs/render_ready_packs/chordpotion_generation_v1_chordpotion/report.json`
  - `outputs/render_ready_packs/complete_song_v1/render_plan.md`
  - `outputs/render_ready_packs/complete_song_v1/report.json`
  - `outputs/render_ready_packs/generated_wav_v1/render_plan.md`
- local_audio_or_snippets
  - none
- local_model_cache
  - none
- local_config
  - none
- private_path_risk
  - `outputs/render_ready_packs/complete_song_v1/vst_assignment.md`
  - `outputs/render_ready_packs/generated_wav_v1/vst_assignment.md`
- obsolete_or_duplicate
  - `.cursor/rules/branchless-development.md`
  - `reports/branch_hygiene/branchless_cursor_policy.md`
  - `reports/branch_hygiene/stash_recovery_inventory.json`
  - `reports/branch_hygiene/stash_recovery_inventory.md`
  - `reports/model_witnesses/branchless_active_witness_recovery_report.json`
  - `reports/model_witnesses/branchless_active_witness_recovery_report.md`
- unknown_review_needed
  - `datasets/ratio_understanding/ratio_observations.jsonl`

## Consolidation Notes

- No source-only safe functionality changes were detected for the requested model-witness, source-loop, midi-buddy, REAPER pack, or source-audio-taste directories/scripts.
- Recovery-by-path is a no-op on this branch pair.
