# Segmentation Review: Pulgas and Salami Rose Joe Louis - When one door closes, another door closes - 01 Bereft, Send.mp3

- manifest_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/segments/Pulgas_and_Salami_Rose_Joe_Louis_-_When_one_door_closes_another_door_closes_-_01_Bereft_Send/20260522T150054174749_audio_structure_v1/segments_manifest.json`
- run_id: `20260522T150054174749_audio_structure_v1`
- source_name: `Pulgas and Salami Rose Joe Louis - When one door closes, another door closes - 01 Bereft, Send.mp3`
- duration_seconds: `281.849025`
- strategy_requested: `audio_structure`
- strategy_used: `audio_structure_v1`
- fallback_used: `False`
- available_features: `['rms', 'onset_strength', 'chroma_change', 'timbre_change', 'novelty_combined']`
- missing_features: `[]`
- candidate_boundary_count: `43`
- accepted_boundary_count: `3`
- candidate_density: `dense`
- fused_candidate_count: `95`
- returned_candidate_count: `43`
- analysis_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/analysis/Pulgas_and_Salami_Rose_Joe_Louis_-_When_one_door_closes_another_door_closes_-_01_Bereft_Send/20260522T150020358993_modal_librosa_dense/structure_analysis.json`
- segmentation_parameters: `{'boundary_threshold': 0.55, 'min_segment_seconds': 30.0, 'max_segment_seconds': 90.0, 'rms_weight': 0.2, 'onset_weight': 0.3, 'chroma_weight': 0.25, 'timbre_weight': 0.25, 'allow_fixed_candidates': False}`

## Accepted Musical Segments

| index | start | end | duration | confidence | reason | evidence | prev | next | window |
|---|---:|---:|---:|---:|---|---|---|---|---|
| 0 | 0.0 | 78.0 | 78.0 | 0.895 | energy_change | combined_novelty=0.663, chroma_change=0.298, timbre_change=0.522, onset_change=0.436, energy_change=1.000 | None | seg_0001 | win_0000 |
| 1 | 78.0 | 141.0 | 63.0 | 0.925 | harmonic_chroma_change | combined_novelty=0.796, chroma_change=1.000, timbre_change=0.507, onset_change=0.620, energy_change=0.321 | seg_0000 | seg_0002 | win_0001 |
| 2 | 141.0 | 195.25 | 54.25 | 0.837 | combined_audio_novelty | combined_novelty=0.862, chroma_change=0.424, timbre_change=0.484, onset_change=0.721, energy_change=0.670 | seg_0001 | seg_0003 | win_0002 |
| 3 | 195.25 | 281.849025 | 86.599025 | 0.6 | combined_audio_novelty | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0002 | None | win_0003 |

## Candidate Boundaries (Accepted vs Rejected)

| time_seconds | confidence | source_feature | contributing_features | reason | status | evidence |
|---:|---:|---|---|---|---|---|
| 5.000 | 0.561142 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength'] | onset_density_change | rejected_or_unused | combined_novelty=0.439, chroma_change=0.413, timbre_change=0.268, onset_change=0.504, energy_change=0.065 |
| 11.500 | 0.697614 | timbre_change | ['chroma_change', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.479, chroma_change=0.577, timbre_change=0.720, onset_change=0.132, energy_change=0.475 |
| 21.750 | 0.338659 | novelty_combined | ['chroma_change', 'novelty_combined'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.299, chroma_change=0.508, timbre_change=0.201, onset_change=0.101, energy_change=0.035 |
| 26.500 | 0.415016 | chroma_change | ['chroma_change', 'novelty_combined'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.321, chroma_change=0.660, timbre_change=0.099, onset_change=0.073, energy_change=0.110 |
| 31.500 | 0.647182 | chroma_change | ['chroma_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.409, chroma_change=0.776, timbre_change=0.129, onset_change=0.047, energy_change=0.176 |
| 40.250 | 0.704408 | chroma_change | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.620, chroma_change=0.565, timbre_change=0.463, onset_change=0.283, energy_change=0.475 |
| 46.500 | 0.631253 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.509, chroma_change=0.583, timbre_change=0.404, onset_change=0.451, energy_change=0.300 |
| 58.750 | 0.584299 | chroma_change | ['chroma_change', 'onset_strength'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.614, chroma_change=0.507, timbre_change=0.507, onset_change=0.410, energy_change=0.266 |
| 64.500 | 0.578471 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.520, chroma_change=0.604, timbre_change=0.385, onset_change=0.364, energy_change=0.281 |
| 71.500 | 0.554104 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.449, chroma_change=0.491, timbre_change=0.286, onset_change=0.286, energy_change=0.364 |
| 78.000 | 0.984189 | rms | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | accepted | combined_novelty=0.663, chroma_change=0.298, timbre_change=0.522, onset_change=0.436, energy_change=1.000 |
| 82.500 | 1.0 | timbre_change | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.978, chroma_change=0.671, timbre_change=0.887, onset_change=0.450, energy_change=0.982 |
| 87.250 | 0.999358 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.684, chroma_change=0.437, timbre_change=0.730, onset_change=0.475, energy_change=0.985 |
| 92.250 | 0.814943 | timbre_change | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.563, chroma_change=0.510, timbre_change=0.766, onset_change=0.312, energy_change=0.309 |
| 97.750 | 0.41939 | novelty_combined | ['novelty_combined', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.379, chroma_change=0.458, timbre_change=0.406, onset_change=0.275, energy_change=0.016 |
| 104.250 | 0.257679 | chroma_change | ['chroma_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.182, chroma_change=0.298, timbre_change=0.220, onset_change=0.008, energy_change=0.010 |
| 114.250 | 0.765435 | novelty_combined | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.645, chroma_change=0.525, timbre_change=0.703, onset_change=0.492, energy_change=0.426 |
| 118.750 | 0.690092 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.530, chroma_change=0.431, timbre_change=0.515, onset_change=0.382, energy_change=0.439 |
| 128.500 | 0.96365 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.884, chroma_change=0.546, timbre_change=0.822, onset_change=0.832, energy_change=0.297 |
| 135.250 | 0.591963 | onset_strength | ['onset_strength', 'rms'] | onset_density_change | rejected_or_unused | combined_novelty=0.711, chroma_change=0.707, timbre_change=0.425, onset_change=0.466, energy_change=0.336 |
| 141.000 | 1.0 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | harmonic_chroma_change | accepted | combined_novelty=0.796, chroma_change=1.000, timbre_change=0.507, onset_change=0.620, energy_change=0.321 |
| 145.750 | 0.981438 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.932, chroma_change=0.762, timbre_change=0.633, onset_change=0.913, energy_change=0.299 |
| 157.750 | 0.818228 | onset_strength | ['novelty_combined', 'onset_strength'] | onset_density_change | rejected_or_unused | combined_novelty=0.765, chroma_change=0.550, timbre_change=0.435, onset_change=0.786, energy_change=0.287 |
| 163.000 | 0.730985 | novelty_combined | ['novelty_combined', 'onset_strength'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.691, chroma_change=0.362, timbre_change=0.131, onset_change=0.643, energy_change=0.642 |
| 167.500 | 0.531197 | novelty_combined | ['novelty_combined', 'onset_strength'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.491, chroma_change=0.052, timbre_change=0.364, onset_change=0.486, energy_change=0.410 |
| 173.500 | 0.931445 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.836, chroma_change=0.556, timbre_change=0.616, onset_change=0.737, energy_change=0.617 |
| 178.750 | 0.675994 | rms | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.532, chroma_change=0.329, timbre_change=0.402, onset_change=0.353, energy_change=0.634 |
| 183.250 | 0.754919 | onset_strength | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.720, chroma_change=0.605, timbre_change=0.511, onset_change=0.646, energy_change=0.452 |
| 187.750 | 0.986801 | onset_strength | ['chroma_change', 'onset_strength', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.918, chroma_change=0.426, timbre_change=0.469, onset_change=0.901, energy_change=0.633 |
| 195.250 | 0.902324 | novelty_combined | ['novelty_combined', 'rms'] | combined_audio_novelty | accepted | combined_novelty=0.862, chroma_change=0.424, timbre_change=0.484, onset_change=0.721, energy_change=0.670 |
| 206.250 | 0.742158 | chroma_change | ['chroma_change', 'onset_strength', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.717, chroma_change=0.659, timbre_change=0.578, onset_change=0.523, energy_change=0.662 |
| 214.000 | 0.597785 | onset_strength | ['novelty_combined', 'onset_strength', 'rms'] | onset_density_change | rejected_or_unused | combined_novelty=0.548, chroma_change=0.254, timbre_change=0.459, onset_change=0.501, energy_change=0.566 |
| 219.000 | 0.796178 | novelty_combined | ['novelty_combined', 'onset_strength', 'rms'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.716, chroma_change=0.628, timbre_change=0.417, onset_change=0.441, energy_change=0.678 |
| 223.750 | 0.636336 | onset_strength | ['novelty_combined', 'onset_strength'] | onset_density_change | rejected_or_unused | combined_novelty=0.542, chroma_change=0.172, timbre_change=0.444, onset_change=0.626, energy_change=0.195 |
| 231.500 | 0.798798 | rms | ['chroma_change', 'novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.585, chroma_change=0.660, timbre_change=0.228, onset_change=0.198, energy_change=0.791 |
| 236.250 | 0.859716 | rms | ['chroma_change', 'novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.582, chroma_change=0.529, timbre_change=0.068, onset_change=0.101, energy_change=0.886 |
| 241.250 | 0.832332 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.658, chroma_change=0.585, timbre_change=0.219, onset_change=0.510, energy_change=0.923 |
| 245.750 | 0.924851 | rms | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.619, chroma_change=0.543, timbre_change=0.316, onset_change=0.153, energy_change=0.923 |
| 250.500 | 0.895974 | rms | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.715, chroma_change=0.521, timbre_change=0.366, onset_change=0.487, energy_change=0.899 |
| 259.250 | 0.745591 | rms | ['novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.552, chroma_change=0.352, timbre_change=0.254, onset_change=0.168, energy_change=0.833 |
| 264.000 | 0.863457 | rms | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.682, chroma_change=0.494, timbre_change=0.309, onset_change=0.370, energy_change=0.886 |
| 273.250 | 0.843428 | rms | ['chroma_change', 'novelty_combined', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.557, chroma_change=0.495, timbre_change=0.217, onset_change=0.231, energy_change=0.941 |
| 280.000 | 0.966929 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.716, chroma_change=0.521, timbre_change=1.000, onset_change=0.515, energy_change=0.869 |

## Transcription Windows

| index | global_start | global_end | core_start | core_end | context_pre | context_post | source_segment_ids | status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 0.0 | 83.0 | 0.0 | 78.0 | 0.0 | 5.0 | ['seg_0000'] | success |
| 1 | 73.0 | 146.0 | 78.0 | 141.0 | 5.0 | 5.0 | ['seg_0001'] | success |
| 2 | 136.0 | 200.25 | 141.0 | 195.25 | 5.0 | 5.0 | ['seg_0002'] | success |
| 3 | 190.25 | 281.849025 | 195.25 | 281.849025 | 5.0 | 0.0 | ['seg_0003'] | success |

## Boundary Diagnostics

- confidence_range: min=`0.23298`, max=`0.944178`
- confidence_mean: `0.689716`
- rejection_reason_counts: `{'violates_min_segment_seconds': 8, 'unused_candidate': 8, 'too_close_to_previous_boundary': 19, 'below_threshold': 5, 'accepted': 3}`

### Top 10 Rejected Candidates by Confidence

| time_seconds | tuned_confidence | source_feature | contributing_features | rejection_reason | boundary_reason | evidence |
|---:|---:|---|---|---|---|---|
| 82.5 | 0.944178 | timbre_change | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | timbre_change | combined_novelty=0.978, chroma_change=0.671, timbre_change=0.887, onset_change=0.450, energy_change=0.982 |
| 87.25 | 0.925732 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | energy_change | combined_novelty=0.684, chroma_change=0.437, timbre_change=0.730, onset_change=0.475, energy_change=0.985 |
| 145.75 | 0.921611 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | harmonic_chroma_change | combined_novelty=0.932, chroma_change=0.762, timbre_change=0.633, onset_change=0.913, energy_change=0.299 |
| 280.0 | 0.915266 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | violates_min_segment_seconds | timbre_change | combined_novelty=0.716, chroma_change=0.521, timbre_change=1.000, onset_change=0.515, energy_change=0.869 |
| 187.75 | 0.9136 | onset_strength | ['chroma_change', 'onset_strength', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.918, chroma_change=0.426, timbre_change=0.469, onset_change=0.901, energy_change=0.633 |
| 128.5 | 0.901092 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | too_close_to_previous_boundary | timbre_change | combined_novelty=0.884, chroma_change=0.546, timbre_change=0.822, onset_change=0.832, energy_change=0.297 |
| 173.5 | 0.872646 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.836, chroma_change=0.556, timbre_change=0.616, onset_change=0.737, energy_change=0.617 |
| 245.75 | 0.828914 | rms | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | unused_candidate | energy_change | combined_novelty=0.619, chroma_change=0.543, timbre_change=0.316, onset_change=0.153, energy_change=0.923 |
| 250.5 | 0.826291 | rms | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | unused_candidate | energy_change | combined_novelty=0.715, chroma_change=0.521, timbre_change=0.366, onset_change=0.487, energy_change=0.899 |
| 264.0 | 0.788552 | rms | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | violates_min_segment_seconds | energy_change | combined_novelty=0.682, chroma_change=0.494, timbre_change=0.309, onset_change=0.370, energy_change=0.886 |

## Review Questions

- Do these boundaries match musical phrases?
- Are segments too long or too short?
- Should threshold be stricter or looser?
- Should beat/bar snapping be added?
- Should chroma/timbre be weighted more?
