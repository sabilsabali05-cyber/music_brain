# Automated Local WAV Rendering

This workflow provides a local, honest MIDI-to-WAV rendering pipeline for local VST workflows.

## Guarantees

- No cloud calls.
- No model training.
- No model downloads.
- No fake render claims.
- No private VST paths in public reports.
- No automatic edits to real Ableton projects.

## Render Modes

- `reaper_auto_render` (preferred): uses local Reaper + local VST registry when configured.
- `ableton_assisted_render` (assisted/future automation): produces a render-ready pack for manual Ableton rendering.
- `preview_synth_render` (fallback only): non-real-VST preview synthesis path, explicitly marked as fallback.
- `dry_run_plan_only` (default): plan/report only when local config is missing or incomplete.

## Honesty Fields

- `wav_rendered=true` only when a verified WAV file exists and passes basic checks.
- `vst_render_used=true` only when configured local VST usage is confirmed.
- `fallback_preview_used=true` only when fallback synth preview path is used.
- `render_plan_only=true` when no render happened.

## One Command Flow

Run:

```powershell
scripts\dev.cmd generate-and-render-wav
```

Outputs:

- Always: `outputs/generated_wav_v1/` with `full.mid`, `stems/`, plans/reports, and `wav_status.md`
- If rendered: `renders/generated_wav_v1/final.wav` and optional stem WAVs
- If not rendered: `outputs/render_ready_packs/generated_wav_v1/` assisted pack

`wav_status.md` is always one of:

- `rendered_wav_available`
- `render_backend_missing`
- `vst_config_missing`
- `render_failed`
- `assisted_render_pack_created`

## Reaper Backend Notes

If complete CLI automation is unavailable, the backend emits:

- `render_backend_status=planned_not_executed`
- actionable project-plan artifacts
- `wav_rendered=false` unless WAV verification succeeds

This ensures no false claims.
