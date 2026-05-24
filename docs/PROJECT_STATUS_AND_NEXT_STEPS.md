# Project Status And Next Steps

## Current Status

- Active integration branch: `cursor/integrate-loose-threads-complete-pipeline-v1`.
- One-command local orchestrator is now wired: `scripts/dev.cmd generate-complete-song-wav`.
- Complete command emits truthful status outputs and review artifacts (no fake WAV/chordpotion/training claims).
- Cloud calls remain intentionally out of scope for this pass.

## What Works

- Deterministic local stem generation (skeleton, bass, lead, optional drums).
- Optional chordpotion path with explicit `missing_config` fallback behavior.
- VST render-plan generation and local render attempt gate.
- Assisted pack fallback path when verified WAV is unavailable.
- Integration reports for loose-thread inventory, decisions, blockers, and privacy debt.

## What Is Blocked / Experimental

- Reaper automation remains partially scaffolded (`planned_not_executed` in many runs).
- ChordPotion transformed MIDI capture is not guaranteed by automation.
- Selector training is blocked unless explicit labeled outcomes exist.
- Privacy scan currently reports failures that must be resolved before merge.

## Immediate Next Steps

- Fix current `check-privacy-leaks` failures and re-run strict privacy gate.
- Keep local config files private and untracked; only commit redacted/boolean reports.
- Verify complete command output in local environment and confirm `wav_status` is honest.
- If WAV is not rendered, use assisted pack workflow and capture manual review feedback.
- Merge only after tests and privacy checks pass with no new regressions.
