# Segmentation Review: Varud - Sigur Ros (Valtari).mp3

- manifest_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/segments/Varud_-_Sigur_Ros_Valtari/20260521T175649610133_audio_structure_v1/segments_manifest.json`
- run_id: `20260521T175649610133_audio_structure_v1`
- source_name: `Varud - Sigur Ros (Valtari).mp3`
- duration_seconds: `392.370794`
- strategy_requested: `audio_structure`
- strategy_used: `audio_structure_v1`
- fallback_used: `False`
- available_features: `['rms', 'onset_strength', 'chroma_change', 'timbre_change', 'novelty_combined']`
- missing_features: `[]`
- candidate_boundary_count: `6`
- accepted_boundary_count: `1`
- candidate_density: `dense`
- fused_candidate_count: `6`
- returned_candidate_count: `6`
- analysis_path: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/samples/analysis/Varud_-_Sigur_Ros_Valtari/structure_analysis.json`
- segmentation_parameters: `{'boundary_threshold': 0.55, 'min_segment_seconds': 30.0, 'max_segment_seconds': 90.0, 'rms_weight': 0.2, 'onset_weight': 0.3, 'chroma_weight': 0.25, 'timbre_weight': 0.25, 'allow_fixed_candidates': False}`

## Accepted Musical Segments

| index | start | end | duration | confidence | reason | evidence | prev | next | window |
|---|---:|---:|---:|---:|---|---|---|---|---|
| 0 | 0.0 | 60.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | None | seg_0001 | win_0000 |
| 1 | 60.0 | 120.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0000 | seg_0002 | win_0001 |
| 2 | 120.0 | 180.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0001 | seg_0003 | win_0002 |
| 3 | 180.0 | 220.0 | 40.0 | 0.561 | onset_density_change | combined_novelty=0.586, chroma_change=0.540, timbre_change=0.502, onset_change=0.605, energy_change=0.085 | seg_0002 | seg_0004 | win_0003 |
| 4 | 220.0 | 280.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0003 | seg_0005 | win_0004 |
| 5 | 280.0 | 340.0 | 60.0 | 0.2 | fixed_interval_fallback | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0004 | seg_0006 | win_0005 |
| 6 | 340.0 | 392.370794 | 52.370794 | 0.6 | combined_audio_novelty | combined_novelty=0.000, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 | seg_0005 | None | win_0006 |

## Candidate Boundaries (Accepted vs Rejected)

| time_seconds | confidence | source_feature | contributing_features | reason | status | evidence |
|---:|---:|---|---|---|---|---|
| 60.000 | 0.2 | novelty_combined | ['novelty_combined'] | fixed_interval_fallback | rejected_or_unused | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 120.000 | 0.2 | novelty_combined | ['novelty_combined'] | fixed_interval_fallback | rejected_or_unused | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 180.000 | 0.2 | novelty_combined | ['novelty_combined'] | fixed_interval_fallback | rejected_or_unused | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 220.000 | 0.586 | novelty_combined | ['novelty_combined'] | onset_density_change | accepted | combined_novelty=0.586, chroma_change=0.540, timbre_change=0.502, onset_change=0.605, energy_change=0.085 |
| 280.000 | 0.2 | novelty_combined | ['novelty_combined'] | fixed_interval_fallback | rejected_or_unused | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 340.000 | 0.2 | novelty_combined | ['novelty_combined'] | fixed_interval_fallback | rejected_or_unused | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |

## Transcription Windows

| index | global_start | global_end | core_start | core_end | context_pre | context_post | source_segment_ids | status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| 0 | 0.0 | 65.0 | 0.0 | 60.0 | 0.0 | 5.0 | ['seg_0000'] | pending |
| 1 | 55.0 | 125.0 | 60.0 | 120.0 | 5.0 | 5.0 | ['seg_0001'] | pending |
| 2 | 115.0 | 185.0 | 120.0 | 180.0 | 5.0 | 5.0 | ['seg_0002'] | pending |
| 3 | 175.0 | 225.0 | 180.0 | 220.0 | 5.0 | 5.0 | ['seg_0003'] | pending |
| 4 | 215.0 | 285.0 | 220.0 | 280.0 | 5.0 | 5.0 | ['seg_0004'] | pending |
| 5 | 275.0 | 345.0 | 280.0 | 340.0 | 5.0 | 5.0 | ['seg_0005'] | pending |
| 6 | 335.0 | 392.370794 | 340.0 | 392.370794 | 5.0 | 0.0 | ['seg_0006'] | pending |

## Boundary Diagnostics

- confidence_range: min=`0.16`, max=`0.560525`
- confidence_mean: `0.226754`
- rejection_reason_counts: `{'fixed_interval_candidate': 5, 'accepted': 1}`

### Top 10 Rejected Candidates by Confidence

| time_seconds | tuned_confidence | source_feature | contributing_features | rejection_reason | boundary_reason | evidence |
|---:|---:|---|---|---|---|---|
| 60.0 | 0.16 | novelty_combined | ['novelty_combined'] | fixed_interval_candidate | fixed_interval_fallback | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 120.0 | 0.16 | novelty_combined | ['novelty_combined'] | fixed_interval_candidate | fixed_interval_fallback | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 180.0 | 0.16 | novelty_combined | ['novelty_combined'] | fixed_interval_candidate | fixed_interval_fallback | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 280.0 | 0.16 | novelty_combined | ['novelty_combined'] | fixed_interval_candidate | fixed_interval_fallback | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |
| 340.0 | 0.16 | novelty_combined | ['novelty_combined'] | fixed_interval_candidate | fixed_interval_fallback | combined_novelty=0.200, chroma_change=0.000, timbre_change=0.000, onset_change=0.000, energy_change=0.000 |

## Review Questions

- Do these boundaries match musical phrases?
- Are segments too long or too short?
- Should threshold be stricter or looser?
- Should beat/bar snapping be added?
- Should chroma/timbre be weighted more?
