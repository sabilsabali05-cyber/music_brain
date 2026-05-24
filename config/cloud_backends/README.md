# Cloud backend config

Use local-only configuration for cloud execution scaffolding.

## Setup

- Copy `cloud_backends.example.json` to `cloud_backends.local.json`.
- Keep providers disabled until authorization and budget review are complete.
- Keep `dry_run_only=true` unless explicit approval is documented.

## Safety defaults

- Cloud execution is disabled by default.
- No cloud APIs are called by check/plan scripts.
- No uploads/downloads/jobs happen unless `execute=true` and all allow gates pass.
- Required secrets are checked by presence only; values are never printed.

## Privacy/provenance rules

- Public reports redact local paths, bucket paths, signed URLs, and device names.
- Transcription is treated as witness evidence, not truth.
- Source separation is weak evidence, not truth.
- Embeddings are semantic evidence, not truth.
