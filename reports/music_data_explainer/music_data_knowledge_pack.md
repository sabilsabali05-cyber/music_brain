# Music Data Knowledge Pack

- built_at: `2026-05-23T19:06:11.052147+00:00`
- performances_found: `2`
- generative_datasets_found: `2`
- known_task_types: `buildup_to_release, call_response, continuation, groove_continuation, harmony_continuation, infill_missing_region, melody_continuation, motif_transformation, phrase_continuation, section_transition`
- ready_for_controlled_batch: `True`
- ready_for_mass_ingestion: `False`
- ready_for_model_training: `False`

## Top Blockers
- symbolic corpus export is not training-ready
- historical privacy debt remains above zero

## Next Best Actions
- Fill a local controlled batch manifest with 1-5 authorized song files.
- Run controlled-batch plan + dry-run before execute mode.
- Prioritize review queue items to increase training-ready corpus coverage.
- Keep privacy scans clean for new public leaks before each merge.

## Evidence Sources
- `reports/mass_ingestion/mass_ingestion_readiness_report.json` (exists)
- `reports/privacy/privacy_leak_scan_report.json` (exists privacy_redacted)
- `reports/controlled_ingestion/controlled_batch_plan.json` (exists)
- `reports/model_training/symbolic_corpus_v1_report.json` (exists)
- `reports/review_queue/review_queue_summary.json` (exists)
- `reports/data_quality/training_candidate_quality_report.json` (exists)
- `reports/model_evaluation/generated_composition_scorecard.json` (exists)
- `outputs/tangible_generation_v1/generation_report.json` (exists)
- `outputs/tangible_generation_v1/demo_composition_plan.json` (exists)
- `outputs/ableton_project_v1/AI_Generated_Song_Project/track_setup.json` (exists)
- `outputs/ableton_project_v1/AI_Generated_Song_Project/export_report.json` (exists)
