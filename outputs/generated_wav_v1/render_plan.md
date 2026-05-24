# Local Render Plan

- generation_id: `generated_wav_v1`
- default_render_backend: `dry_run_plan_only`

## Stem Assignments
- `bass` role=`bass` plugin=`none` preset=`none` backend=`dry_run_plan_only` uncertainty=`high`
- `drums` role=`drums` plugin=`none` preset=`none` backend=`dry_run_plan_only` uncertainty=`high`
- `lead` role=`lead` plugin=`none` preset=`none` backend=`dry_run_plan_only` uncertainty=`high`
- `pad` role=`pad` plugin=`none` preset=`none` backend=`dry_run_plan_only` uncertainty=`high`

## Planner Notes
- Plan generated from local MIDI stems only.
- No cloud render calls or model training were used.
- If VST config is missing, backend should remain dry_run_plan_only.
