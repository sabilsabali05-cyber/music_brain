# Database Artifact Inventory

- artifact_count: `48`

## `datasets/feedback/generation_feedback.jsonl`
- file_type: `jsonl`
- row_count: `1`
- schema_fields: `approved_for_training_weighting, comment, feedback_id, rating, target`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `datasets/model_training/symbolic_corpus_v1/exclude.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/model_training/symbolic_corpus_v1/review.jsonl`
- file_type: `jsonl`
- row_count: `40`
- schema_fields: `authorization, quality_bucket, quality_score, queue_id, training_allowed`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `40`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `40`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `40`

## `datasets/model_training/symbolic_corpus_v1/train.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/model_training/symbolic_corpus_v1/validation.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/review_queue/review_queue_v1.jsonl`
- file_type: `jsonl`
- row_count: `40`
- schema_fields: `authorization, exclude, provenance, queue_id, review_status, source_record_id, training_allowed`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `40`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `40`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `40`

## `datasets/training_exports/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/accepted_records.jsonl`
- file_type: `jsonl`
- row_count: `27`
- schema_fields: `audio_ref, confidence, confidence_reason, consensus_refs, content_state, counterpoint_summary, duration_seconds, end_seconds, excluded_fields, export_record_id, export_split, external_feature_refs, feature_refs, granularity, grid_confidence, inclusion_reason, interval_class_summary, label_status, limitations, local_tempo_bpm, merged_midi_ref, meter_time_refs, midi_ref, model_source_refs, note_density_polyphony, note_on_count, note_on_density_per_second, performance_id, pitch_class_histogram, pitch_class_summary, pitch_harmony_refs, pitch_range, polyphonic_density, provenance, pulse_stability, recommended_training_weight, record_id, register_summary, review_recommendations, route_confidence, routing_refs, segment_id, segment_run_id, silence_ratio_proxy, sonority_type_candidate, source_record_id, start_seconds, subdivision_type, theory_source_refs, training_weight, transcription_reliability_score, trust_tier, tuning_summary, velocity_mean, velocity_std, verification_status, voice_count_estimate, voice_leading_summary, voicing_span, window_id, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `27`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `27`
- missing_policy_fields_count: `27`
- missing_label_fields_count: `27`

## `datasets/training_exports/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/audio_midi_only_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/export_manifest.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `accepted_observation_count, audio_midi_only_count, consensus_status, counts_per_split, created_at, excluded_field_summary, external_feature_refs, external_witnesses_available, external_witnesses_missing, field_trust_policy_version, inclusion_rules_used, label_upgrade_candidates_path, limitations, meter_time_features_path, model_consensus_ref, model_sources_used, performance_id, pipeline_git_commit, pitch_harmony_features_path, quarantined_count, review_recommendations, review_required_count, routing_refs, segment_run_id, source_ai_record_count, source_feature_pack_path, theory_sources_used, weak_label_count, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `datasets/training_exports/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/quarantined_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/review_required_records.jsonl`
- file_type: `jsonl`
- row_count: `376`
- schema_fields: `best_rhythm_family_match, chord_movement_refs, confidence, confidence_reason, consensus_refs, content_state, counterpoint_summary, created_at, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, external_conflict_warnings, external_feature_refs, external_key_summary, external_tag_summary, external_tempo_summary, extractor_name, feature_refs, feature_version, granularity, grid_confidence, harmony_pattern_index_refs, inclusion_reason, input_features, interval_class_summary, label, label_status, label_upgrade_candidate_refs, label_upgrade_candidates_path, limitations, local_tempo_bpm, macro_section_candidate, meter_hypothesis_candidates, meter_time_ambiguity, meter_time_refs, microtiming_summary, model_source_refs, motif_group_refs, motif_refs, performance_id, pitch_class_summary, pitch_harmony_refs, pitch_range, pulse_stability, record_id, record_type, register_summary, review_reasons, review_recommendations, review_required, rhythm_family_match_refs, route_confidence, routing_refs, segment_run_id, sonority_type_candidate, source_artifact_paths, source_name, source_record_id, start_seconds, subdivision_type, text_summary, theory_source_refs, token_pattern_compact, training_weight, trust_tier, tuning_summary, unknown_pattern, vamp_refs, verification_status, verified_by, voice_leading_summary, window_id, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `376`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `376`
- missing_policy_fields_count: `376`
- missing_label_fields_count: `376`

## `datasets/training_exports/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/weak_label_records.jsonl`
- file_type: `jsonl`
- row_count: `403`
- schema_fields: `confidence, confidence_reason, consensus_refs, content_state, counterpoint_summary, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, external_feature_refs, granularity, grid_confidence, inclusion_reason, interval_class_summary, label, label_status, label_upgrade_candidate_refs, label_upgrade_candidates_path, limitations, local_tempo_bpm, macro_section_candidate, meter_hypothesis_candidates, meter_time_ambiguity, meter_time_refs, microtiming_summary, model_source_refs, performance_id, pitch_class_summary, pitch_harmony_refs, pitch_range, pulse_stability, record_id, register_summary, review_recommendations, route_confidence, routing_refs, segment_run_id, sonority_type_candidate, source_record_id, source_record_ref, start_seconds, subdivision_type, theory_source_refs, training_weight, trust_tier, tuning_summary, voice_leading_summary, weak_fields, window_id, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `403`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `403`
- missing_policy_fields_count: `403`
- missing_label_fields_count: `403`

## `datasets/training_exports/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/accepted_records.jsonl`
- file_type: `jsonl`
- row_count: `109`
- schema_fields: `audio_ref, confidence, confidence_reason, consensus_refs, content_state, counterpoint_summary, duration_seconds, end_seconds, excluded_fields, export_record_id, export_split, external_feature_refs, feature_refs, granularity, grid_confidence, inclusion_reason, interval_class_summary, label_status, limitations, local_tempo_bpm, merged_midi_ref, meter_time_refs, midi_ref, model_source_refs, note_density_polyphony, note_on_count, note_on_density_per_second, performance_id, pitch_class_histogram, pitch_class_summary, pitch_harmony_refs, pitch_range, polyphonic_density, provenance, pulse_stability, recommended_training_weight, record_id, register_summary, review_recommendations, route_confidence, routing_refs, segment_id, segment_run_id, silence_ratio_proxy, sonority_type_candidate, source_record_id, start_seconds, subdivision_type, theory_source_refs, training_weight, transcription_reliability_score, trust_tier, tuning_summary, velocity_mean, velocity_std, verification_status, voice_count_estimate, voice_leading_summary, voicing_span, window_id, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `109`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `109`
- missing_policy_fields_count: `109`
- missing_label_fields_count: `109`

## `datasets/training_exports/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/audio_midi_only_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/export_manifest.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `accepted_observation_count, audio_midi_only_count, consensus_status, counts_per_split, created_at, excluded_field_summary, external_feature_refs, external_witnesses_available, external_witnesses_missing, field_trust_policy_version, inclusion_rules_used, label_upgrade_candidates_path, limitations, meter_time_features_path, model_consensus_ref, model_sources_used, performance_id, pipeline_git_commit, pitch_harmony_features_path, quarantined_count, review_recommendations, review_required_count, routing_refs, segment_run_id, source_ai_record_count, source_feature_pack_path, theory_sources_used, weak_label_count, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `datasets/training_exports/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/quarantined_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/review_required_records.jsonl`
- file_type: `jsonl`
- row_count: `1664`
- schema_fields: `best_rhythm_family_match, chord_movement_refs, confidence, confidence_reason, consensus_refs, content_state, counterpoint_summary, created_at, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, external_feature_refs, extractor_name, feature_refs, feature_version, granularity, grid_confidence, harmony_pattern_index_refs, inclusion_reason, input_features, interval_class_summary, label, label_status, label_upgrade_candidate_refs, label_upgrade_candidates_path, limitations, local_tempo_bpm, macro_section_candidate, meter_hypothesis_candidates, meter_time_ambiguity, meter_time_refs, microtiming_summary, model_source_refs, motif_group_refs, motif_refs, performance_id, pitch_class_summary, pitch_harmony_refs, pitch_range, pulse_stability, record_id, record_type, register_summary, review_reasons, review_recommendations, review_required, rhythm_family_match_refs, route_confidence, routing_refs, segment_run_id, sonority_type_candidate, source_artifact_paths, source_name, source_record_id, start_seconds, subdivision_type, text_summary, theory_source_refs, token_pattern_compact, training_weight, trust_tier, tuning_summary, unknown_pattern, vamp_refs, verification_status, verified_by, voice_leading_summary, window_id, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1664`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1664`
- missing_policy_fields_count: `1664`
- missing_label_fields_count: `1664`

## `datasets/training_exports/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/weak_label_records.jsonl`
- file_type: `jsonl`
- row_count: `1773`
- schema_fields: `confidence, confidence_reason, consensus_refs, content_state, counterpoint_summary, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, external_feature_refs, granularity, grid_confidence, inclusion_reason, interval_class_summary, label, label_status, label_upgrade_candidate_refs, label_upgrade_candidates_path, limitations, local_tempo_bpm, macro_section_candidate, meter_hypothesis_candidates, meter_time_ambiguity, meter_time_refs, microtiming_summary, model_source_refs, performance_id, pitch_class_summary, pitch_harmony_refs, pitch_range, pulse_stability, record_id, register_summary, review_recommendations, route_confidence, routing_refs, segment_run_id, sonority_type_candidate, source_record_id, source_record_ref, start_seconds, subdivision_type, theory_source_refs, training_weight, trust_tier, tuning_summary, voice_leading_summary, weak_fields, window_id, witness_agreement_summary, witness_conflict_warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1773`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1773`
- missing_policy_fields_count: `1773`
- missing_label_fields_count: `1773`

## `datasets/training_exports/20260522T150019594510_Pulgas_and_Salami_Rose_Joe_Louis_-_When_dc83c53371/20260522T150054174749_audio_structure_v1/accepted_records.jsonl`
- file_type: `jsonl`
- row_count: `9`
- schema_fields: `audio_ref, confidence, confidence_reason, duration_seconds, end_seconds, excluded_fields, export_record_id, export_split, feature_refs, granularity, inclusion_reason, label_status, limitations, merged_midi_ref, midi_ref, note_on_count, note_on_density_per_second, performance_id, pitch_class_histogram, polyphonic_density, provenance, recommended_training_weight, record_id, segment_id, segment_run_id, silence_ratio_proxy, source_record_id, start_seconds, training_weight, transcription_reliability_score, trust_tier, velocity_mean, velocity_std, verification_status, window_id`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `9`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `9`
- missing_policy_fields_count: `9`
- missing_label_fields_count: `9`

## `datasets/training_exports/20260522T150019594510_Pulgas_and_Salami_Rose_Joe_Louis_-_When_dc83c53371/20260522T150054174749_audio_structure_v1/audio_midi_only_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260522T150019594510_Pulgas_and_Salami_Rose_Joe_Louis_-_When_dc83c53371/20260522T150054174749_audio_structure_v1/export_manifest.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `accepted_observation_count, audio_midi_only_count, counts_per_split, created_at, excluded_field_summary, field_trust_policy_version, inclusion_rules_used, limitations, performance_id, pipeline_git_commit, quarantined_count, review_required_count, segment_run_id, source_ai_record_count, source_feature_pack_path, weak_label_count`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `datasets/training_exports/20260522T150019594510_Pulgas_and_Salami_Rose_Joe_Louis_-_When_dc83c53371/20260522T150054174749_audio_structure_v1/quarantined_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260522T150019594510_Pulgas_and_Salami_Rose_Joe_Louis_-_When_dc83c53371/20260522T150054174749_audio_structure_v1/review_required_records.jsonl`
- file_type: `jsonl`
- row_count: `142`
- schema_fields: `best_rhythm_family_match, chord_movement_refs, confidence, confidence_reason, created_at, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, extractor_name, feature_refs, feature_version, granularity, harmony_pattern_index_refs, inclusion_reason, input_features, label, label_status, limitations, motif_group_refs, motif_refs, performance_id, record_id, record_type, review_reasons, review_required, rhythm_family_match_refs, segment_run_id, source_artifact_paths, source_name, source_record_id, start_seconds, text_summary, token_pattern_compact, training_weight, trust_tier, unknown_pattern, vamp_refs, verification_status, verified_by, window_id`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `142`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `142`
- missing_policy_fields_count: `142`
- missing_label_fields_count: `142`

## `datasets/training_exports/20260522T150019594510_Pulgas_and_Salami_Rose_Joe_Louis_-_When_dc83c53371/20260522T150054174749_audio_structure_v1/weak_label_records.jsonl`
- file_type: `jsonl`
- row_count: `151`
- schema_fields: `confidence, confidence_reason, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, granularity, inclusion_reason, label, label_status, limitations, performance_id, record_id, segment_run_id, source_record_id, source_record_ref, start_seconds, training_weight, trust_tier, weak_fields, window_id`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `151`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `151`
- missing_policy_fields_count: `151`
- missing_label_fields_count: `151`

## `datasets/training_exports/20260522T150238990635_Pulgas_and_Salami_Rose_Joe_Louis_-_When_1f6c273076/20260522T150322987308_audio_structure_v1/accepted_records.jsonl`
- file_type: `jsonl`
- row_count: `7`
- schema_fields: `audio_ref, confidence, confidence_reason, duration_seconds, end_seconds, excluded_fields, export_record_id, export_split, feature_refs, granularity, inclusion_reason, label_status, limitations, merged_midi_ref, midi_ref, note_on_count, note_on_density_per_second, performance_id, pitch_class_histogram, polyphonic_density, provenance, recommended_training_weight, record_id, segment_id, segment_run_id, silence_ratio_proxy, source_record_id, start_seconds, training_weight, transcription_reliability_score, trust_tier, velocity_mean, velocity_std, verification_status, window_id`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `7`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `7`
- missing_policy_fields_count: `7`
- missing_label_fields_count: `7`

## `datasets/training_exports/20260522T150238990635_Pulgas_and_Salami_Rose_Joe_Louis_-_When_1f6c273076/20260522T150322987308_audio_structure_v1/audio_midi_only_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260522T150238990635_Pulgas_and_Salami_Rose_Joe_Louis_-_When_1f6c273076/20260522T150322987308_audio_structure_v1/export_manifest.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `accepted_observation_count, audio_midi_only_count, counts_per_split, created_at, excluded_field_summary, field_trust_policy_version, inclusion_rules_used, limitations, performance_id, pipeline_git_commit, quarantined_count, review_required_count, segment_run_id, source_ai_record_count, source_feature_pack_path, weak_label_count`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `datasets/training_exports/20260522T150238990635_Pulgas_and_Salami_Rose_Joe_Louis_-_When_1f6c273076/20260522T150322987308_audio_structure_v1/quarantined_records.jsonl`
- file_type: `jsonl`
- row_count: `0`
- schema_fields: ``
- date_range: ``
- accepted_count: `0`
- review_required_count: `0`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `0`
- missing_policy_fields_count: `0`
- missing_label_fields_count: `0`

## `datasets/training_exports/20260522T150238990635_Pulgas_and_Salami_Rose_Joe_Louis_-_When_1f6c273076/20260522T150322987308_audio_structure_v1/review_required_records.jsonl`
- file_type: `jsonl`
- row_count: `96`
- schema_fields: `best_rhythm_family_match, chord_movement_refs, confidence, confidence_reason, created_at, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, extractor_name, feature_refs, feature_version, granularity, harmony_pattern_index_refs, inclusion_reason, input_features, label, label_status, limitations, motif_group_refs, motif_refs, performance_id, record_id, record_type, review_reasons, review_required, rhythm_family_match_refs, segment_run_id, source_artifact_paths, source_name, source_record_id, start_seconds, text_summary, token_pattern_compact, training_weight, trust_tier, unknown_pattern, vamp_refs, verification_status, verified_by, window_id`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `96`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `96`
- missing_policy_fields_count: `96`
- missing_label_fields_count: `96`

## `datasets/training_exports/20260522T150238990635_Pulgas_and_Salami_Rose_Joe_Louis_-_When_1f6c273076/20260522T150322987308_audio_structure_v1/weak_label_records.jsonl`
- file_type: `jsonl`
- row_count: `103`
- schema_fields: `confidence, confidence_reason, duration_seconds, end_seconds, evidence_refs, excluded_fields, export_record_id, export_split, granularity, inclusion_reason, label, label_status, limitations, performance_id, record_id, segment_run_id, source_record_id, source_record_ref, start_seconds, training_weight, trust_tier, weak_fields, window_id`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `103`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `103`
- missing_policy_fields_count: `103`
- missing_label_fields_count: `103`

## `datasets/training_exports/training_exports_summary.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `accepted_percentage, performances_by_dataset_inclusion_decision, performances_with_quarantined_records, performances_with_zero_accepted_records, review_required_percentage, top_limitations_or_warnings, total_accepted_observation_records, total_audio_midi_only_records, total_performances, total_quarantined_records, total_review_required_records, total_source_ai_records, total_weak_label_records`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `outputs/ballad_2min_v2_review_regen/review_regeneration_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `kept_stems, regenerated_stems, status`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/batches/20260522T023234490710_batch_trusted_export_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `config, created_at, dataset_summary_json_path, dataset_summary_md_path, files_discovered, inbox_folder, performance_results, performances_planned, summary`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/batches/20260522T150413226738_batch_trusted_export_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `config, created_at, dataset_summary_json_path, dataset_summary_md_path, files_discovered, inbox_folder, performance_results, performances_planned, summary`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/batches/20260522T152242794032_batch_trusted_export_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `config, created_at, dataset_summary_json_path, dataset_summary_md_path, files_discovered, inbox_folder, performance_results, performances_planned, summary`
- date_range: `2026-05-22..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/controlled_ingestion/controlled_batch_plan.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `allow_modal, allow_training_export, allow_transcription, authorization_required, authorized_song_files_count, batch_goal, batch_id, errors, estimated_artifacts, estimated_review_burden, limitations, manifest_path, max_sample_library_items, max_song_files, provenance, requested_sample_items, song_files_count, source_authorization, status, strict_mode, warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/controlled_ingestion/controlled_batch_run_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `batch_id, errors, execute_requested, execution_notes, limitations, manifest_path, manifest_path_redacted, permission_flags, planner_status, provenance, requested_actions, runnable_item_count, skipped_unauthorized, skipped_unauthorized_count, status, warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/controlled_ingestion/runs/controlled_batch_example_v1/controlled_batch_run_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `batch_id, errors, execute_requested, execution_notes, limitations, manifest_path, manifest_path_redacted, permission_flags, planner_status, provenance, requested_actions, runnable_item_count, skipped_unauthorized, skipped_unauthorized_count, status, warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/controlled_ingestion/runs/controlled_batch_example_v1/run_state.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `batch_id, errors, execute_requested, manifest_path, manifest_path_redacted, runnable_item_count, skipped_unauthorized_count, status, warnings`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/data_quality/training_candidate_quality_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `candidate_count, exclude_count, high_quality_count, review_count, status`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/dataset_quality/dataset_quality_yield_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `dataset_recommendations, dataset_risk_flag_counts, performance_reports, total_performances_scanned`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/mass_ingestion/mass_ingestion_readiness_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `blockers, controlled_batch_plan, created_at, dataset_scale_estimate, feature_layer_readiness, gates, limitations, model_training_readiness, ready_for_controlled_batch, ready_for_mass_ingestion, ready_for_model_training, recommended_next_batch_size, required_next_actions, review_burden_estimate, risk_flags, sound_library_readiness, strengths, top_blockers, top_strengths`
- date_range: `2026-05-23..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/model_training/personalized_training_readiness.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `blockers, data_snapshot, first_recommended_trainable_subsystem, generated_at, limitations, model_training_has_occurred, plan, status, subsystem_readiness`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/model_training/symbolic_corpus_v1_report.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `exclude_count, limitations, review_count, status, train_count, training_ready, validation_count`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/privacy/historical_path_scrub_plan.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `finding_count, findings, limitations, provenance, replacements_applied, safe_apply_candidate_count, safe_apply_candidates, skipped_candidate_count, skipped_candidates, status`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`

## `reports/privacy/privacy_leak_scan_report.json`
- file_type: `json`
- row_count: `6`
- schema_fields: `debt_type, line_count, marker, path`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `6`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `6`
- missing_policy_fields_count: `6`
- missing_label_fields_count: `6`

## `reports/review_queue/human_review_batch_001.json`
- file_type: `json`
- row_count: `50`
- schema_fields: `asks, current_status, item_id, priority_score, source_artifact, source_path_redacted, source_type`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `50`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `50`
- missing_policy_fields_count: `50`
- missing_label_fields_count: `50`

## `reports/review_queue/review_queue_summary.json`
- file_type: `json`
- row_count: `1`
- schema_fields: `exclude_count, limitations, pending_count, queue_size, status`
- date_range: `2026-05-24..2026-05-24`
- accepted_count: `0`
- review_required_count: `1`
- rejected_count: `0`
- training_allowed_count: `0`
- production_only_count: `0`
- retrieval_only_count: `1`
- missing_policy_fields_count: `1`
- missing_label_fields_count: `1`
