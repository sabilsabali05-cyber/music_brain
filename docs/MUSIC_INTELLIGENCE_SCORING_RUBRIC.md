# Music Intelligence Scoring Rubric

The scoring module computes deterministic `0.0..1.0` scores from strict schema records.

## Computed Scores

- `tempo_structure_score`
- `harmony_score`
- `bass_melody_score`
- `rhythm_score`
- `texture_score`
- `transcription_reliability_score`
- `emotional_value_score`
- `weirdness_value_score`
- `junk_penalty`
- `policy_completeness_score`
- `overall_music_value_score`
- `retrieval_value_score`
- `training_value_score`

## Rule Mapping

- Strong harmony and clear chord movement increase `harmony_score`.
- Clear bass movement and melodic contour increase `bass_melody_score`.
- Recurring motifs increase motif development contribution used in bass/melody and overall value.
- Stable groove OR intentional rhythmic complexity increases `rhythm_score`.
- Noisy/junk moments increase `junk_penalty` and reduce `overall_music_value_score`.
- Low transcription confidence suppresses `training_value_score` but can still retain retrieval value.
- Missing policy fields force `training_value_score` to zero.
- Missing labels force `training_value_score` to zero.

## Aggregation

- `overall_music_value_score` combines tempo, harmony, bass/melody, rhythm, texture, emotional value, weirdness value, and motif development, then subtracts weighted junk penalty.
- `retrieval_value_score` emphasizes overall music value with partial credit for transcription reliability and policy completeness.
- `training_value_score` starts from retrieval value and is hard-blocked by missing policy or labels.

## Determinism

- No model calls, cloud calls, or random sampling are used.
- Scores are pure functions of `MusicIntelligenceRecord`.
- Inputs are clamped and normalized before arithmetic.
