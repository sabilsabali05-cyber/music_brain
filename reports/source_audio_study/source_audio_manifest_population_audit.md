# Source Audio Manifest Population Audit

- old_source_items_considered_from_trust_glob: `4`
- new_manifest_rows_created_from_authorized_roots: `5686`
- supported_files_found_under_allowed_roots: `5686`

## Why only 4 rows existed
- Old logic only populated manifest rows from trust-audit JSON files under features/performances/*/*/trust/training_data_audit.json. That branch had 4 such files, so only 4 rows were produced.

## Code path change
- old: `scripts/build_source_audio_study_manifest.py::build_manifest -> ROOT_DIR.glob(TRUST_GLOB) -> _build_item(SourceAudioStudyItem)`
- new: `scripts/build_source_audio_study_manifest.py::build_manifest -> _discover_authorized_sources -> _build_manifest_row -> _select_controlled_batch`
