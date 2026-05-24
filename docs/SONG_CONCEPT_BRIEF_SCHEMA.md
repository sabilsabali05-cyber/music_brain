# SongConceptBrief Schema

`SongConceptBrief` lives in `features/concept_to_composition/concept_schema.py`.

Required fields:

- `title`
- `short_description`
- `emotional_core`
- `narrative_arc`
- `perspective`
- `scene_or_image`
- `energy_curve`
- `tension_curve`
- `density_curve`
- `tempo_range`
- `key_or_mode_preference`
- `harmony_strategy`
- `chord_movement_strategy`
- `bass_strategy`
- `melody_strategy`
- `rhythm_strategy`
- `texture_strategy`
- `arrangement_strategy`
- `section_plan`
- `motifs_to_try`
- `avoid_patterns`
- `preserve_patterns`
- `weirdness_policy`
- `vocal_space_policy`
- `reference_influence_policy`
- `generation_seed`
- `confidence`
- `unresolved_questions`

Notes:

- Curves are normalized lists (0.0-1.0) describing macro-shape targets.
- `tempo_range` stores `min_bpm` and `max_bpm`.
- `section_plan` captures named sections, bar lengths, and intent.
- Policies are declarative and feed deterministic generation controls.
