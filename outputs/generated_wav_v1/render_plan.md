# Local Render Plan

- generation_id: `generated_wav_v1`
- default_render_backend: `dry_run_plan_only`

## Stem Assignments
- `bass` role=`bass` plugin=`omnisphere_vst3` preset=`Default` backend=`dry_run_plan_only` uncertainty=`medium`
- `drums` role=`drums` plugin=`chordpotion_midi_fx` preset=`Default` backend=`dry_run_plan_only` uncertainty=`medium`
- `lead` role=`lead` plugin=`omnisphere_vst3` preset=`Default` backend=`dry_run_plan_only` uncertainty=`medium`
- `pad` role=`pad` plugin=`omnisphere_vst3` preset=`Default` backend=`dry_run_plan_only` uncertainty=`medium`

## Planner Notes
- Plan generated from local MIDI stems only.
- No cloud render calls or model training were used.
- If VST config is missing, backend should remain dry_run_plan_only.
