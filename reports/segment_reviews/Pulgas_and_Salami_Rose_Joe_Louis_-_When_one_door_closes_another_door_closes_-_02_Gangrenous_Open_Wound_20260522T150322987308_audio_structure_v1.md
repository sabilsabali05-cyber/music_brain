# Segmentation Review: Pulgas and Salami Rose Joe Louis - When one door closes, another door closes - 02 Gangrenous Open Wound.mp3

- manifest_path: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Pulgas_and_Salami_Rose_Joe_Louis_-_When_one_door_closes_another_door_closes_-_02_Gangrenous_Open_Wound/20260522T150322987308_audio_structure_v1/segments_manifest.json`
- run_id: `20260522T150322987308_audio_structure_v1`
- source_name: `Pulgas and Salami Rose Joe Louis - When one door closes, another door closes - 02 Gangrenous Open Wound.mp3`
- duration_seconds: `189.340658`
- strategy_requested: `audio_structure`
- strategy_used: `audio_structure_v1`
- fallback_used: `False`
- available_features: `['rms', 'onset_strength', 'chroma_change', 'timbre_change', 'novelty_combined']`
- missing_features: `[]`
- candidate_boundary_count: `31`
- accepted_boundary_count: `2`
- candidate_density: `dense`
- fused_candidate_count: `62`
- returned_candidate_count: `31`
- analysis_path: `C:/Users/izzyo/ai-composer/music_brain/samples/analysis/Pulgas_and_Salami_Rose_Joe_Louis_-_When_one_door_closes_another_door_closes_-_02_Gangrenous_Open_Wound/20260522T150239155925_modal_librosa_dense/structure_analysis.json`
- segmentation_parameters: `{'boundary_threshold': 0.55, 'min_segment_seconds': 30.0, 'max_segment_seconds': 90.0, 'rms_weight': 0.2, 'onset_weight': 0.3, 'chroma_weight': 0.25, 'timbre_weight': 0.25, 'allow_fixed_candidates': False}`

## Accepted Musical Segments

| index | start | end | duration | confidence | reason | evidence | prev | next | window |
|---|---:|---:|---:|---:|---|---|---|---|---|
| 0 | 0.0 | 54.25 | 54.25 | 0.794 | energy_change | combined_novelty=0.912, chroma_change=0.638, timbre_change=0.480, onset_change=0.681, energy_change=0.790 | None | seg_0001 | win_0000 |
| 1 | 54.25 | 119.25 | 65.0 | 0.785 | energy_change | combined_novelty=0.634, chroma_change=0.569, timbre_change=0.443, onset_change=0.311, energy_change=0.732 | seg_0000 | seg_0002 | win_0001 |
| 2 | 119.25 | 189.340658 | 70.090658 | 0.6 | combined_audio_novelty | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0001 | None | win_0002 |

## Candidate Boundaries (Accepted vs Rejected)

| time_seconds | confidence | source_feature | contributing_features | reason | status | evidence |
|---:|---:|---|---|---|---|---|
| 1.500 | 0.776607 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.703, chroma_change=0.517, timbre_change=0.675, onset_change=0.466, energy_change=0.714 |
| 6.000 | 0.731207 | novelty_combined | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.611, chroma_change=0.399, timbre_change=0.314, onset_change=0.453, energy_change=0.688 |
| 12.750 | 0.663385 | rms | ['onset_strength', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.484, chroma_change=0.411, timbre_change=0.322, onset_change=0.335, energy_change=0.699 |
| 17.500 | 0.869701 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.601, chroma_change=0.720, timbre_change=0.418, onset_change=0.441, energy_change=0.792 |
| 24.250 | 0.767557 | novelty_combined | ['chroma_change', 'novelty_combined', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.688, chroma_change=0.513, timbre_change=0.356, onset_change=0.250, energy_change=0.968 |
| 29.250 | 0.642365 | chroma_change | ['chroma_change', 'novelty_combined', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.517, chroma_change=0.654, timbre_change=0.510, onset_change=0.481, energy_change=0.161 |
| 35.250 | 0.812004 | rms | ['onset_strength', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.724, chroma_change=0.507, timbre_change=0.423, onset_change=0.438, energy_change=0.911 |
| 40.750 | 0.785369 | rms | ['rms'] | energy_change | rejected_or_unused | combined_novelty=0.527, chroma_change=0.473, timbre_change=0.127, onset_change=0.076, energy_change=0.924 |
| 47.750 | 0.773969 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.694, chroma_change=0.900, timbre_change=0.343, onset_change=0.468, energy_change=0.767 |
| 54.250 | 0.832537 | rms | ['rms'] | energy_change | accepted | combined_novelty=0.912, chroma_change=0.638, timbre_change=0.480, onset_change=0.681, energy_change=0.790 |
| 63.250 | 0.731295 | rms | ['rms'] | energy_change | rejected_or_unused | combined_novelty=0.540, chroma_change=0.320, timbre_change=0.401, onset_change=0.125, energy_change=0.834 |
| 70.000 | 0.692703 | rms | ['chroma_change', 'novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.532, chroma_change=0.409, timbre_change=0.408, onset_change=0.152, energy_change=0.722 |
| 74.750 | 0.760133 | rms | ['chroma_change', 'novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.451, chroma_change=0.350, timbre_change=0.171, onset_change=0.103, energy_change=0.803 |
| 80.250 | 0.857535 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.853, chroma_change=0.844, timbre_change=0.550, onset_change=0.424, energy_change=0.854 |
| 84.750 | 0.9003 | rms | ['chroma_change', 'novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.524, chroma_change=0.638, timbre_change=0.153, onset_change=0.087, energy_change=1.000 |
| 93.750 | 0.667389 | rms | ['rms'] | energy_change | rejected_or_unused | combined_novelty=0.433, chroma_change=0.216, timbre_change=0.282, onset_change=0.084, energy_change=0.793 |
| 98.500 | 0.853129 | rms | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.615, chroma_change=0.497, timbre_change=0.327, onset_change=0.231, energy_change=0.996 |
| 109.750 | 0.707224 | rms | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.529, chroma_change=0.519, timbre_change=0.310, onset_change=0.173, energy_change=0.619 |
| 114.250 | 0.651763 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.440, chroma_change=0.398, timbre_change=0.569, onset_change=0.375, energy_change=0.334 |
| 119.250 | 0.857802 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | accepted | combined_novelty=0.634, chroma_change=0.569, timbre_change=0.443, onset_change=0.311, energy_change=0.732 |
| 124.250 | 0.799913 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.652, chroma_change=0.612, timbre_change=0.355, onset_change=0.372, energy_change=0.908 |
| 128.750 | 0.9544 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.776, chroma_change=0.728, timbre_change=0.612, onset_change=0.432, energy_change=0.841 |
| 133.500 | 0.889427 | rms | ['chroma_change', 'novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.560, chroma_change=0.664, timbre_change=0.282, onset_change=0.117, energy_change=0.944 |
| 138.000 | 0.629865 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.588, chroma_change=0.452, timbre_change=0.606, onset_change=0.291, energy_change=0.530 |
| 143.250 | 0.735431 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.597, chroma_change=0.661, timbre_change=0.416, onset_change=0.564, energy_change=0.370 |
| 148.250 | 0.790314 | rms | ['chroma_change', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.646, chroma_change=0.508, timbre_change=0.446, onset_change=0.410, energy_change=0.894 |
| 159.250 | 0.928311 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.637, chroma_change=0.791, timbre_change=0.395, onset_change=0.322, energy_change=0.960 |
| 168.000 | 0.917716 | rms | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.599, chroma_change=0.549, timbre_change=0.448, onset_change=0.092, energy_change=0.913 |
| 173.250 | 0.480565 | chroma_change | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.348, chroma_change=0.459, timbre_change=0.306, onset_change=0.201, energy_change=0.344 |
| 181.750 | 0.638386 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.446, chroma_change=0.546, timbre_change=0.426, onset_change=0.351, energy_change=0.366 |
| 188.250 | 0.419306 | timbre_change | ['chroma_change', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.166, chroma_change=0.424, timbre_change=0.496, onset_change=0.007, energy_change=0.138 |

## Transcription Windows

| index | global_start | global_end | core_start | core_end | context_pre | context_post | source_segment_ids | status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 0.0 | 59.25 | 0.0 | 54.25 | 0.0 | 5.0 | ['seg_0000'] | success |
| 1 | 49.25 | 124.25 | 54.25 | 119.25 | 5.0 | 5.0 | ['seg_0001'] | success |
| 2 | 114.25 | 189.340658 | 119.25 | 189.340658 | 5.0 | 0.0 | ['seg_0002'] | success |

## Boundary Diagnostics

- confidence_range: min=`0.387373`, max=`0.890074`
- confidence_mean: `0.700904`
- rejection_reason_counts: `{'violates_min_segment_seconds': 10, 'too_close_to_previous_boundary': 17, 'accepted': 2, 'unused_candidate': 2}`

### Top 10 Rejected Candidates by Confidence

| time_seconds | tuned_confidence | source_feature | contributing_features | rejection_reason | boundary_reason | evidence |
|---:|---:|---|---|---|---|---|
| 128.75 | 0.890074 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | energy_change | combined_novelty=0.776, chroma_change=0.728, timbre_change=0.612, onset_change=0.432, energy_change=0.841 |
| 159.25 | 0.85973 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | unused_candidate | energy_change | combined_novelty=0.637, chroma_change=0.791, timbre_change=0.395, onset_change=0.322, energy_change=0.960 |
| 168.0 | 0.826047 | rms | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | violates_min_segment_seconds | energy_change | combined_novelty=0.599, chroma_change=0.549, timbre_change=0.448, onset_change=0.092, energy_change=0.913 |
| 80.25 | 0.815371 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | energy_change | combined_novelty=0.853, chroma_change=0.844, timbre_change=0.550, onset_change=0.424, energy_change=0.854 |
| 17.5 | 0.810782 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | violates_min_segment_seconds | energy_change | combined_novelty=0.601, chroma_change=0.720, timbre_change=0.418, onset_change=0.441, energy_change=0.792 |
| 84.75 | 0.805034 | rms | ['chroma_change', 'novelty_combined', 'rms'] | unused_candidate | energy_change | combined_novelty=0.524, chroma_change=0.638, timbre_change=0.153, onset_change=0.087, energy_change=1.000 |
| 133.5 | 0.80362 | rms | ['chroma_change', 'novelty_combined', 'rms'] | too_close_to_previous_boundary | energy_change | combined_novelty=0.560, chroma_change=0.664, timbre_change=0.282, onset_change=0.117, energy_change=0.944 |
| 98.5 | 0.777358 | rms | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | too_close_to_previous_boundary | energy_change | combined_novelty=0.615, chroma_change=0.497, timbre_change=0.327, onset_change=0.231, energy_change=0.996 |
| 35.25 | 0.758825 | rms | ['onset_strength', 'rms'] | too_close_to_previous_boundary | energy_change | combined_novelty=0.724, chroma_change=0.507, timbre_change=0.423, onset_change=0.438, energy_change=0.911 |
| 124.25 | 0.746903 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | energy_change | combined_novelty=0.652, chroma_change=0.612, timbre_change=0.355, onset_change=0.372, energy_change=0.908 |

## Review Questions

- Do these boundaries match musical phrases?
- Are segments too long or too short?
- Should threshold be stricter or looser?
- Should beat/bar snapping be added?
- Should chroma/timbre be weighted more?
