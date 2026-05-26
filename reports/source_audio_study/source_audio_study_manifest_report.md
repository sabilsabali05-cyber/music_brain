# Source Audio Study Manifest Report

- source_items_considered: `4`
- analysis_allowed_count: `0`
- analysis_blocked_count: `4`
- training_allowed_count: `0`

## Policy notes
- No source audio files were moved, modified, or deleted.
- Manifest rows separate retrieval/training/analysis authorization decisions.
- Raw audio analysis is blocked unless analysis_allowed=true per row.
- Missing local authorization config blocks all analysis via missing_local_authorization_config.
- Excluded and retrieval-only roots are never analyzed.
- Training is disabled unless explicitly allowed.
- Source-to-root authorization matching uses normalized absolute candidates and prefix matching.
