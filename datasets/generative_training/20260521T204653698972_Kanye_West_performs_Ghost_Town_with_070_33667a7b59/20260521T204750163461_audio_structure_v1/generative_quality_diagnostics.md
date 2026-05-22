# Generative Quality Diagnostics - 20260521T204750163461_audio_structure_v1

- example_count: `88`

## Split reason breakdown
- train: `{"quality_meets_train_threshold": 31}`
- validation: `{"duration_out_of_range": 7, "phrase_boundary_weak": 10, "quality_meets_validation_threshold": 42, "task_policy_failed": 7, "weak_or_missing_task_evidence": 3}`
- review: `{"duration_out_of_range": 1, "phrase_boundary_weak": 2, "quality_below_threshold": 15, "route_state_unsuitable": 13, "task_policy_failed": 14}`
- exclude: `{}`

## Quality component averages
- transcription_reliability: `0.885795`
- route_suitability: `0.774659`
- phrase_boundary_quality: `0.863636`
- target_density: `0.751136`
- musical_completeness: `1.0`
- repetition_or_motif_strength: `0.527838`
- witness_agreement_score: `0.84`
- ambiguity_penalty: `0.16`
- review_penalty: `0.0`
- final_score: `0.66295`

## Missing task diagnostics
- harmony_continuation: `{"harmonic_or_polyphonic_regions_available": 41, "regions_with_pitch_harmony_refs": 41, "regions_with_target_midi_events": 41, "why_no_examples_were_created": []}`
- motif_transformation: `{"motif_candidates_available": 1047, "repeated_motif_groups": 93, "passing_duration_note_constraints": 93, "why_no_examples_were_created": []}`

## Top salvage candidates
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:buildup_to_release:472.25-592.5:592.5-656.5", "task_type": "buildup_to_release", "final_score": 0.6456, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:infill_missing_region:44.75-244.0:116.25-186.75", "task_type": "infill_missing_region", "final_score": 0.5874, "current_split": "review", "blockers": ["duration_out_of_range", "phrase_boundary_weak", "quality_below_threshold", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:infill_missing_region:288.0-472.25:325.0-383.5", "task_type": "infill_missing_region", "final_score": 0.5874, "current_split": "review", "blockers": ["phrase_boundary_weak", "quality_below_threshold"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:0.0-44.75:44.75-116.25", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:44.75-116.25:116.25-186.75", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:116.25-186.75:186.75-244.0", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:186.75-244.0:244.0-288.0", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:244.0-288.0:288.0-325.0", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:288.0-325.0:325.0-383.5", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:325.0-383.5:383.5-472.25", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:383.5-472.25:472.25-531.0", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:472.25-531.0:531.0-592.5", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:592.5-656.5:656.5-712.75", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:phrase_continuation:656.5-712.75:712.75-751.421", "task_type": "phrase_continuation", "final_score": 0.5396, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
- {"example_id": "20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir:20260521T204750163461_audio_structure_v1:section_transition:32.75-44.75:44.75-56.75", "task_type": "section_transition", "final_score": 0.5156, "current_split": "review", "blockers": ["quality_below_threshold", "route_state_unsuitable", "task_policy_failed"]}
