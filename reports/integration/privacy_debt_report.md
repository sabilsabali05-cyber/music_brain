# Privacy Debt Report

- privacy_scan_status: `fail`
- new_public_leak_count: `4`
- pre_existing_historical_path_debt_count: `6`
- silent_ignore_allowed: `false`

## New Public Leaks (Must Fix)

- `reports/taste_learning/feedback_ingestion_report.json` marker=`C:/Users/`
- `reports/taste_learning/feedback_ingestion_report.json` marker=`C:/Users/izzyo`
- `reports/taste_learning/feedback_ingestion_report.md` marker=`C:/Users/`
- `reports/taste_learning/feedback_ingestion_report.md` marker=`C:/Users/izzyo`

## Classification

- Introduced during this consolidation validation run: `reports/taste_learning/feedback_ingestion_report.json`, `reports/taste_learning/feedback_ingestion_report.md`.
- Pre-existing historical debt remains unchanged in this pass.

## Historical Debt (Tracked)

- `docs/ABLETON_EXPORT_WORKFLOW.md`
- `scripts/evaluate_mass_ingestion_readiness.py`
- `scripts/export_ableton_project_v1.py`
- `scripts/generate_tangible_demo.py`
- `scripts/index_sample_library.py`
- `scripts/validate_ableton_project_export.py`

## Policy / Gates Applied In This Pass

- `scripts\dev.cmd check-privacy-leaks`
- direct marker grep scans for `C:/Users/|C:\\Users\\|cookies|session`
- `git ls-files config/local_vst_registry.local.json config/local_render_config.local.json config/beat_battle_ranked_site.local.json browser_state/ playwright_state/ site_sessions/ beat_battle_round_audio/ renders/`

## Handling Rule

Privacy failures are reported explicitly and remain visible; they are not silently ignored.
