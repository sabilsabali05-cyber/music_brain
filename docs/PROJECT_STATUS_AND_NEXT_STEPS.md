# Project Status And Next Steps

## Current Status

- Canonical active branch: `cursor/consolidate-synplant-and-beatbattle-v1`.
- Superseded branch: `cursor/music-understanding-taste-loop-v1`.
- Integrated branches: `cursor/synplant-local-render-target-v1`, `cursor/beat-battle-ranked-site-automation-v1`.
- Retired/superseded branch: `cursor/chordpotion-intelligent-preset-selector-v1` (fully contained in canonical branch line; no unique commits/files).
- Primary commands for canonical branch:
  - `scripts\dev.cmd test`
  - `scripts\dev.cmd run-music-understanding-loop`
  - `scripts\dev.cmd generate-complete-song-wav`
  - `scripts\dev.cmd create-reaper-project-from-selected-candidate`
  - `scripts\dev.cmd beat-battle-ranked-site-auto`
  - `scripts\dev.cmd check-privacy-leaks`

## What Works

- Deterministic local stem generation (skeleton, bass, lead, optional drums).
- Synplant assignment path wired as local render target only; no composer-role claim.
- Beat Battle automation path wired and safety-gated by local config; no fake submission/result path.
- Assisted pack fallback path remains available when verified WAV is unavailable.
- Integration reports for loose-thread inventory, decisions, blockers, and privacy debt.

## What Is Blocked / Experimental

- Reaper automation remains partially scaffolded (`planned_not_executed` in many runs).
- `scripts\dev.cmd create-reaper-project-from-selected-candidate` is currently unavailable in `scripts/dev.ps1` task map.
- Beat Battle site automation is blocked by missing `config/beat_battle_ranked_site.local.json`.
- Privacy scan currently reports failures that must be resolved before merge.

## Immediate Next Steps

- Keep local config/session/audio folders private and ignored (`browser_state/`, `playwright_state/`, `site_sessions/`, `beat_battle_round_audio/`, `renders/`).
- Add/verify `config/beat_battle_ranked_site.local.json` locally before rerunning Beat Battle auto flow.
- Review `candidate_01.mid` through `candidate_08.mid` and append labeled taste feedback.
- Reach 20+ labeled feedback examples to enable trained composition taste ranker mode.
- Resolve new privacy leaks in taste feedback reports and track historical debt separately.
