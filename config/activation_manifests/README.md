# Activation Manifests

Use activation manifests to plan or run the full model activation scaffold with strict safety gates.

## Quick Start

1. Copy `full_activation.example.json` to `full_activation.local.json`.
2. Keep `execute=false` and all `allow_flags` false until explicit authorization review is complete.
3. Run:
   - `scripts\dev.cmd plan-full-model-activation config/activation_manifests/full_activation.example.json`
   - `scripts\dev.cmd run-full-model-activation config/activation_manifests/full_activation.example.json`

## Safety Rules

- Audio is never processed unless `execute=true` and required `allow_flags` are true.
- Every input must include `explicitly_authorized_for_execution=true` and an allowed `authorization_status`.
- Training export is blocked unless both `training_allowed=true` and `human_review_required=true`.
- Planner/runner reports are public-redacted and must not expose private machine paths.

## Local File Policy

- Local manifests belong in `*.local.json`.
- Local manifests are git-ignored by default.
