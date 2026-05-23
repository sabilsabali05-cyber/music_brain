# Segmentation Review: Kanye West performs Ghost Town with 070 Shake and the Sunday Service Choir.mp3

- manifest_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/segments/Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204750163461_audio_structure_v1/segments_manifest.json`
- run_id: `20260521T204750163461_audio_structure_v1`
- source_name: `Kanye West performs Ghost Town with 070 Shake and the Sunday Service Choir.mp3`
- duration_seconds: `751.420952`
- strategy_requested: `audio_structure`
- strategy_used: `audio_structure_v1`
- fallback_used: `False`
- available_features: `['rms', 'onset_strength', 'chroma_change', 'timbre_change', 'novelty_combined']`
- missing_features: `[]`
- candidate_boundary_count: `43`
- accepted_boundary_count: `12`
- candidate_density: `dense`
- fused_candidate_count: `269`
- returned_candidate_count: `43`
- analysis_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/analysis/Kanye_West_performs_Ghost_Town_with_070_Shake_and_the_Sunday_Service_Choir/20260521T204701196539_modal_librosa_dense/structure_analysis.json`
- segmentation_parameters: `{'boundary_threshold': 0.55, 'min_segment_seconds': 30.0, 'max_segment_seconds': 90.0, 'rms_weight': 0.2, 'onset_weight': 0.3, 'chroma_weight': 0.25, 'timbre_weight': 0.25, 'allow_fixed_candidates': False}`

## Accepted Musical Segments

| index | start | end | duration | confidence | reason | evidence | prev | next | window |
|---|---:|---:|---:|---:|---|---|---|---|---|
| 0 | 0.0 | 44.75 | 44.75 | 0.759 | energy_change | combined_novelty=0.722, chroma_change=0.531, timbre_change=0.477, onset_change=0.557, energy_change=0.616 | None | seg_0001 | win_0000 |
| 1 | 44.75 | 116.25 | 71.5 | 0.631 | energy_change | combined_novelty=0.492, chroma_change=0.452, timbre_change=0.284, onset_change=0.301, energy_change=0.629 | seg_0000 | seg_0002 | win_0001 |
| 2 | 116.25 | 186.75 | 70.5 | 0.86 | combined_audio_novelty | combined_novelty=0.797, chroma_change=0.653, timbre_change=0.657, onset_change=0.713, energy_change=0.458 | seg_0001 | seg_0003 | win_0002 |
| 3 | 186.75 | 244.0 | 57.25 | 0.943 | timbre_change | combined_novelty=0.762, chroma_change=0.849, timbre_change=0.875, onset_change=0.492, energy_change=0.785 | seg_0002 | seg_0004 | win_0003 |
| 4 | 244.0 | 288.0 | 44.0 | 0.705 | onset_density_change | combined_novelty=0.670, chroma_change=0.497, timbre_change=0.498, onset_change=0.595, energy_change=0.644 | seg_0003 | seg_0005 | win_0004 |
| 5 | 288.0 | 325.0 | 37.0 | 0.651 | timbre_change | combined_novelty=0.475, chroma_change=0.573, timbre_change=0.574, onset_change=0.338, energy_change=0.476 | seg_0004 | seg_0006 | win_0005 |
| 6 | 325.0 | 383.5 | 58.5 | 0.748 | combined_audio_novelty | combined_novelty=0.690, chroma_change=0.474, timbre_change=0.434, onset_change=0.564, energy_change=0.529 | seg_0005 | seg_0007 | win_0006 |
| 7 | 383.5 | 472.25 | 88.75 | 0.784 | timbre_change | combined_novelty=0.691, chroma_change=0.636, timbre_change=0.854, onset_change=0.442, energy_change=0.343 | seg_0006 | seg_0008 | win_0007 |
| 8 | 472.25 | 531.0 | 58.75 | 0.734 | onset_density_change | combined_novelty=0.674, chroma_change=0.307, timbre_change=0.469, onset_change=0.611, energy_change=0.611 | seg_0007 | seg_0009 | win_0008 |
| 9 | 531.0 | 592.5 | 61.5 | 0.73 | timbre_change | combined_novelty=0.542, chroma_change=0.300, timbre_change=0.735, onset_change=0.530, energy_change=0.416 | seg_0008 | seg_0010 | win_0009 |
| 10 | 592.5 | 656.5 | 64.0 | 0.849 | timbre_change | combined_novelty=0.606, chroma_change=0.179, timbre_change=1.000, onset_change=0.329, energy_change=0.431 | seg_0009 | seg_0011 | win_0010 |
| 11 | 656.5 | 712.75 | 56.25 | 0.791 | onset_density_change | combined_novelty=0.674, chroma_change=0.247, timbre_change=0.705, onset_change=0.827, energy_change=0.265 | seg_0010 | seg_0012 | win_0011 |
| 12 | 712.75 | 751.420952 | 38.670952 | 0.6 | combined_audio_novelty | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0011 | None | win_0012 |

## Candidate Boundaries (Accepted vs Rejected)

| time_seconds | confidence | source_feature | contributing_features | reason | status | evidence |
|---:|---:|---|---|---|---|---|
| 0.250 | 0.766918 | onset_strength | ['novelty_combined', 'onset_strength', 'rms'] | onset_density_change | rejected_or_unused | combined_novelty=0.524, chroma_change=0.107, timbre_change=0.172, onset_change=0.775, energy_change=0.434 |
| 44.750 | 0.812858 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | accepted | combined_novelty=0.722, chroma_change=0.531, timbre_change=0.477, onset_change=0.557, energy_change=0.616 |
| 79.750 | 0.704431 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.556, chroma_change=0.414, timbre_change=0.411, onset_change=0.538, energy_change=0.384 |
| 116.250 | 0.689156 | rms | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | accepted | combined_novelty=0.492, chroma_change=0.452, timbre_change=0.284, onset_change=0.301, energy_change=0.629 |
| 137.000 | 0.694994 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.517, chroma_change=0.459, timbre_change=0.573, onset_change=0.545, energy_change=0.341 |
| 145.000 | 0.884105 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.829, chroma_change=0.582, timbre_change=0.668, onset_change=0.736, energy_change=0.432 |
| 158.000 | 0.759129 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.575, chroma_change=0.567, timbre_change=0.620, onset_change=0.612, energy_change=0.312 |
| 164.000 | 0.865608 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.669, chroma_change=0.797, timbre_change=0.568, onset_change=0.562, energy_change=0.458 |
| 171.000 | 0.794999 | onset_strength | ['onset_strength'] | onset_density_change | rejected_or_unused | combined_novelty=0.922, chroma_change=0.926, timbre_change=0.624, onset_change=0.727, energy_change=0.340 |
| 186.750 | 0.917163 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.797, chroma_change=0.653, timbre_change=0.657, onset_change=0.713, energy_change=0.458 |
| 193.250 | 0.877343 | chroma_change | ['chroma_change', 'onset_strength'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.535, chroma_change=1.000, timbre_change=0.520, onset_change=0.365, energy_change=0.678 |
| 205.250 | 0.743368 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.620, chroma_change=0.427, timbre_change=0.546, onset_change=0.564, energy_change=0.535 |
| 212.500 | 1.0 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=1.000, chroma_change=0.566, timbre_change=0.564, onset_change=0.909, energy_change=0.751 |
| 221.000 | 0.951859 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.792, chroma_change=0.599, timbre_change=0.595, onset_change=0.553, energy_change=0.682 |
| 230.750 | 0.800873 | chroma_change | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.485, chroma_change=0.786, timbre_change=0.326, onset_change=0.173, energy_change=0.734 |
| 235.500 | 1.0 | novelty_combined | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.969, chroma_change=0.539, timbre_change=0.709, onset_change=0.996, energy_change=0.796 |
| 244.000 | 0.995177 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | accepted | combined_novelty=0.762, chroma_change=0.849, timbre_change=0.875, onset_change=0.492, energy_change=0.785 |
| 288.000 | 0.741641 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | onset_density_change | accepted | combined_novelty=0.670, chroma_change=0.497, timbre_change=0.498, onset_change=0.595, energy_change=0.644 |
| 320.500 | 0.688927 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.529, chroma_change=0.654, timbre_change=0.537, onset_change=0.382, energy_change=0.417 |
| 325.000 | 0.693422 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | accepted | combined_novelty=0.475, chroma_change=0.573, timbre_change=0.574, onset_change=0.338, energy_change=0.476 |
| 383.500 | 0.809861 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | combined_audio_novelty | accepted | combined_novelty=0.690, chroma_change=0.474, timbre_change=0.434, onset_change=0.564, energy_change=0.529 |
| 401.000 | 0.689259 | chroma_change | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.487, chroma_change=0.614, timbre_change=0.424, onset_change=0.224, energy_change=0.380 |
| 411.250 | 0.942984 | novelty_combined | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.823, chroma_change=0.612, timbre_change=0.656, onset_change=0.714, energy_change=0.384 |
| 472.250 | 0.836771 | timbre_change | ['onset_strength', 'timbre_change'] | timbre_change | accepted | combined_novelty=0.691, chroma_change=0.636, timbre_change=0.854, onset_change=0.442, energy_change=0.343 |
| 482.500 | 0.923712 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.726, chroma_change=0.490, timbre_change=0.629, onset_change=0.784, energy_change=0.414 |
| 489.500 | 0.687095 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.567, chroma_change=0.450, timbre_change=0.619, onset_change=0.525, energy_change=0.359 |
| 518.500 | 0.726472 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.606, chroma_change=0.470, timbre_change=0.630, onset_change=0.453, energy_change=0.420 |
| 531.000 | 0.793208 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.674, chroma_change=0.307, timbre_change=0.469, onset_change=0.611, energy_change=0.611 |
| 543.000 | 0.891827 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.758, chroma_change=0.559, timbre_change=0.637, onset_change=0.718, energy_change=0.408 |
| 548.500 | 0.737453 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.589, chroma_change=0.647, timbre_change=0.574, onset_change=0.502, energy_change=0.554 |
| 570.750 | 0.738742 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.437, chroma_change=0.282, timbre_change=0.655, onset_change=0.429, energy_change=0.343 |
| 576.750 | 0.712756 | rms | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | energy_change | rejected_or_unused | combined_novelty=0.473, chroma_change=0.379, timbre_change=0.510, onset_change=0.449, energy_change=0.672 |
| 592.500 | 0.787527 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | accepted | combined_novelty=0.542, chroma_change=0.300, timbre_change=0.735, onset_change=0.530, energy_change=0.416 |
| 611.750 | 0.862259 | chroma_change | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.781, chroma_change=0.721, timbre_change=0.435, onset_change=0.650, energy_change=0.487 |
| 628.750 | 0.890861 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.767, chroma_change=0.382, timbre_change=0.735, onset_change=0.773, energy_change=0.331 |
| 635.000 | 0.973502 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.812, chroma_change=0.843, timbre_change=0.924, onset_change=0.688, energy_change=0.578 |
| 656.500 | 0.941941 | timbre_change | ['novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | accepted | combined_novelty=0.606, chroma_change=0.179, timbre_change=1.000, onset_change=0.329, energy_change=0.431 |
| 665.250 | 0.791305 | timbre_change | ['novelty_combined', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.463, chroma_change=0.113, timbre_change=0.906, onset_change=0.139, energy_change=0.425 |
| 671.500 | 0.770519 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.602, chroma_change=0.439, timbre_change=0.615, onset_change=0.579, energy_change=0.377 |
| 676.750 | 0.692656 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.503, chroma_change=0.548, timbre_change=0.426, onset_change=0.285, energy_change=0.342 |
| 685.750 | 0.902011 | onset_strength | ['chroma_change', 'onset_strength', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.753, chroma_change=0.401, timbre_change=0.646, onset_change=0.859, energy_change=0.556 |
| 705.750 | 0.914525 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength'] | onset_density_change | rejected_or_unused | combined_novelty=0.809, chroma_change=0.541, timbre_change=0.633, onset_change=0.848, energy_change=0.349 |
| 712.750 | 0.853488 | onset_strength | ['novelty_combined', 'onset_strength', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.674, chroma_change=0.247, timbre_change=0.705, onset_change=0.827, energy_change=0.265 |

## Transcription Windows

| index | global_start | global_end | core_start | core_end | context_pre | context_post | source_segment_ids | status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 0.0 | 49.75 | 0.0 | 44.75 | 0.0 | 5.0 | ['seg_0000'] | success |
| 1 | 39.75 | 121.25 | 44.75 | 116.25 | 5.0 | 5.0 | ['seg_0001'] | success |
| 2 | 111.25 | 191.75 | 116.25 | 186.75 | 5.0 | 5.0 | ['seg_0002'] | success |
| 3 | 181.75 | 249.0 | 186.75 | 244.0 | 5.0 | 5.0 | ['seg_0003'] | success |
| 4 | 239.0 | 293.0 | 244.0 | 288.0 | 5.0 | 5.0 | ['seg_0004'] | success |
| 5 | 283.0 | 330.0 | 288.0 | 325.0 | 5.0 | 5.0 | ['seg_0005'] | success |
| 6 | 320.0 | 388.5 | 325.0 | 383.5 | 5.0 | 5.0 | ['seg_0006'] | success |
| 7 | 378.5 | 477.25 | 383.5 | 472.25 | 5.0 | 5.0 | ['seg_0007'] | success |
| 8 | 467.25 | 536.0 | 472.25 | 531.0 | 5.0 | 5.0 | ['seg_0008'] | success |
| 9 | 526.0 | 597.5 | 531.0 | 592.5 | 5.0 | 5.0 | ['seg_0009'] | success |
| 10 | 587.5 | 661.5 | 592.5 | 656.5 | 5.0 | 5.0 | ['seg_0010'] | success |
| 11 | 651.5 | 717.75 | 656.5 | 712.75 | 5.0 | 5.0 | ['seg_0011'] | success |
| 12 | 707.75 | 751.420952 | 712.75 | 751.420952 | 5.0 | 0.0 | ['seg_0012'] | success |

## Boundary Diagnostics

- confidence_range: min=`0.63137`, max=`0.954022`
- confidence_mean: `0.765383`
- rejection_reason_counts: `{'violates_min_segment_seconds': 1, 'accepted': 12, 'unused_candidate': 1, 'too_close_to_previous_boundary': 29}`

### Top 10 Rejected Candidates by Confidence

| time_seconds | tuned_confidence | source_feature | contributing_features | rejection_reason | boundary_reason | evidence |
|---:|---:|---|---|---|---|---|
| 235.5 | 0.954022 | novelty_combined | ['chroma_change', 'novelty_combined', 'rms', 'timbre_change'] | too_close_to_previous_boundary | combined_audio_novelty | combined_novelty=0.969, chroma_change=0.539, timbre_change=0.709, onset_change=0.996, energy_change=0.796 |
| 212.5 | 0.941095 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=1.000, chroma_change=0.566, timbre_change=0.564, onset_change=0.909, energy_change=0.751 |
| 635.0 | 0.931534 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | harmonic_chroma_change | combined_novelty=0.812, chroma_change=0.843, timbre_change=0.924, onset_change=0.688, energy_change=0.578 |
| 221.0 | 0.881634 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | combined_audio_novelty | combined_novelty=0.792, chroma_change=0.599, timbre_change=0.595, onset_change=0.553, energy_change=0.682 |
| 411.25 | 0.875953 | novelty_combined | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | combined_audio_novelty | combined_novelty=0.823, chroma_change=0.612, timbre_change=0.656, onset_change=0.714, energy_change=0.384 |
| 482.5 | 0.858524 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.726, chroma_change=0.490, timbre_change=0.629, onset_change=0.784, energy_change=0.414 |
| 705.75 | 0.855192 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.809, chroma_change=0.541, timbre_change=0.633, onset_change=0.848, energy_change=0.349 |
| 685.75 | 0.847759 | onset_strength | ['chroma_change', 'onset_strength', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.753, chroma_change=0.401, timbre_change=0.646, onset_change=0.859, energy_change=0.556 |
| 543.0 | 0.832663 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.758, chroma_change=0.559, timbre_change=0.637, onset_change=0.718, energy_change=0.408 |
| 145.0 | 0.831215 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | timbre_change | combined_novelty=0.829, chroma_change=0.582, timbre_change=0.668, onset_change=0.736, energy_change=0.432 |

## Review Questions

- Do these boundaries match musical phrases?
- Are segments too long or too short?
- Should threshold be stricter or looser?
- Should beat/bar snapping be added?
- Should chroma/timbre be weighted more?
