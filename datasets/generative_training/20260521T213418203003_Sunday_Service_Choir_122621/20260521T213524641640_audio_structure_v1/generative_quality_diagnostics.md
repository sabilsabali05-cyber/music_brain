# Generative Quality Diagnostics - 20260521T213524641640_audio_structure_v1

- example_count: `387`

## Split reason breakdown
- train: `{}`
- validation: `{"quality_meets_validation_threshold": 53}`
- review: `{"duration_out_of_range": 18, "phrase_boundary_weak": 67, "quality_below_threshold": 332, "route_state_unsuitable": 91, "task_policy_failed": 108, "weak_or_missing_task_evidence": 16}`
- exclude: `{"phrase_boundary_weak": 2, "quality_below_threshold": 2, "route_state_unsuitable": 2, "task_policy_failed": 2}`

## Quality component averages
- transcription_reliability: `0.897933`
- route_suitability: `0.67509`
- phrase_boundary_quality: `0.821705`
- target_density: `0.760853`
- musical_completeness: `1.0`
- repetition_or_motif_strength: `0.523948`
- witness_agreement_score: `0.42`
- ambiguity_penalty: `0.24`
- review_penalty: `0.0`
- final_score: `0.509901`

## Missing task diagnostics
- harmony_continuation: `{"harmonic_or_polyphonic_regions_available": 119, "regions_with_pitch_harmony_refs": 119, "regions_with_target_midi_events": 119, "why_no_examples_were_created": []}`
- motif_transformation: `{"motif_candidates_available": 1764, "repeated_motif_groups": 272, "passing_duration_note_constraints": 272, "why_no_examples_were_created": []}`

## Top salvage candidates
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:372.5-438.5:438.5-498.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:438.5-498.5:498.5-558.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:498.5-558.5:558.5-644.0", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:558.5-644.0:644.0-683.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:644.0-683.5:683.5-773.25", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:683.5-773.25:773.25-853.0", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:773.25-853.0:853.0-913.0", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:853.0-913.0:913.0-964.0", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:964.0-1024.0:1024.0-1092.75", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1024.0-1092.75:1092.75-1162.0", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1092.75-1162.0:1162.0-1222.0", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1222.0-1280.75:1280.75-1340.75", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1340.75-1400.75:1400.75-1460.75", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1400.75-1460.75:1460.75-1520.75", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1460.75-1520.75:1520.75-1580.75", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1580.75-1640.75:1640.75-1700.75", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1640.75-1700.75:1700.75-1761.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1700.75-1761.5:1761.5-1821.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1761.5-1821.5:1821.5-1881.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1821.5-1881.5:1881.5-1941.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1881.5-1941.5:1941.5-2001.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:1941.5-2001.5:2001.5-2061.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:2001.5-2061.5:2061.5-2121.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:2061.5-2121.5:2121.5-2181.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
- {"example_id": "20260521T213418203003_Sunday_Service_Choir_122621:20260521T213524641640_audio_structure_v1:groove_continuation:2121.5-2181.5:2181.5-2241.5", "task_type": "groove_continuation", "final_score": 0.5998, "current_split": "review", "blockers": ["quality_below_threshold"]}
