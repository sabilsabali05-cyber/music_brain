# Privacy Leak Scan Report

- status: `fail`
- strict_mode: `False`
- new_public_leak_count: `12`
- pre_existing_historical_path_debt_count: `6`

## New Public Leaks
- `datasets/ratio_understanding/ratio_observations.jsonl` marker=`C:/Users/` count=`56`
- `datasets/ratio_understanding/ratio_observations.jsonl` marker=`C:/Users/izzyo` count=`56`
- `outputs/ratio_controlled_song_v1/generation_report.md` marker=`C:/Users/` count=`1`
- `outputs/ratio_controlled_song_v1/generation_report.md` marker=`C:/Users/izzyo` count=`1`
- `reports/ratio_understanding/ratio_understanding_report.json` marker=`C:/Users/` count=`6`
- `reports/ratio_understanding/ratio_understanding_report.json` marker=`C:/Users/izzyo` count=`6`
- `reports/ratio_understanding/ratio_understanding_report.md` marker=`C:/Users/` count=`6`
- `reports/ratio_understanding/ratio_understanding_report.md` marker=`C:/Users/izzyo` count=`6`
- `reports/taste_learning/feedback_ingestion_report.json` marker=`C:/Users/` count=`1`
- `reports/taste_learning/feedback_ingestion_report.json` marker=`C:/Users/izzyo` count=`1`
- `reports/taste_learning/feedback_ingestion_report.md` marker=`C:/Users/` count=`1`
- `reports/taste_learning/feedback_ingestion_report.md` marker=`C:/Users/izzyo` count=`1`

## Pre-existing Historical Path Debt
- `docs/ABLETON_EXPORT_WORKFLOW.md` marker=`private_synplant_seed_paths` count=`1`
- `scripts/evaluate_mass_ingestion_readiness.py` marker=`sample_seed_records.jsonl` count=`1`
- `scripts/export_ableton_project_v1.py` marker=`private_synplant_seed_paths` count=`2`
- `scripts/generate_tangible_demo.py` marker=`sample_seed_records.jsonl` count=`1`
- `scripts/index_sample_library.py` marker=`sample_seed_records.jsonl` count=`1`
- `scripts/validate_ableton_project_export.py` marker=`private_synplant_seed_paths` count=`2`

## Limitations
- String-based scan only; semantic privacy issues may require manual review.
- Historical debt is reported but does not fail unless file is newly changed on this branch.
