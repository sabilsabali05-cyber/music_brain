# Loose Threads Inventory

Generated for branch `cursor/consolidate-synplant-and-beatbattle-v1`.

## Branch Status

- Canonical active branch: `cursor/consolidate-synplant-and-beatbattle-v1` (active).
- Superseded branch: `cursor/music-understanding-taste-loop-v1`.
- Integrated branch: `cursor/synplant-local-render-target-v1`.
- Integrated branch: `cursor/beat-battle-ranked-site-automation-v1`.
- Retired/superseded branch: `cursor/chordpotion-intelligent-preset-selector-v1`.
- Supersession reason: fully contained in the canonical branch line with no unique commits/files.

## Inventory Items

- `source_understanding_contract` (`docs/SOURCE_AUDIO_UNDERSTANDING_CONTRACT.md`) status=`new_core`; strict confidence/evidence policy; command=`scripts/dev.cmd build-source-understanding-records`; blockers=`none`; privacy_risk=`low`; artifact_risk=`low`; next=`enforce_in_builder_and_tests`.
- `source_understanding_builder` (`scripts/build_source_understanding_records.py`) status=`new_core`; builds source understanding records from local corpus/intelligence/theory/feedback artifacts; command=`scripts/dev.cmd build-source-understanding-records`; blockers=`none`; privacy_risk=`low`; artifact_risk=`medium`; next=`reuse_as_single_source_of_truth`.
- `source_to_generation_mapper` (`features/source_understanding/source_to_generation.py`) status=`new_core`; maps understanding fields to generation controls; command=`scripts/dev.cmd generate-ranked-midi-candidates`; blockers=`none`; privacy_risk=`low`; artifact_risk=`low`; next=`keep_and_extend`.
- `taste_feedback_schema` (`features/taste_learning/taste_feedback_schema.py`) status=`new_core`; defines core taste labels and authorization gate; command=`scripts/dev.cmd ingest-output-feedback`; blockers=`none`; privacy_risk=`low`; artifact_risk=`low`; next=`treat_as_contract`.
- `composition_taste_ranker` (`features/taste_learning/composition_ranker.py`) status=`new_core`; heuristic-only below 20 labels and tiny local trained ranker at/above 20 labels; command=`scripts/dev.cmd train-composition-taste-ranker`; blockers=`needs >=20 authorized labels for trained mode`; privacy_risk=`low`; artifact_risk=`medium`; next=`collect_authorized_feedback`.
- `multi_candidate_midi_generation` (`scripts/generate_ranked_midi_candidates.py`) status=`new_core`; generates and ranks >=8 candidates with feature extraction; command=`scripts/dev.cmd generate-ranked-midi-candidates`; blockers=`none`; privacy_risk=`low`; artifact_risk=`medium`; next=`reuse_in_loop`.
- `music_understanding_loop_orchestrator` (`scripts/run_music_understanding_loop.py`) status=`new_core`; orchestrates understanding -> generation -> review -> learning status; command=`scripts/dev.cmd run-music-understanding-loop`; blockers=`none`; privacy_risk=`low`; artifact_risk=`medium`; next=`set_as_primary_loop`.
- `feedback_ingestion` (`scripts/ingest_output_feedback.py`) status=`new_core`; ingests only authorized taste feedback rows; command=`scripts/dev.cmd ingest-output-feedback`; blockers=`none`; privacy_risk=`low`; artifact_risk=`low`; next=`feed_ranker_training`.
- `chordpotion_optional_role` (`reports/chordpotion/chordpotion_role_in_pipeline.md`) status=`updated_core_policy`; ChordPotion optional fallback only; command=`scripts/dev.cmd run-music-understanding-loop`; blockers=`none`; privacy_risk=`low`; artifact_risk=`low`; next=`keep_optional`.
- `synplant_optional_sound_design_role` (`docs/SYNPLANT_AND_SOUND_DESIGN_ROLE.md`) status=`updated_core_policy`; Synplant not required for core loop truth; command=`none`; blockers=`none`; privacy_risk=`low`; artifact_risk=`low`; next=`preserve_policy`.
- `existing_complete_song_pipeline` (`scripts/generate_complete_song_wav.py`) status=`related_existing`; render-focused local full pipeline; command=`scripts/dev.cmd generate-complete-song-wav`; blockers=`not understanding/taste-focused`; privacy_risk=`medium`; artifact_risk=`medium`; next=`keep_separate`.
- `cloud_activation_workstreams` (`scripts/dev.ps1` cloud/modal tasks) status=`related_out_of_scope`; cloud-oriented scaffolding not used in this loop; command=`not_used_in_new_loop`; blockers=`new loop forbids cloud`; privacy_risk=`medium`; artifact_risk=`medium`; next=`explicitly_not_called`.

## Discovered Related Untracked/Modified Buckets

- Existing local render/chordpotion generated output trees remain present and are treated as unrelated to the new core loop.
- Existing private local config surfaces remain blocked from committed output expansion.
- Existing cloud/model activation scripts remain available but isolated from `run-music-understanding-loop`.
