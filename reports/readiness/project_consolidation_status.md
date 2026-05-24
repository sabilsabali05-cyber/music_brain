# Project Consolidation Readiness Dashboard

## Scope
- repo_root: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain`
- current_branch: `cursor/actually-activate-moonbeam-hf-v1`
- main_hash: `5a85e10f98d9115c2395b316e68ad81f026b9711`
- current_head_hash_before_commit: `e22c494dc0f4dc89e39b894b2fa56d4535df1f05`

## Branch Landscape
- Active branches (recent): `cursor/actually-activate-moonbeam-hf-v1`, `cursor/activate-symbolic-backends-v1`, `cursor/ableton-agent-bridge-v1`, `cursor/cloud-full-activation-v1`, `backup/mixed-cloud-ableton-before-split`, `main`
- Requested branches present: Ableton bridge, symbolic activation, moonbeam HF activation, cloud/full activation family are present
- Requested microtonal/hum-to-midi branches: not present by branch name in local/remote refs

### Merge-Ready (ahead, not behind main)
- `cursor/ableton-agent-bridge-v1` (ahead 3, behind 0)
- `cursor/actually-activate-moonbeam-hf-v1` (ahead 2, behind 0)
- `cursor/activate-symbolic-backends-v1` (ahead 1, behind 0)
- `cursor/cloud-full-activation-v1` (ahead 1, behind 0)
- `backup/mixed-cloud-ableton-before-split` (ahead 1, behind 0)

### Stale / Sibling / Conflicting
- Stale: `cursor/music-data-explainer-v1`, `cursor/moonbeam-feasibility-spike`, `cursor/synplant-puredata-generative-architecture`, `cursor/synplant-seed-selection-architecture`
- Sibling overlap family: `cursor/activate-symbolic-backends-v1`, `cursor/actually-activate-moonbeam-hf-v1`, `cursor/full-model-activation-pipeline-v1`, `cursor/cloud-full-activation-v1`
- Highest overlap conflicts:
  - `cursor/activate-symbolic-backends-v1` vs `cursor/actually-activate-moonbeam-hf-v1` (56 overlapping files)
  - `cursor/cloud-full-activation-v1` vs `backup/mixed-cloud-ableton-before-split` (46 overlapping files)

## Feature Set Coverage by Branch
- full activation pipeline: `cursor/full-model-activation-pipeline-v1`, `cursor/activate-symbolic-backends-v1`, `cursor/actually-activate-moonbeam-hf-v1`
- cloud activation: `cursor/cloud-full-activation-v1`, `backup/mixed-cloud-ableton-before-split`
- Ableton agent bridge: `cursor/ableton-agent-bridge-v1`, `backup/mixed-cloud-ableton-before-split`
- ballad outputs: `cursor/activate-symbolic-backends-v1`, `cursor/actually-activate-moonbeam-hf-v1`, `cursor/ableton-agent-bridge-v1`
- symbolic backend activation: `cursor/activate-symbolic-backends-v1`, `cursor/actually-activate-moonbeam-hf-v1`, `cursor/symbolic-model-backend-adapters`
- Hugging Face/source discovery: `cursor/actually-activate-moonbeam-hf-v1`
- integration inventory: `cursor/actually-activate-moonbeam-hf-v1`
- source separation: `cursor/source-separation-witness-vertical-slice-v1`, `cursor/cloud-full-activation-v1`
- transcription witnesses: `cursor/transcription-witnesses-vertical-slice-v1`, `cursor/cloud-full-activation-v1`
- audio understanding: `cursor/audio-understanding-vertical-slice-v1`, `cursor/cloud-full-activation-v1`
- microtonal layer: none by branch name
- hum-to-MIDI live companion: none by branch name

## Truthful Readiness
- Scaffold-only features:
  - full activation pipeline execution remains dry-run
  - controlled ingestion runner remains dry-run shell
  - cloud execution remains policy/planning, not real execution
  - microtonal + hum-to-MIDI remain design-doc level
- Features producing real artifacts:
  - integration inventory reports
  - symbolic backend activation reports
  - symbolic ensemble reports + IR artifacts
  - ballad generation reports
  - privacy and model-integration availability reports
- Actually active models: none
- Blocked models:
  - `moonbeam`, `midigpt`, `musicbert`, `demucs`, `basic_pitch`, `yourmt3`, `essentia`: disabled in local config
  - `text2midi`: configured in local config but still unavailable
- Mass ingestion ready: `false`
- Controlled batch ready: `true`
- Model training ready: `false`
- Ableton integration (real vs scaffold): mixed but scaffold-heavy
- Cloud execution (real vs dry-run): dry-run only (`modal_called=false`, `execute_allowed=false`)

## Generated MIDI Status
- Present in current worktree: `false`
- Present in branch history/trees:
  - `outputs/ballad_2min_v2/*.mid`
  - `outputs/symbolic_ensemble_v1/selected_candidate.mid`
  - `outputs/symbolic_ensemble_v1/generated_candidates/*.mid`
  - `outputs/tangible_generation_v1/generated_*.mid`
  - `outputs/ableton_project_v1/AI_Generated_Song_Project/MIDI/*.mid`

## Validation Results
- `scripts/dev.cmd test`: pass (`371 passed, 3 warnings`)
- `scripts/dev.cmd check-privacy-leaks`: pass with historical debt (`new_public_leak_count=0`, `pre_existing_historical_path_debt_count=6`)
- `scripts/dev.cmd check-model-integrations`: pass (`configured_count=1`, `available_count=0`)
- Required direct greps:
  - `C:/Users/<user>`: none found
  - `C:\Users\<user>`: none found
  - `HF_TOKEN` in reports/docs/outputs/config: none found
  - `MODAL_TOKEN` in reports/docs/outputs/config: none found
  - `REPLICATE_API_TOKEN` in reports/docs/outputs/config: none found

## Top 5 Blockers
- Historical privacy debt remains non-zero (6 records).
- No model backend is currently available for real execution.
- Mass ingestion blocked by review burden and training-tokenization gates.
- Cloud execution has no real execution witness (dry-run only).
- Microtonal/hum-to-MIDI are not implemented as runnable branches.

## Next 5 Recommended Jobs
- Run safe historical scrub planning and reduce debt to zero.
- Execute one real controlled ingestion witness with explicit local manifest controls.
- Enable one symbolic backend in local config and produce one non-cloud smoke witness.
- Consolidate overlapping activation branches into one canonical branch.
- Convert microtonal/hum-to-MIDI designs into runnable, tested local scaffolds.
