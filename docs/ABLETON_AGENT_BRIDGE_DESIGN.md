# Ableton Agent Bridge Design (Scaffold v1)

## Purpose

This scaffold defines a safe bridge between LLM-generated musical intent and structured Ableton command plans.
It only supports validation, preview, and human review gates.
It does **not** control Ableton, mutate a Live Set, process audio, run GUI automation, or train models.

## Core Flow

1. Read intent and mock project state.
2. Build proposed arrangement-aware command plan.
3. Validate commands against schema and policy constraints.
4. Produce dry-run report for human approval.
5. Keep all real execution future-gated.

## Command Surface (Future-Planned)

- `create_track`
- `create_midi_clip`
- `replace_midi_clip`
- `duplicate_clip`
- `move_clip`
- `split_section`
- `create_scene`
- `rename_track`
- `group_tracks`
- `set_track_volume`
- `set_track_pan`
- `automate_device_parameter`
- `automate_mixer_parameter`
- `add_device_placeholder`
- `route_track_placeholder`
- `create_return_send_automation`
- `insert_generated_bridge`
- `insert_generated_variation`
- `thin_arrangement`
- `build_transition`
- `export_review_package`

## Safety Rules Enforced

- Dry-run by default.
- No real Ableton mutation.
- No GUI automation.
- No private paths in reports.
- Every command must be schema-validatable.
- Every destructive change requires `human_review_required=true`.
- Generated clip insertion requires provenance metadata.
- Model outputs are marked `generated_candidate`, never final.
- Source-separated/transcribed evidence is `witness_not_truth`.
- Real Live Set writes remain future-gated.

## Output Expectations

The dry-run report includes:

- interpreted musical intent
- proposed arrangement changes
- proposed generated candidates needed
- proposed Ableton commands
- risk warnings
- human review checklist
- explicit flags proving no real execution occurred
