# Complete Pipeline Usage

## One-Command Run

Run:

`scripts/dev.cmd generate-complete-song-wav`

This command executes a local-only integration pipeline that:

1. Loads local config if present.
2. Loads available corpus/theory/texture profile context.
3. Builds generation intent.
4. Generates skeleton + bass + lead + optional stems.
5. Runs optional chordpotion intent/selection/audition/transform/score flow when configured.
6. Falls back to direct stems path with `chordpotion_status=missing_config` when unavailable.
7. Builds VST render plan.
8. Attempts local render if Reaper/VST is configured.
9. Creates assisted pack when render is unavailable/unverified.
10. Writes pipeline status artifacts and review/feedback artifacts.

## Output Paths

- `outputs/complete_song_v1/wav_status.md`
- `reports/integration/complete_song_pipeline_status.md`
- `reports/integration/complete_song_pipeline_status.json`
- `outputs/complete_song_v1/review_sheet.md`
- `reports/review_queue/complete_song_v1_feedback_template.json`

## Truth / Safety Rules

- Final WAV is only claimed when verified as real audio.
- ChordPotion is only claimed as attempted when configured and actually invoked.
- `transformed_midi_captured=true` only when file exists and parses.
- `trained_selector_used=true` only when local artifact and report both confirm trained mode.
- No cloud calls, no fake rendering claims, no fake model usage claims.

## Local Config Steps

- Keep local config in `*.local.json` only.
- Configure Reaper and local VST registry privately.
- Do not commit private local paths.

## Review Loop

- Use `outputs/complete_song_v1/review_sheet.md` for manual quality checks.
- Fill `reports/review_queue/complete_song_v1_feedback_template.json` after listening/review.
- Re-run command after adjustments and compare status artifacts.

## Non-Real / Experimental Parts

- Reaper CLI automation may remain plan-only in some environments.
- ChordPotion transformed MIDI capture may remain unavailable without manual/local setup.
- Training is not part of the complete pipeline command unless explicitly run with valid labels.
