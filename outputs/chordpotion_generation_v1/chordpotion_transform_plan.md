# ChordPotion Transform Plan

- generation_id: `chordpotion_generation_v1`
- bpm: `100`
- midi_fx_role: `chord_pattern_generator`
- midi_fx_plugin_id: `chordpotion_midi_fx`
- chordpotion_configured: `true`
- chordpotion_available: `true`
- reaper_available: `true`
- instrument_vst_available: `true`
- transformed_midi_captured: `false`
- blocked: `false`
- blocked_reason: `none`

## Inputs/Outputs
- input_harmony_midi: `outputs/chordpotion_generation_v1/harmony_skeleton.mid`
- input_bass_midi: `outputs/chordpotion_generation_v1/bass.mid`
- input_lead_guide_midi: `outputs/chordpotion_generation_v1/lead_guide.mid`
- output_transformed_midi: `outputs/chordpotion_generation_v1/transformed_harmony.mid`

## Missing Config
- none

## Planner Notes
- Plan is local-only and does not assume plugin behavior unless verified available.
- If blocked=true, proceed with assisted DAW pack and manual plugin execution.
