# Local VST Render Backends

This document describes local render backends and registry behavior.

## VST Registry

Public template:

- `config/local_vst_registry.example.json`

Local private config (ignored):

- `config/local_vst_registry.local.json`

Required plugin schema fields:

- `plugin_id`, `display_name`, `vendor`, `format`, `category`
- `local_path` (local-only), `local_path_redacted` (public-safe)
- `available`, `verified_loadable`, `preset_names`, `texture_tags`, `roles`, `notes`

Rules:

- Keep real `local_path` only in ignored local config.
- Public reports expose only `local_path_redacted`.
- Never assume plugin availability unless local config or scanner confirms it.

## Backend Behavior

### `reaper_auto_render`

- Preferred backend for automated local VST rendering.
- Requires configured Reaper executable path and VST registry.
- Missing config safe-fails with explicit report fields.
- If automation is not fully available, emits actionable plan and `planned_not_executed`.

### `ableton_assisted_render`

- Creates a render-ready pack for manual review/render.
- Does not claim WAV rendering.
- Includes stem MIDI copies, plan docs, and review checklist.

### `preview_synth_render`

- Fallback-only mode.
- Must be explicitly marked non-real-VST.
- `fallback_preview_used=true` only when this mode is used.

### `dry_run_plan_only`

- Default mode when local config is absent.
- Builds render plans and reports only.
- Never claims rendered WAV outputs.
