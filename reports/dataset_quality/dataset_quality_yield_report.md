# Dataset Quality and Yield Report

- total performances scanned: `4`
- corpus ready for mass ingestion: `False`
- minimum blockers before mass input: `["needs_manual_review", "needs_meter_calibration", "needs_pitch_harmony_calibration", "needs_external_witness"]`
- best next analyzer to package: `musicnn`
- expected data yield per hour: `1934.3849`
- expected accepted observations per hour: `123.856`
- expected review burden per hour: `1810.5288`

## Dataset risk flag counts
- external_witness_disagreement: `1`
- high_review_required_percentage: `4`
- low_beat_confidence: `1`
- missing_external_meter_witness: `4`
- missing_microtonal_evidence: `4`

## 20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir / 20260521T204750163461_audio_structure_v1
- records_per_minute: `32.179034`
- accepted_observations_per_minute: `2.155915`
- review_required_percentage: `93.3002`
- risk_flags: `["high_review_required_percentage", "low_beat_confidence", "missing_external_meter_witness", "missing_microtonal_evidence"]`
- recommendations: `{"ready_for_training_observation_only": false, "needs_review": true, "needs_external_witness": false, "needs_routing_calibration": false, "needs_meter_calibration": true, "needs_pitch_harmony_calibration": false, "needs_manual_review": true, "good_candidate_for_mass_ingestion_template": false}`
- witness_coverage: `{"yourmt3_pretty_midi_present": true, "librosa_internal_features_present": true, "essentia": {"present": true, "status": "success"}, "music21": {"present": true, "status": "success"}, "musicnn": {"present": false, "status": "unavailable"}, "beatnet_madmom": {"present": false, "status": "unavailable"}, "omnizart": {"present": false, "status": "unavailable"}, "consensus_status": "supportive", "unresolved_conflicts": ["missing_external_meter_hypotheses"], "low_confidence_warnings": ["semantic_tag_mismatch"]}`
- layer_completeness: `{"source_manifest_present": true, "segments_present": true, "merged_midi_present": true, "rhythm_features_present": true, "harmony_features_present": true, "routing_present": true, "meter_time_present": true, "pitch_harmony_present": true, "trust_reports_present": true, "training_export_present": true, "external_witnesses_present": true, "model_consensus_present": true, "audit_report_present": true}`

## 20260521T213418203003_Sunday_Service_Choir_122621 / 20260521T213524641640_audio_structure_v1
- records_per_minute: `31.995505`
- accepted_observations_per_minute: `1.967011`
- review_required_percentage: `93.8522`
- risk_flags: `["external_witness_disagreement", "high_review_required_percentage", "missing_external_meter_witness", "missing_microtonal_evidence"]`
- recommendations: `{"ready_for_training_observation_only": false, "needs_review": true, "needs_external_witness": false, "needs_routing_calibration": false, "needs_meter_calibration": false, "needs_pitch_harmony_calibration": true, "needs_manual_review": true, "good_candidate_for_mass_ingestion_template": false}`
- witness_coverage: `{"yourmt3_pretty_midi_present": true, "librosa_internal_features_present": true, "essentia": {"present": true, "status": "success"}, "music21": {"present": true, "status": "success"}, "musicnn": {"present": false, "status": "missing"}, "beatnet_madmom": {"present": false, "status": "missing"}, "omnizart": {"present": false, "status": "missing"}, "consensus_status": "conflicted", "unresolved_conflicts": ["missing_external_meter_hypotheses", "tonal_center_conflict"], "low_confidence_warnings": ["semantic_tag_mismatch", "tonal_conflict"]}`
- layer_completeness: `{"source_manifest_present": true, "segments_present": true, "merged_midi_present": true, "rhythm_features_present": true, "harmony_features_present": true, "routing_present": true, "meter_time_present": true, "pitch_harmony_present": true, "trust_reports_present": true, "training_export_present": true, "external_witnesses_present": true, "model_consensus_present": true, "audit_report_present": true}`

## 20260522T150019594510_Pulgas_and_Salami_Rose_Joe_Louis_-_When_one_door_closes_another_door_closes_-_01_Bereft_Send / 20260522T150054174749_audio_structure_v1
- records_per_minute: `32.144869`
- accepted_observations_per_minute: `1.915919`
- review_required_percentage: `94.0397`
- risk_flags: `["high_review_required_percentage", "missing_external_meter_witness", "missing_microtonal_evidence"]`
- recommendations: `{"ready_for_training_observation_only": false, "needs_review": true, "needs_external_witness": true, "needs_routing_calibration": false, "needs_meter_calibration": true, "needs_pitch_harmony_calibration": true, "needs_manual_review": true, "good_candidate_for_mass_ingestion_template": false}`
- witness_coverage: `{"yourmt3_pretty_midi_present": true, "librosa_internal_features_present": true, "essentia": {"present": false, "status": "missing"}, "music21": {"present": false, "status": "missing"}, "musicnn": {"present": false, "status": "missing"}, "beatnet_madmom": {"present": false, "status": "missing"}, "omnizart": {"present": false, "status": "missing"}, "consensus_status": "missing", "unresolved_conflicts": [], "low_confidence_warnings": []}`
- layer_completeness: `{"source_manifest_present": true, "segments_present": true, "merged_midi_present": true, "rhythm_features_present": true, "harmony_features_present": true, "routing_present": false, "meter_time_present": false, "pitch_harmony_present": false, "trust_reports_present": true, "training_export_present": true, "external_witnesses_present": false, "model_consensus_present": false, "audit_report_present": true}`

## 20260522T150238990635_Pulgas_and_Salami_Rose_Joe_Louis_-_When_one_door_closes_another_door_closes_-_02_Gangrenous_Open_Wound / 20260522T150322987308_audio_structure_v1
- records_per_minute: `32.639582`
- accepted_observations_per_minute: `2.218224`
- review_required_percentage: `93.2039`
- risk_flags: `["high_review_required_percentage", "missing_external_meter_witness", "missing_microtonal_evidence"]`
- recommendations: `{"ready_for_training_observation_only": false, "needs_review": true, "needs_external_witness": true, "needs_routing_calibration": false, "needs_meter_calibration": true, "needs_pitch_harmony_calibration": true, "needs_manual_review": true, "good_candidate_for_mass_ingestion_template": false}`
- witness_coverage: `{"yourmt3_pretty_midi_present": true, "librosa_internal_features_present": true, "essentia": {"present": false, "status": "missing"}, "music21": {"present": false, "status": "missing"}, "musicnn": {"present": false, "status": "missing"}, "beatnet_madmom": {"present": false, "status": "missing"}, "omnizart": {"present": false, "status": "missing"}, "consensus_status": "missing", "unresolved_conflicts": [], "low_confidence_warnings": []}`
- layer_completeness: `{"source_manifest_present": true, "segments_present": true, "merged_midi_present": true, "rhythm_features_present": true, "harmony_features_present": true, "routing_present": false, "meter_time_present": false, "pitch_harmony_present": false, "trust_reports_present": true, "training_export_present": true, "external_witnesses_present": false, "model_consensus_present": false, "audit_report_present": true}`
