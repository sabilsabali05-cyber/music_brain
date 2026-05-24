# Privacy Leak Scan Report

- status: `fail`
- strict_mode: `False`
- new_public_leak_count: `5`
- pre_existing_historical_path_debt_count: `6`

## New Public Leaks
- `features/music_theory_understanding/theory_schema.py` marker=`C:/Users/` count=`1`
- `outputs/through_composed_story_100bpm_v2/generation_report.json` marker=`C:/Users/` count=`2`
- `outputs/through_composed_story_100bpm_v2/generation_report.json` marker=`C:/Users/izzyo` count=`2`
- `outputs/through_composed_story_100bpm_v2/generation_report.md` marker=`C:/Users/` count=`2`
- `outputs/through_composed_story_100bpm_v2/generation_report.md` marker=`C:/Users/izzyo` count=`2`

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
