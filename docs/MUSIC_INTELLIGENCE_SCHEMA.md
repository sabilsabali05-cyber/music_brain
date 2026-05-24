# Music Intelligence Schema

This schema defines strict typed objects for canonical music intelligence records with deterministic validation and redaction.

## Core Objects

- `MusicIntelligenceRecord`: Root record containing normalized source metadata, feature groups, moments, policy outcome, and provenance.
- `TempoStructureFeatures`: Tempo stability, structure clarity, motif recurrence, section count.
- `HarmonyTonalityFeatures`: Harmonic richness, chord movement strength, tonality confidence, modulation interest.
- `BassMelodyFeatures`: Bass motion clarity, melodic contour strength, motif development, counterpoint interest.
- `RhythmFeatures`: Groove stability, rhythmic complexity, syncopation interest, timing confidence.
- `TextureInstrumentationFeatures`: Texture clarity, instrumentation diversity, arrangement evolution, noise penalty.
- `ValueMoment`: Time-bounded musically valuable moment in seconds with optional bar/beat references.
- `JunkMoment`: Time-bounded noisy or low-value moment in seconds with optional bar/beat references.
- `PolicyOutcome`: Authorization, training/retrieval permissions, policy completeness, label completeness, policy exclusion flag.
- `FeatureProvenance`: Source artifact and redacted source path plus extractor identity and confidence.
- `PromotionDecision`: Deterministic promotion label (`training_safe`, `retrieval_only`, `excluded`) and blockers.

## Validation Rules

- Score-like fields are clamped to `0.0..1.0`.
- Time ranges use seconds and enforce `start_seconds >= 0` and `end_seconds >= start_seconds`.
- `bpm_estimate` range is `20..320`.
- `source_path_redacted` is always redacted and may not contain private local paths or raw URLs.
- Authorization and promotion labels are normalized and validated against fixed enum-like sets.

## Null Behavior

- Numeric feature fields are nullable and represent unknown/not observed values.
- Completeness booleans (`has_complete_*`) explicitly encode whether critical fields are populated.
- Optional confidence fields default to null and are only used when present.
- Missing labels or policy completeness is preserved as explicit booleans in `PolicyOutcome`.

## Provenance Requirements

- Every record carries `FeatureProvenance`.
- Provenance must include:
  - `source_artifact`
  - `source_path_redacted` (redacted, no private paths, no raw URLs)
  - `extractor_name`
  - `extractor_version`
- Optional `confidence` and `notes` are allowed but still clamped/redacted as applicable.
