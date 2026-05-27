# Stash Recovery Inventory

- branch: `cursor/music-brain-active`
- stashes inventoried: `19`
- created for branchless recovery with unsafe-path exclusion.

## Classification Legend

- `apply_to_active_branch`: safe and directly needed now
- `keep_for_manual_review`: potentially useful but not safe/clear enough for automatic recovery
- `ignore_for_now`: unrelated or stale for current recovery target
- `unsafe_do_not_apply`: contains unsafe artifacts (audio/local configs/model caches/private paths)

## Per-Stash Inventory

- `stash@{0}` `temp-generated-report-changes-from-commit-checkpoint`
  - files changed: 42 tracked (reports + outputs + `outputs/render_ready_packs/*` + `.RPP`)
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{1}` `temp-unintended-commit-content`
  - files changed: same 42 tracked path set as `stash@{0}`
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{2}` `temp-policy-only-commit`
  - files changed: 4 tracked (`.cursor/rules/branchless-development.md`, branch hygiene/privacy reports)
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{3}` `pre-branchless-migration`
  - files changed: 9 tracked + 18 untracked (includes generated MIDI reroll artifacts)
  - contains: code=`false` reports=`true` generated_midi=`true` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{4}` `pre-music-understanding-loop-branch-switch`
  - files changed: 7 tracked (reports/outputs only)
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{5}` `temp-privacy-report-artifacts`
  - files changed: 2 tracked (`reports/privacy/*`)
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{6}` `temp-unrelated-before-commit`
  - files changed: 9 tracked (privacy/taste/source reports)
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{7}` `temp-unrelated-generated-files`
  - files changed: 9 tracked (privacy/taste/source reports)
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{8}` `post-audit-microtonal-test`
  - files changed: untracked-only stash (1 file)
  - contains: code=`true` reports=`false` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{9}` `post-audit-reviews-untracked`
  - files changed: untracked-only stash (1 file)
  - contains: code=`false` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{10}` `post-audit-preserve-unrelated`
  - files changed: 2 tracked + 37 untracked (`scripts/dev.ps1` + readiness report + extras)
  - contains: code=`true` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{11}` `temp-pre-checkpoint-all`
  - files changed: 15 tracked + 1,195 untracked (includes local config files, many `library/*` audio artifacts, model cache paths)
  - contains: code=`true` reports=`true` generated_midi=`true` source_loop.wav=`false` local_configs=`true` model_caches=`true` private_paths=`true`
  - recommended_action: `unsafe_do_not_apply`

- `stash@{12}` `temp-explicit-unrelated`
  - files changed: 15 tracked + 37 untracked (symbolic backend + setup reports/scripts)
  - contains: code=`true` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{13}` `temp-live-performance-untracked`
  - files changed: 14 tracked + 3 untracked (symbolic backend + setup reports/scripts)
  - contains: code=`true` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{14}` `temp-pre-checkpoint-unrelated-2`
  - files changed: 21 tracked + 6 untracked (includes `outputs/symbolic_ensemble_v1/selected_candidate.mid`)
  - contains: code=`true` reports=`true` generated_midi=`true` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{15}` `temp-pre-checkpoint-unrelated`
  - files changed: 13 tracked + 68 untracked
  - contains: code=`true` reports=`true` generated_midi=`true` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{16}` `temp-safe-commit-isolation`
  - files changed: 14 tracked + 58 untracked
  - contains: code=`true` reports=`true` generated_midi=`true` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `keep_for_manual_review`

- `stash@{17}` `pre-cleanup-unrelated-architecture-work-before-sample-library-merge`
  - files changed: 3 tracked + 11 untracked (agent handoff/report files)
  - contains: code=`true` reports=`true` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

- `stash@{18}` `temp-before-local-sounds-index`
  - files changed: untracked-only stash (7 files)
  - contains: code=`true` reports=`false` generated_midi=`false` source_loop.wav=`false` local_configs=`false` model_caches=`false` private_paths=`false`
  - recommended_action: `ignore_for_now`

## Selective-Apply Decision

- No stash was auto-applied.
- The only stash explicitly marked unsafe is `stash@{11}` due to local configs/audio/model-cache/private-path risk.
- Mixed-content stashes were left intact for manual review to keep branchless recovery safe.
