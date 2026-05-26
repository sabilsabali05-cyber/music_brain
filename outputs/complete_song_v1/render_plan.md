# Local Render Plan

- generation_id: `complete_song_v1`
- default_render_backend: `reaper_auto_render`

## Stem Assignments
- `bass` role=`bass` plugin=`none` preset=`none` backend=`reaper_auto_render` uncertainty=`high`
- `chords` role=`texture` plugin=`none` preset=`none` backend=`reaper_auto_render` uncertainty=`high`
- `drums_optional` role=`drums` plugin=`none` preset=`none` backend=`reaper_auto_render` uncertainty=`high`
- `lead` role=`lead` plugin=`none` preset=`none` backend=`reaper_auto_render` uncertainty=`high`
- `skeleton` role=`texture` plugin=`none` preset=`none` backend=`reaper_auto_render` uncertainty=`high`
- `texture` role=`texture` plugin=`none` preset=`none` backend=`reaper_auto_render` uncertainty=`high`

## Planner Notes
- Plan generated from local MIDI stems only.
- No cloud render calls or model training were used.
- If VST config is missing, backend should remain dry_run_plan_only.
- Composition/taste/understanding pipeline remains independent from Synplant render assignment.
