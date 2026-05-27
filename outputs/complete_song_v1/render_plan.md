# Local Render Plan

- generation_id: `complete_song_v1`
- default_render_backend: `reaper_auto_render`

## Stem Assignments
- `bass` role=`bass` plugin=`omnisphere_vst3` preset=`Default` backend=`reaper_auto_render` uncertainty=`medium`
- `chords` role=`texture` plugin=`chordpotion_midi_fx` preset=`Default` backend=`reaper_auto_render` uncertainty=`medium`
- `drums_optional` role=`drums` plugin=`chordpotion_midi_fx` preset=`Default` backend=`reaper_auto_render` uncertainty=`medium`
- `lead` role=`lead` plugin=`omnisphere_vst3` preset=`Default` backend=`reaper_auto_render` uncertainty=`medium`
- `skeleton` role=`texture` plugin=`chordpotion_midi_fx` preset=`Default` backend=`reaper_auto_render` uncertainty=`medium`
- `texture` role=`texture` plugin=`chordpotion_midi_fx` preset=`Default` backend=`reaper_auto_render` uncertainty=`medium`

## Planner Notes
- Plan generated from local MIDI stems only.
- No cloud render calls or model training were used.
- If VST config is missing, backend should remain dry_run_plan_only.
- Composition/taste/understanding pipeline remains independent from Synplant render assignment.
