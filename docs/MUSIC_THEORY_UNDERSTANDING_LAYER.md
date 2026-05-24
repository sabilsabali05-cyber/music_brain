# Music Theory Understanding Layer v1

This layer converts existing corpus rows into confidence-aware music theory intelligence, then maps that intelligence into deterministic generation controls.

## Inputs

- `datasets/normalized_music_corpus/normalized_music_corpus.jsonl`
- `datasets/training_corpus/retrieval_only.jsonl`
- `datasets/training_corpus/review_required.jsonl`
- `datasets/music_intelligence/music_intelligence_records.jsonl` (when present)
- `reports/database/normalized_music_corpus_report.json`
- `reports/training_corpus/corpus_split_report.json`

## Core guarantees

- No ingest of new files.
- No cloud calls.
- No model training.
- No unauthorized raw audio processing.
- No fake certainty (confidence is explicit and clamped).
- Ambiguous material can be marked `not_applicable` instead of forcing Western harmony.
- No training-safe assumption.

## Outputs

- `datasets/music_theory/theory_understanding_records.jsonl`
- `datasets/music_theory/generation_conditioning_profiles.jsonl`
- `reports/music_theory/*.json`
- `reports/music_theory/*.md`
- `outputs/theory_conditioned_generation_v1/*.mid`

## Framework lenses

1. Western functional harmony
2. Jazz/extended harmony
3. Gospel/choral-ish movement
4. Modal/nonfunctional harmony
5. Neo-Riemannian/chromatic movement
6. Counterpoint/voice-leading
7. Rhythm/groove
8. Hip-hop/loop-based form
9. Texture/timbre
10. Microtonal/pitch-bend awareness (only when evidence exists)
