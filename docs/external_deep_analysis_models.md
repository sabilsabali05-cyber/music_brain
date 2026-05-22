# External Deep Analysis Models

## Roles and Boundaries

- `YourMT3` remains the transcription backbone and primary symbolic source.
- `Essentia` is an optional local descriptor witness for rhythm/tonal/spectral/high-level signals.
- `musicnn` is an optional local tag witness for semantic audio labels.
- External providers are **witness signals, not truth**. They can support or challenge internal inferences, but they do not override core YourMT3-driven outputs.

## Optionality and Failure Behavior

- External providers are first-class but optional.
- Missing dependencies must not break the pipeline.
- Unavailable providers write structured JSON artifacts with:
  - `provider_name`
  - `status` (`unavailable` or `failed`)
  - dependency/install notes
  - limitations and warnings
- Feature extraction defaults to internal-only behavior unless explicitly enabled with:
  - `--include-external-analyzers`
  - `--external-providers essentia,musicnn`

## Data Governance

- Only authorized local audio from `performance_manifest.json` is used.
- No audio is sent to third-party APIs.
- No new transcription flow is introduced.
- No embeddings database, model training, or UI/database changes are required.
- AI JSONL records store only compact summaries and file references for external outputs, not huge embedding arrays.

## Licensing Caution (Essentia)

- Essentia usage can involve AGPL/commercial licensing considerations depending on deployment and distribution model.
- Teams should review legal requirements before production/commercial rollout.
