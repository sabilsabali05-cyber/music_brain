# Privacy Leak Scan Report

- status: `ok`
- strict_mode: `False`
- new_public_leak_count: `0`
- pre_existing_historical_path_debt_count: `17`

## New Public Leaks
- none

## Pre-existing Historical Path Debt
- `docs/ABLETON_EXPORT_WORKFLOW.md` marker=`private_synplant_seed_paths` count=`1`
- `scripts/evaluate_mass_ingestion_readiness.py` marker=`sample_seed_records.jsonl` count=`1`
- `scripts/export_ableton_project_v1.py` marker=`private_synplant_seed_paths` count=`2`
- `scripts/generate_tangible_demo.py` marker=`sample_seed_records.jsonl` count=`1`
- `scripts/index_sample_library.py` marker=`sample_seed_records.jsonl` count=`1`
- `scripts/validate_ableton_project_export.py` marker=`private_synplant_seed_paths` count=`2`
- `tests/test_controlled_ingestion_sprint.py` marker=`C:\Users\` count=`1`
- `tests/test_controlled_ingestion_sprint.py` marker=`C:/Users/` count=`1`
- `tests/test_controlled_ingestion_sprint.py` marker=`OneDrive/Desktop/sounds` count=`1`
- `tests/test_controlled_ingestion_sprint.py` marker=`private_synplant_seed_paths` count=`2`
- `tests/test_mass_ingestion_readiness.py` marker=`sample_seed_records.jsonl` count=`1`
- `tests/test_mass_ingestion_readiness_foundation.py` marker=`C:/Users/` count=`1`
- `tests/test_privacy_leak_guard.py` marker=`C:\Users\` count=`1`
- `tests/test_privacy_leak_guard.py` marker=`C:/Users/` count=`3`
- `tests/test_privacy_leak_guard.py` marker=`OneDrive\Desktop\sounds` count=`1`
- `tests/test_privacy_leak_guard.py` marker=`private_synplant_seed_paths` count=`2`
- `tests/test_tangible_generation_demo.py` marker=`sample_seed_records.jsonl` count=`1`

## Limitations
- String-based scan only; semantic privacy issues may require manual review.
- Historical debt is reported but does not fail unless file is newly changed on this branch.
