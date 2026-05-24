# ChordPotion Transform Plan

- generation_id: `chordpotion_generation_v1`
- bpm: `100`
- midi_fx_role: `chord_pattern_generator`
- midi_fx_plugin_id: `none`
- chordpotion_configured: `false`
- chordpotion_available: `false`
- reaper_available: `false`
- instrument_vst_available: `false`
- transformed_midi_captured: `false`
- blocked: `true`
- blocked_reason: `local_requirements_missing`

## Inputs/Outputs
- input_harmony_midi: `outputs/chordpotion_generation_v1/harmony_skeleton.mid`
- input_bass_midi: `outputs/chordpotion_generation_v1/bass.mid`
- input_lead_guide_midi: `outputs/chordpotion_generation_v1/lead_guide.mid`
- output_transformed_midi: `outputs/chordpotion_generation_v1/transformed_harmony.mid`

## Missing Config
- preferred_chordpotion_plugin_id
- chordpotion_plugin_unavailable
- reaper_executable_path
- instrument_vst_unavailable

## Planner Notes
- Plan is local-only and does not assume plugin behavior unless verified available.
- If blocked=true, proceed with assisted DAW pack and manual plugin execution.
