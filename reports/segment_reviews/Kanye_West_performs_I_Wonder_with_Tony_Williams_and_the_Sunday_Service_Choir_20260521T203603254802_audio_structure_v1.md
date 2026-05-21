# Segmentation Review: Kanye West performs I Wonder with Tony Williams and the Sunday Service Choir.mp3

- manifest_path: `C:/Users/izzyo/ai-composer/music_brain/samples/segments/Kanye_West_performs_I_Wonder_with_Tony_Williams_and_the_Sunday_Service_Choir/20260521T203603254802_audio_structure_v1/segments_manifest.json`
- run_id: `20260521T203603254802_audio_structure_v1`
- source_name: `Kanye West performs I Wonder with Tony Williams and the Sunday Service Choir.mp3`
- duration_seconds: `209.86195`
- strategy_requested: `audio_structure`
- strategy_used: `audio_structure_v1`
- fallback_used: `False`
- available_features: `['rms', 'onset_strength', 'chroma_change', 'timbre_change', 'novelty_combined']`
- missing_features: `[]`
- candidate_boundary_count: `34`
- accepted_boundary_count: `2`
- candidate_density: `dense`
- fused_candidate_count: `69`
- returned_candidate_count: `34`
- analysis_path: `C:/Users/izzyo/ai-composer/music_brain/samples/analysis/Kanye_West_performs_I_Wonder_with_Tony_Williams_and_the_Sunday_Service_Choir/20260521T203531046417_modal_librosa_dense/structure_analysis.json`
- segmentation_parameters: `{'boundary_threshold': 0.55, 'min_segment_seconds': 30.0, 'max_segment_seconds': 90.0, 'rms_weight': 0.2, 'onset_weight': 0.3, 'chroma_weight': 0.25, 'timbre_weight': 0.25, 'allow_fixed_candidates': False}`

## Accepted Musical Segments

| index | start | end | duration | confidence | reason | evidence | prev | next | window |
|---|---:|---:|---:|---:|---|---|---|---|---|
| 0 | 0.0 | 56.25 | 56.25 | 0.71 | energy_change | combined_novelty=0.661, chroma_change=0.676, timbre_change=0.540, onset_change=0.342, energy_change=0.610 | None | seg_0001 | win_0000 |
| 1 | 56.25 | 122.5 | 66.25 | 0.606 | harmonic_chroma_change | combined_novelty=0.508, chroma_change=0.697, timbre_change=0.313, onset_change=0.227, energy_change=0.571 | seg_0000 | seg_0002 | win_0001 |
| 2 | 122.5 | 209.86195 | 87.36195 | 0.6 | combined_audio_novelty | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0001 | None | win_0002 |

## Candidate Boundaries (Accepted vs Rejected)

| time_seconds | confidence | source_feature | contributing_features | reason | status | evidence |
|---:|---:|---|---|---|---|---|
| 0.250 | 0.949857 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.631, chroma_change=0.380, timbre_change=0.664, onset_change=0.875, energy_change=0.430 |
| 5.000 | 1.0 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.764, chroma_change=0.401, timbre_change=1.000, onset_change=0.395, energy_change=0.688 |
| 10.750 | 0.673574 | rms | ['chroma_change', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.692, chroma_change=0.489, timbre_change=0.778, onset_change=0.327, energy_change=0.602 |
| 16.250 | 0.677194 | rms | ['chroma_change', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.451, chroma_change=0.526, timbre_change=0.313, onset_change=0.213, energy_change=0.749 |
| 22.250 | 0.611969 | novelty_combined | ['novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.532, chroma_change=0.096, timbre_change=0.647, onset_change=0.390, energy_change=0.570 |
| 28.000 | 0.763312 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.714, chroma_change=0.446, timbre_change=0.858, onset_change=0.544, energy_change=0.595 |
| 36.500 | 0.785222 | novelty_combined | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.665, chroma_change=0.527, timbre_change=0.948, onset_change=0.368, energy_change=0.591 |
| 45.000 | 0.816961 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.797, chroma_change=0.638, timbre_change=0.507, onset_change=0.581, energy_change=0.665 |
| 51.500 | 0.679666 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.466, chroma_change=0.548, timbre_change=0.518, onset_change=0.312, energy_change=0.611 |
| 56.250 | 0.754837 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | accepted | combined_novelty=0.661, chroma_change=0.676, timbre_change=0.540, onset_change=0.342, energy_change=0.610 |
| 63.750 | 0.631841 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.552, chroma_change=0.650, timbre_change=0.247, onset_change=0.439, energy_change=0.654 |
| 70.000 | 0.435553 | rms | ['rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.458, chroma_change=0.453, timbre_change=0.387, onset_change=0.339, energy_change=0.425 |
| 77.000 | 0.684614 | chroma_change | ['chroma_change', 'novelty_combined'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.592, chroma_change=0.673, timbre_change=0.448, onset_change=0.250, energy_change=0.490 |
| 81.750 | 0.823844 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.607, chroma_change=0.748, timbre_change=0.640, onset_change=0.591, energy_change=0.469 |
| 86.500 | 0.71782 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.558, chroma_change=0.552, timbre_change=0.499, onset_change=0.372, energy_change=0.508 |
| 92.500 | 0.585904 | rms | ['rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.497, chroma_change=0.420, timbre_change=0.463, onset_change=0.222, energy_change=0.572 |
| 97.750 | 0.768145 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.646, chroma_change=0.610, timbre_change=0.588, onset_change=0.558, energy_change=0.528 |
| 106.250 | 0.698 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.495, chroma_change=0.647, timbre_change=0.418, onset_change=0.285, energy_change=0.608 |
| 111.000 | 0.477888 | timbre_change | ['rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.526, chroma_change=0.759, timbre_change=0.391, onset_change=0.222, energy_change=0.443 |
| 116.750 | 0.559401 | rms | ['rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.536, chroma_change=0.491, timbre_change=0.520, onset_change=0.489, energy_change=0.510 |
| 122.500 | 0.648386 | chroma_change | ['chroma_change', 'novelty_combined'] | harmonic_chroma_change | accepted | combined_novelty=0.508, chroma_change=0.697, timbre_change=0.313, onset_change=0.227, energy_change=0.571 |
| 129.250 | 0.34336 | timbre_change | ['timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.322, chroma_change=0.141, timbre_change=0.355, onset_change=0.222, energy_change=0.363 |
| 135.250 | 0.611857 | rms | ['rms'] | energy_change | rejected_or_unused | combined_novelty=0.423, chroma_change=0.139, timbre_change=0.448, onset_change=0.109, energy_change=0.714 |
| 140.250 | 0.7221 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | energy_change | rejected_or_unused | combined_novelty=0.572, chroma_change=0.586, timbre_change=0.243, onset_change=0.472, energy_change=0.739 |
| 145.750 | 0.755162 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.608, chroma_change=0.735, timbre_change=0.434, onset_change=0.555, energy_change=0.686 |
| 153.000 | 0.611935 | onset_strength | ['onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.535, chroma_change=0.770, timbre_change=0.496, onset_change=0.530, energy_change=0.484 |
| 159.750 | 1.0 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.710, chroma_change=1.000, timbre_change=0.422, onset_change=0.291, energy_change=0.628 |
| 164.500 | 0.741175 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.560, chroma_change=0.690, timbre_change=0.489, onset_change=0.386, energy_change=0.575 |
| 177.750 | 0.878483 | chroma_change | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.610, chroma_change=0.838, timbre_change=0.466, onset_change=0.366, energy_change=0.795 |
| 183.250 | 0.738543 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.556, chroma_change=0.855, timbre_change=0.282, onset_change=0.368, energy_change=0.591 |
| 195.000 | 0.835712 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.652, chroma_change=0.533, timbre_change=0.595, onset_change=0.354, energy_change=0.774 |
| 199.750 | 0.799318 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.548, chroma_change=0.775, timbre_change=0.638, onset_change=0.413, energy_change=0.576 |
| 204.500 | 0.77198 | rms | ['chroma_change', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.483, chroma_change=0.398, timbre_change=0.484, onset_change=0.190, energy_change=0.878 |
| 209.500 | 0.973319 | rms | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.605, chroma_change=0.627, timbre_change=0.375, onset_change=0.337, energy_change=1.000 |

## Transcription Windows

| index | global_start | global_end | core_start | core_end | context_pre | context_post | source_segment_ids | status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 0.0 | 61.25 | 0.0 | 56.25 | 0.0 | 5.0 | ['seg_0000'] | success |
| 1 | 51.25 | 127.5 | 56.25 | 122.5 | 5.0 | 5.0 | ['seg_0001'] | success |
| 2 | 117.5 | 209.86195 | 122.5 | 209.86195 | 5.0 | 0.0 | ['seg_0002'] | success |

## Boundary Diagnostics

- confidence_range: min=`0.327308`, max=`0.921232`
- confidence_mean: `0.678574`
- rejection_reason_counts: `{'violates_min_segment_seconds': 11, 'too_close_to_previous_boundary': 11, 'accepted': 2, 'below_threshold': 5, 'unused_candidate': 5}`

### Top 10 Rejected Candidates by Confidence

| time_seconds | tuned_confidence | source_feature | contributing_features | rejection_reason | boundary_reason | evidence |
|---:|---:|---|---|---|---|---|
| 5.0 | 0.921232 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | violates_min_segment_seconds | timbre_change | combined_novelty=0.764, chroma_change=0.401, timbre_change=1.000, onset_change=0.395, energy_change=0.688 |
| 159.75 | 0.913647 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | unused_candidate | harmonic_chroma_change | combined_novelty=0.710, chroma_change=1.000, timbre_change=0.422, onset_change=0.291, energy_change=0.628 |
| 209.5 | 0.889012 | rms | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | violates_min_segment_seconds | energy_change | combined_novelty=0.605, chroma_change=0.627, timbre_change=0.375, onset_change=0.337, energy_change=1.000 |
| 0.25 | 0.881797 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | violates_min_segment_seconds | onset_density_change | combined_novelty=0.631, chroma_change=0.380, timbre_change=0.664, onset_change=0.875, energy_change=0.430 |
| 177.75 | 0.821759 | chroma_change | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | unused_candidate | harmonic_chroma_change | combined_novelty=0.610, chroma_change=0.838, timbre_change=0.466, onset_change=0.366, energy_change=0.795 |
| 81.75 | 0.782694 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | harmonic_chroma_change | combined_novelty=0.607, chroma_change=0.748, timbre_change=0.640, onset_change=0.591, energy_change=0.469 |
| 195.0 | 0.777127 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | violates_min_segment_seconds | energy_change | combined_novelty=0.652, chroma_change=0.533, timbre_change=0.595, onset_change=0.354, energy_change=0.774 |
| 45.0 | 0.772312 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.797, chroma_change=0.638, timbre_change=0.507, onset_change=0.581, energy_change=0.665 |
| 199.75 | 0.758 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | violates_min_segment_seconds | harmonic_chroma_change | combined_novelty=0.548, chroma_change=0.775, timbre_change=0.638, onset_change=0.413, energy_change=0.576 |
| 36.5 | 0.747599 | novelty_combined | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | too_close_to_previous_boundary | combined_audio_novelty | combined_novelty=0.665, chroma_change=0.527, timbre_change=0.948, onset_change=0.368, energy_change=0.591 |

## Review Questions

- Do these boundaries match musical phrases?
- Are segments too long or too short?
- Should threshold be stricter or looser?
- Should beat/bar snapping be added?
- Should chroma/timbre be weighted more?
