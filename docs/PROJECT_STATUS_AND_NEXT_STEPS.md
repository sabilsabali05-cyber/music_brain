# Project Status And Next Steps

## Current Status

- Canonical active branch: `cursor/music-understanding-taste-loop-v1`.
- Retired/superseded branch: `cursor/chordpotion-intelligent-preset-selector-v1` (fully contained in canonical branch; no unique commits/files).
- Primary command for active loop: `scripts/dev.cmd run-music-understanding-loop`.
- Current review focus: `outputs/music_understanding_loop_v1/candidates/candidate_01.mid` through `candidate_08.mid`.
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

- Run `scripts/dev.cmd test` and `scripts/dev.cmd run-music-understanding-loop` on `cursor/music-understanding-taste-loop-v1`.
- Review `candidate_01.mid` through `candidate_08.mid` and append labeled taste feedback.
- Reach 20+ labeled feedback examples to enable trained composition taste ranker mode.
- Keep local config files private and untracked; only commit redacted/boolean reports.
- Re-run `scripts/dev.cmd check-privacy-leaks` and address any failing findings.
