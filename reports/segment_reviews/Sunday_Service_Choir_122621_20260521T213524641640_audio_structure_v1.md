# Segmentation Review: Sunday Service Choir 122621.mp3

- manifest_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/segments/Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1/segments_manifest.json`
- run_id: `20260521T213524641640_audio_structure_v1`
- source_name: `Sunday Service Choir 122621.mp3`
- duration_seconds: `3324.842086`
- strategy_requested: `audio_structure`
- strategy_used: `audio_structure_v1`
- fallback_used: `False`
- available_features: `['rms', 'onset_strength', 'chroma_change', 'timbre_change', 'novelty_combined']`
- missing_features: `[]`
- candidate_boundary_count: `43`
- accepted_boundary_count: `20`
- candidate_density: `dense`
- fused_candidate_count: `986`
- returned_candidate_count: `43`
- analysis_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/analysis/Sunday_Service_Choir_122621/20260521T213424878654_modal_librosa_dense/structure_analysis.json`
- segmentation_parameters: `{'boundary_threshold': 0.55, 'min_segment_seconds': 30.0, 'max_segment_seconds': 90.0, 'rms_weight': 0.2, 'onset_weight': 0.3, 'chroma_weight': 0.25, 'timbre_weight': 0.25, 'allow_fixed_candidates': False}`

## Accepted Musical Segments

| index | start | end | duration | confidence | reason | evidence | prev | next | window |
|---|---:|---:|---:|---:|---|---|---|---|---|
| 0 | 0.0 | 60.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | None | seg_0001 | win_0000 |
| 1 | 60.0 | 120.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0000 | seg_0002 | win_0001 |
| 2 | 120.0 | 180.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0001 | seg_0003 | win_0002 |
| 3 | 180.0 | 253.25 | 73.25 | 0.798 | combined_audio_novelty | combined_novelty=0.777, chroma_change=0.426, timbre_change=0.639, onset_change=0.768, energy_change=0.318 | seg_0002 | seg_0004 | win_0003 |
| 4 | 253.25 | 313.25 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0003 | seg_0005 | win_0004 |
| 5 | 313.25 | 372.5 | 59.25 | 0.86 | onset_density_change | combined_novelty=0.906, chroma_change=0.603, timbre_change=0.689, onset_change=0.740, energy_change=0.405 | seg_0004 | seg_0006 | win_0005 |
| 6 | 372.5 | 438.5 | 66.0 | 0.817 | onset_density_change | combined_novelty=0.807, chroma_change=0.390, timbre_change=0.668, onset_change=0.815, energy_change=0.032 | seg_0005 | seg_0007 | win_0006 |
| 7 | 438.5 | 498.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0006 | seg_0008 | win_0007 |
| 8 | 498.5 | 558.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0007 | seg_0009 | win_0008 |
| 9 | 558.5 | 644.0 | 85.5 | 0.788 | combined_audio_novelty | combined_novelty=0.749, chroma_change=0.439, timbre_change=0.570, onset_change=0.567, energy_change=0.220 | seg_0008 | seg_0010 | win_0009 |
| 10 | 644.0 | 683.5 | 39.5 | 0.865 | combined_audio_novelty | combined_novelty=0.869, chroma_change=0.434, timbre_change=0.520, onset_change=0.698, energy_change=0.396 | seg_0009 | seg_0011 | win_0010 |
| 11 | 683.5 | 773.25 | 89.75 | 0.811 | onset_density_change | combined_novelty=0.706, chroma_change=0.347, timbre_change=0.569, onset_change=0.799, energy_change=0.210 | seg_0010 | seg_0012 | win_0011 |
| 12 | 773.25 | 853.0 | 79.75 | 0.869 | combined_audio_novelty | combined_novelty=0.827, chroma_change=0.504, timbre_change=0.677, onset_change=0.679, energy_change=0.300 | seg_0011 | seg_0013 | win_0012 |
| 13 | 853.0 | 913.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0012 | seg_0014 | win_0013 |
| 14 | 913.0 | 964.0 | 51.0 | 0.778 | combined_audio_novelty | combined_novelty=0.692, chroma_change=0.419, timbre_change=0.632, onset_change=0.530, energy_change=0.288 | seg_0013 | seg_0015 | win_0014 |
| 15 | 964.0 | 1024.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0014 | seg_0016 | win_0015 |
| 16 | 1024.0 | 1092.75 | 68.75 | 0.924 | onset_density_change | combined_novelty=0.912, chroma_change=0.487, timbre_change=0.609, onset_change=0.929, energy_change=0.326 | seg_0015 | seg_0017 | win_0016 |
| 17 | 1092.75 | 1162.0 | 69.25 | 0.859 | onset_density_change | combined_novelty=0.876, chroma_change=0.521, timbre_change=0.694, onset_change=0.712, energy_change=0.292 | seg_0016 | seg_0018 | win_0017 |
| 18 | 1162.0 | 1222.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0017 | seg_0019 | win_0018 |
| 19 | 1222.0 | 1280.75 | 58.75 | 0.789 | timbre_change | combined_novelty=0.723, chroma_change=0.478, timbre_change=0.799, onset_change=0.625, energy_change=0.241 | seg_0018 | seg_0020 | win_0019 |
| 20 | 1280.75 | 1340.75 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0019 | seg_0021 | win_0020 |
| 21 | 1340.75 | 1400.75 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0020 | seg_0022 | win_0021 |
| 22 | 1400.75 | 1460.75 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0021 | seg_0023 | win_0022 |
| 23 | 1460.75 | 1520.75 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0022 | seg_0024 | win_0023 |
| 24 | 1520.75 | 1580.75 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0023 | seg_0025 | win_0024 |
| 25 | 1580.75 | 1640.75 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0024 | seg_0026 | win_0025 |
| 26 | 1640.75 | 1700.75 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0025 | seg_0027 | win_0026 |
| 27 | 1700.75 | 1761.5 | 60.75 | 0.834 | combined_audio_novelty | combined_novelty=0.796, chroma_change=0.469, timbre_change=0.657, onset_change=0.714, energy_change=0.057 | seg_0026 | seg_0028 | win_0027 |
| 28 | 1761.5 | 1821.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0027 | seg_0029 | win_0028 |
| 29 | 1821.5 | 1881.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0028 | seg_0030 | win_0029 |
| 30 | 1881.5 | 1941.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0029 | seg_0031 | win_0030 |
| 31 | 1941.5 | 2001.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0030 | seg_0032 | win_0031 |
| 32 | 2001.5 | 2061.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0031 | seg_0033 | win_0032 |
| 33 | 2061.5 | 2121.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0032 | seg_0034 | win_0033 |
| 34 | 2121.5 | 2181.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0033 | seg_0035 | win_0034 |
| 35 | 2181.5 | 2241.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0034 | seg_0036 | win_0035 |
| 36 | 2241.5 | 2301.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0035 | seg_0037 | win_0036 |
| 37 | 2301.5 | 2361.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0036 | seg_0038 | win_0037 |
| 38 | 2361.5 | 2421.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0037 | seg_0039 | win_0038 |
| 39 | 2421.5 | 2481.5 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0038 | seg_0040 | win_0039 |
| 40 | 2481.5 | 2550.75 | 69.25 | 0.904 | harmonic_chroma_change | combined_novelty=0.746, chroma_change=1.000, timbre_change=0.510, onset_change=0.417, energy_change=0.095 | seg_0039 | seg_0041 | win_0040 |
| 41 | 2550.75 | 2638.75 | 88.0 | 0.738 | combined_audio_novelty | combined_novelty=0.689, chroma_change=0.626, timbre_change=0.553, onset_change=0.427, energy_change=0.151 | seg_0040 | seg_0042 | win_0041 |
| 42 | 2638.75 | 2688.75 | 50.0 | 0.868 | combined_audio_novelty | combined_novelty=0.868, chroma_change=0.673, timbre_change=0.703, onset_change=0.591, energy_change=0.138 | seg_0041 | seg_0043 | win_0042 |
| 43 | 2688.75 | 2741.25 | 52.5 | 0.886 | combined_audio_novelty | combined_novelty=0.851, chroma_change=0.628, timbre_change=0.816, onset_change=0.549, energy_change=0.102 | seg_0042 | seg_0044 | win_0043 |
| 44 | 2741.25 | 2788.5 | 47.25 | 0.774 | combined_audio_novelty | combined_novelty=0.800, chroma_change=0.641, timbre_change=0.671, onset_change=0.512, energy_change=0.127 | seg_0043 | seg_0045 | win_0044 |
| 45 | 2788.5 | 2876.0 | 87.5 | 0.763 | onset_density_change | combined_novelty=0.913, chroma_change=0.685, timbre_change=0.870, onset_change=0.563, energy_change=0.185 | seg_0044 | seg_0046 | win_0045 |
| 46 | 2876.0 | 2936.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0045 | seg_0047 | win_0046 |
| 47 | 2936.0 | 2996.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0046 | seg_0048 | win_0047 |
| 48 | 2996.0 | 3056.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0047 | seg_0049 | win_0048 |
| 49 | 3056.0 | 3116.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0048 | seg_0050 | win_0049 |
| 50 | 3116.0 | 3170.25 | 54.25 | 0.775 | energy_change | combined_novelty=0.552, chroma_change=0.150, timbre_change=0.232, onset_change=0.160, energy_change=1.000 | seg_0049 | seg_0051 | win_0050 |
| 51 | 3170.25 | 3230.25 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0050 | seg_0052 | win_0051 |
| 52 | 3230.25 | 3270.25 | 40.0 | 0.823 | combined_audio_novelty | combined_novelty=0.820, chroma_change=0.787, timbre_change=0.528, onset_change=0.614, energy_change=0.019 | seg_0051 | seg_0053 | win_0052 |
| 53 | 3270.25 | 3324.842086 | 54.592086 | 0.6 | combined_audio_novelty | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0052 | None | win_0053 |

## Candidate Boundaries (Accepted vs Rejected)

| time_seconds | confidence | source_feature | contributing_features | reason | status | evidence |
|---:|---:|---|---|---|---|---|
| 210.750 | 0.883947 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength'] | onset_density_change | rejected_or_unused | combined_novelty=0.758, chroma_change=0.384, timbre_change=0.447, onset_change=0.829, energy_change=0.139 |
| 253.250 | 0.857009 | novelty_combined | ['novelty_combined', 'onset_strength', 'rms'] | combined_audio_novelty | accepted | combined_novelty=0.777, chroma_change=0.426, timbre_change=0.639, onset_change=0.768, energy_change=0.318 |
| 365.500 | 0.814774 | novelty_combined | ['chroma_change', 'novelty_combined'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.775, chroma_change=0.404, timbre_change=0.410, onset_change=0.814, energy_change=0.188 |
| 372.500 | 0.918283 | onset_strength | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.906, chroma_change=0.603, timbre_change=0.689, onset_change=0.740, energy_change=0.405 |
| 402.500 | 0.826797 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.707, chroma_change=0.530, timbre_change=0.562, onset_change=0.415, energy_change=0.444 |
| 438.500 | 0.892186 | onset_strength | ['chroma_change', 'onset_strength', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.807, chroma_change=0.390, timbre_change=0.668, onset_change=0.815, energy_change=0.032 |
| 644.000 | 0.868708 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.749, chroma_change=0.439, timbre_change=0.570, onset_change=0.567, energy_change=0.220 |
| 675.750 | 0.868305 | onset_strength | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.737, chroma_change=0.373, timbre_change=0.555, onset_change=0.755, energy_change=0.338 |
| 683.500 | 0.948872 | novelty_combined | ['novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.869, chroma_change=0.434, timbre_change=0.520, onset_change=0.698, energy_change=0.396 |
| 773.250 | 0.886375 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.706, chroma_change=0.347, timbre_change=0.569, onset_change=0.799, energy_change=0.210 |
| 781.250 | 0.946762 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.853, chroma_change=0.585, timbre_change=0.581, onset_change=0.813, energy_change=0.189 |
| 789.000 | 0.960764 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | onset_density_change | rejected_or_unused | combined_novelty=0.894, chroma_change=0.498, timbre_change=0.721, onset_change=0.812, energy_change=0.355 |
| 853.000 | 0.946757 | novelty_combined | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.827, chroma_change=0.504, timbre_change=0.677, onset_change=0.679, energy_change=0.300 |
| 869.000 | 1.0 | onset_strength | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=1.000, chroma_change=0.487, timbre_change=0.510, onset_change=1.000, energy_change=0.544 |
| 964.000 | 0.852316 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.692, chroma_change=0.419, timbre_change=0.632, onset_change=0.530, energy_change=0.288 |
| 1060.250 | 0.853353 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.733, chroma_change=0.513, timbre_change=0.530, onset_change=0.551, energy_change=0.161 |
| 1092.750 | 1.0 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.912, chroma_change=0.487, timbre_change=0.609, onset_change=0.929, energy_change=0.326 |
| 1157.500 | 0.852293 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.833, chroma_change=0.583, timbre_change=0.543, onset_change=0.616, energy_change=0.342 |
| 1162.000 | 0.929254 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.876, chroma_change=0.521, timbre_change=0.694, onset_change=0.712, energy_change=0.292 |
| 1166.500 | 0.8711 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.860, chroma_change=0.480, timbre_change=0.704, onset_change=0.631, energy_change=0.284 |
| 1268.000 | 0.935733 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.859, chroma_change=0.282, timbre_change=0.809, onset_change=0.793, energy_change=0.191 |
| 1274.750 | 0.848005 | onset_strength | ['novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | onset_density_change | rejected_or_unused | combined_novelty=0.805, chroma_change=0.209, timbre_change=0.813, onset_change=0.686, energy_change=0.302 |
| 1280.750 | 0.846916 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | accepted | combined_novelty=0.723, chroma_change=0.478, timbre_change=0.799, onset_change=0.625, energy_change=0.241 |
| 1290.250 | 0.954036 | novelty_combined | ['novelty_combined', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.914, chroma_change=0.226, timbre_change=0.816, onset_change=0.905, energy_change=0.228 |
| 1761.500 | 0.915918 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.796, chroma_change=0.469, timbre_change=0.657, onset_change=0.714, energy_change=0.057 |
| 2538.250 | 0.896549 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.777, chroma_change=0.669, timbre_change=0.601, onset_change=0.692, energy_change=0.115 |
| 2550.750 | 1.0 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | harmonic_chroma_change | accepted | combined_novelty=0.746, chroma_change=1.000, timbre_change=0.510, onset_change=0.417, energy_change=0.095 |
| 2574.750 | 0.819221 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.508, chroma_change=0.528, timbre_change=0.802, onset_change=0.298, energy_change=0.056 |
| 2638.750 | 0.809406 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.689, chroma_change=0.626, timbre_change=0.553, onset_change=0.427, energy_change=0.151 |
| 2643.250 | 0.838736 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | rejected_or_unused | combined_novelty=0.719, chroma_change=0.608, timbre_change=0.642, onset_change=0.512, energy_change=0.195 |
| 2649.500 | 0.822232 | timbre_change | ['onset_strength', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.853, chroma_change=0.674, timbre_change=0.744, onset_change=0.561, energy_change=0.101 |
| 2673.500 | 0.822898 | chroma_change | ['chroma_change', 'onset_strength'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.819, chroma_change=0.764, timbre_change=0.686, onset_change=0.455, energy_change=0.104 |
| 2688.750 | 0.948399 | novelty_combined | ['novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.868, chroma_change=0.673, timbre_change=0.703, onset_change=0.591, energy_change=0.138 |
| 2707.500 | 0.922146 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.847, chroma_change=0.501, timbre_change=0.778, onset_change=0.692, energy_change=0.146 |
| 2712.500 | 0.841477 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.656, chroma_change=0.414, timbre_change=0.757, onset_change=0.509, energy_change=0.150 |
| 2741.250 | 0.970875 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.851, chroma_change=0.628, timbre_change=0.816, onset_change=0.549, energy_change=0.102 |
| 2756.000 | 0.828374 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.817, chroma_change=0.709, timbre_change=0.821, onset_change=0.377, energy_change=0.156 |
| 2788.500 | 0.840203 | novelty_combined | ['novelty_combined', 'timbre_change'] | combined_audio_novelty | accepted | combined_novelty=0.800, chroma_change=0.641, timbre_change=0.671, onset_change=0.512, energy_change=0.127 |
| 2817.250 | 0.827842 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | timbre_change | rejected_or_unused | combined_novelty=0.666, chroma_change=0.425, timbre_change=0.730, onset_change=0.513, energy_change=0.163 |
| 2876.000 | 0.805212 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | onset_density_change | accepted | combined_novelty=0.913, chroma_change=0.685, timbre_change=0.870, onset_change=0.563, energy_change=0.185 |
| 2899.000 | 0.863947 | chroma_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | harmonic_chroma_change | rejected_or_unused | combined_novelty=0.612, chroma_change=0.834, timbre_change=0.599, onset_change=0.491, energy_change=0.150 |
| 3170.250 | 0.883161 | rms | ['novelty_combined', 'rms'] | energy_change | accepted | combined_novelty=0.552, chroma_change=0.150, timbre_change=0.232, onset_change=0.160, energy_change=1.000 |
| 3270.250 | 0.899917 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength'] | combined_audio_novelty | accepted | combined_novelty=0.820, chroma_change=0.787, timbre_change=0.528, onset_change=0.614, energy_change=0.019 |

## Transcription Windows

| index | global_start | global_end | core_start | core_end | context_pre | context_post | source_segment_ids | status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 0.0 | 65.0 | 0.0 | 60.0 | 0.0 | 5.0 | ['seg_0000'] | success |
| 1 | 55.0 | 125.0 | 60.0 | 120.0 | 5.0 | 5.0 | ['seg_0001'] | success |
| 2 | 115.0 | 185.0 | 120.0 | 180.0 | 5.0 | 5.0 | ['seg_0002'] | success |
| 3 | 175.0 | 258.25 | 180.0 | 253.25 | 5.0 | 5.0 | ['seg_0003'] | success |
| 4 | 248.25 | 318.25 | 253.25 | 313.25 | 5.0 | 5.0 | ['seg_0004'] | success |
| 5 | 308.25 | 377.5 | 313.25 | 372.5 | 5.0 | 5.0 | ['seg_0005'] | success |
| 6 | 367.5 | 443.5 | 372.5 | 438.5 | 5.0 | 5.0 | ['seg_0006'] | success |
| 7 | 433.5 | 503.5 | 438.5 | 498.5 | 5.0 | 5.0 | ['seg_0007'] | success |
| 8 | 493.5 | 563.5 | 498.5 | 558.5 | 5.0 | 5.0 | ['seg_0008'] | success |
| 9 | 553.5 | 649.0 | 558.5 | 644.0 | 5.0 | 5.0 | ['seg_0009'] | success |
| 10 | 639.0 | 688.5 | 644.0 | 683.5 | 5.0 | 5.0 | ['seg_0010'] | success |
| 11 | 678.5 | 778.25 | 683.5 | 773.25 | 5.0 | 5.0 | ['seg_0011'] | success |
| 12 | 768.25 | 858.0 | 773.25 | 853.0 | 5.0 | 5.0 | ['seg_0012'] | success |
| 13 | 848.0 | 918.0 | 853.0 | 913.0 | 5.0 | 5.0 | ['seg_0013'] | success |
| 14 | 908.0 | 969.0 | 913.0 | 964.0 | 5.0 | 5.0 | ['seg_0014'] | success |
| 15 | 959.0 | 1029.0 | 964.0 | 1024.0 | 5.0 | 5.0 | ['seg_0015'] | success |
| 16 | 1019.0 | 1097.75 | 1024.0 | 1092.75 | 5.0 | 5.0 | ['seg_0016'] | success |
| 17 | 1087.75 | 1167.0 | 1092.75 | 1162.0 | 5.0 | 5.0 | ['seg_0017'] | success |
| 18 | 1157.0 | 1227.0 | 1162.0 | 1222.0 | 5.0 | 5.0 | ['seg_0018'] | success |
| 19 | 1217.0 | 1285.75 | 1222.0 | 1280.75 | 5.0 | 5.0 | ['seg_0019'] | success |
| 20 | 1275.75 | 1345.75 | 1280.75 | 1340.75 | 5.0 | 5.0 | ['seg_0020'] | success |
| 21 | 1335.75 | 1405.75 | 1340.75 | 1400.75 | 5.0 | 5.0 | ['seg_0021'] | success |
| 22 | 1395.75 | 1465.75 | 1400.75 | 1460.75 | 5.0 | 5.0 | ['seg_0022'] | success |
| 23 | 1455.75 | 1525.75 | 1460.75 | 1520.75 | 5.0 | 5.0 | ['seg_0023'] | success |
| 24 | 1515.75 | 1585.75 | 1520.75 | 1580.75 | 5.0 | 5.0 | ['seg_0024'] | success |
| 25 | 1575.75 | 1645.75 | 1580.75 | 1640.75 | 5.0 | 5.0 | ['seg_0025'] | success |
| 26 | 1635.75 | 1705.75 | 1640.75 | 1700.75 | 5.0 | 5.0 | ['seg_0026'] | success |
| 27 | 1695.75 | 1766.5 | 1700.75 | 1761.5 | 5.0 | 5.0 | ['seg_0027'] | success |
| 28 | 1756.5 | 1826.5 | 1761.5 | 1821.5 | 5.0 | 5.0 | ['seg_0028'] | success |
| 29 | 1816.5 | 1886.5 | 1821.5 | 1881.5 | 5.0 | 5.0 | ['seg_0029'] | success |
| 30 | 1876.5 | 1946.5 | 1881.5 | 1941.5 | 5.0 | 5.0 | ['seg_0030'] | success |
| 31 | 1936.5 | 2006.5 | 1941.5 | 2001.5 | 5.0 | 5.0 | ['seg_0031'] | success |
| 32 | 1996.5 | 2066.5 | 2001.5 | 2061.5 | 5.0 | 5.0 | ['seg_0032'] | success |
| 33 | 2056.5 | 2126.5 | 2061.5 | 2121.5 | 5.0 | 5.0 | ['seg_0033'] | success |
| 34 | 2116.5 | 2186.5 | 2121.5 | 2181.5 | 5.0 | 5.0 | ['seg_0034'] | success |
| 35 | 2176.5 | 2246.5 | 2181.5 | 2241.5 | 5.0 | 5.0 | ['seg_0035'] | success |
| 36 | 2236.5 | 2306.5 | 2241.5 | 2301.5 | 5.0 | 5.0 | ['seg_0036'] | success |
| 37 | 2296.5 | 2366.5 | 2301.5 | 2361.5 | 5.0 | 5.0 | ['seg_0037'] | success |
| 38 | 2356.5 | 2426.5 | 2361.5 | 2421.5 | 5.0 | 5.0 | ['seg_0038'] | success |
| 39 | 2416.5 | 2486.5 | 2421.5 | 2481.5 | 5.0 | 5.0 | ['seg_0039'] | success |
| 40 | 2476.5 | 2555.75 | 2481.5 | 2550.75 | 5.0 | 5.0 | ['seg_0040'] | success |
| 41 | 2545.75 | 2643.75 | 2550.75 | 2638.75 | 5.0 | 5.0 | ['seg_0041'] | success |
| 42 | 2633.75 | 2693.75 | 2638.75 | 2688.75 | 5.0 | 5.0 | ['seg_0042'] | success |
| 43 | 2683.75 | 2746.25 | 2688.75 | 2741.25 | 5.0 | 5.0 | ['seg_0043'] | success |
| 44 | 2736.25 | 2793.5 | 2741.25 | 2788.5 | 5.0 | 5.0 | ['seg_0044'] | success |
| 45 | 2783.5 | 2881.0 | 2788.5 | 2876.0 | 5.0 | 5.0 | ['seg_0045'] | success |
| 46 | 2871.0 | 2941.0 | 2876.0 | 2936.0 | 5.0 | 5.0 | ['seg_0046'] | success |
| 47 | 2931.0 | 3001.0 | 2936.0 | 2996.0 | 5.0 | 5.0 | ['seg_0047'] | success |
| 48 | 2991.0 | 3061.0 | 2996.0 | 3056.0 | 5.0 | 5.0 | ['seg_0048'] | success |
| 49 | 3051.0 | 3121.0 | 3056.0 | 3116.0 | 5.0 | 5.0 | ['seg_0049'] | success |
| 50 | 3111.0 | 3175.25 | 3116.0 | 3170.25 | 5.0 | 5.0 | ['seg_0050'] | success |
| 51 | 3165.25 | 3235.25 | 3170.25 | 3230.25 | 5.0 | 5.0 | ['seg_0051'] | success |
| 52 | 3225.25 | 3275.25 | 3230.25 | 3270.25 | 5.0 | 5.0 | ['seg_0052'] | success |
| 53 | 3265.25 | 3324.842086 | 3270.25 | 3324.842086 | 5.0 | 0.0 | ['seg_0053'] | success |

## Boundary Diagnostics

- confidence_range: min=`0.738065`, max=`0.931635`
- confidence_mean: `0.814609`
- rejection_reason_counts: `{'unused_candidate': 3, 'accepted': 20, 'too_close_to_previous_boundary': 20}`

### Top 10 Rejected Candidates by Confidence

| time_seconds | tuned_confidence | source_feature | contributing_features | rejection_reason | boundary_reason | evidence |
|---:|---:|---|---|---|---|---|
| 869.0 | 0.931635 | onset_strength | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=1.000, chroma_change=0.487, timbre_change=0.510, onset_change=1.000, energy_change=0.544 |
| 789.0 | 0.892467 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.894, chroma_change=0.498, timbre_change=0.721, onset_change=0.812, energy_change=0.355 |
| 1290.25 | 0.878695 | novelty_combined | ['novelty_combined', 'timbre_change'] | too_close_to_previous_boundary | combined_audio_novelty | combined_novelty=0.914, chroma_change=0.226, timbre_change=0.816, onset_change=0.905, energy_change=0.228 |
| 781.25 | 0.872035 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.853, chroma_change=0.585, timbre_change=0.581, onset_change=0.813, energy_change=0.189 |
| 1268.0 | 0.858285 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.859, chroma_change=0.282, timbre_change=0.809, onset_change=0.793, energy_change=0.191 |
| 2707.5 | 0.849055 | timbre_change | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | too_close_to_previous_boundary | timbre_change | combined_novelty=0.847, chroma_change=0.501, timbre_change=0.778, onset_change=0.692, energy_change=0.146 |
| 2538.25 | 0.826888 | novelty_combined | ['chroma_change', 'novelty_combined', 'onset_strength', 'timbre_change'] | too_close_to_previous_boundary | combined_audio_novelty | combined_novelty=0.777, chroma_change=0.669, timbre_change=0.601, onset_change=0.692, energy_change=0.115 |
| 1166.5 | 0.805289 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.860, chroma_change=0.480, timbre_change=0.704, onset_change=0.631, energy_change=0.284 |
| 210.75 | 0.80398 | onset_strength | ['chroma_change', 'novelty_combined', 'onset_strength'] | unused_candidate | onset_density_change | combined_novelty=0.758, chroma_change=0.384, timbre_change=0.447, onset_change=0.829, energy_change=0.139 |
| 675.75 | 0.79988 | onset_strength | ['chroma_change', 'onset_strength', 'rms', 'timbre_change'] | too_close_to_previous_boundary | onset_density_change | combined_novelty=0.737, chroma_change=0.373, timbre_change=0.555, onset_change=0.755, energy_change=0.338 |

## Review Questions

- Do these boundaries match musical phrases?
- Are segments too long or too short?
- Should threshold be stricter or looser?
- Should beat/bar snapping be added?
- Should chroma/timbre be weighted more?
