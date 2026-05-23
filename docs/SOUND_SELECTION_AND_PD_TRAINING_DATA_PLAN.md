# Sound Selection And Pure Data Training Data Plan

## Future Training Tasks

- `role_to_sample_seed_retrieval`
- `sample_seed_to_synplant_success_prediction`
- `synplant_candidate_ranking`
- `midi_part_to_texture_request`
- `composition_context_to_sound_palette`
- `composition_context_to_pd_patch_type`
- `pd_template_parameter_prediction`
- `pd_patch_candidate_ranking`
- `max_for_live_macro_control_prediction`
- `rendered_stem_feedback_prediction`

## Staged Development Path

1. **Manual logging**
   - Human picks sample seeds, Synplant outputs, and Pure Data templates.
   - Ratings and notes are captured consistently.
2. **Template-based Pd generation/control**
   - Pure Data templates are reused with controlled parameter mappings.
   - Ableton/Max routing references are logged per track role.
3. **Generated Pd patch candidates**
   - Candidate Pure Data systems are proposed from templates and context.
   - Candidate summaries include object graph/control mapping metadata.
4. **Model-ranked patch systems**
   - Model ranks Synplant and Pure Data candidates for role fit/mix fit.
   - Human override remains available for safety and quality.
5. **Ableton/Max rendered feedback loop**
   - Rendered stems and macro/routing outcomes become supervision signals.
   - Model learns from end-result quality, not just intermediate choices.

## What The Serious Model Should Learn

- Which local sample seed best fits each role and context.
- Which Synplant candidate patch should be selected from seed-derived options.
- Which Pure Data patch type/template best serves each section and role.
- How to set or predict parameter/control mappings for Pure Data and Max for Live.
- How routing and control decisions affect rendered stem quality and composition coherence.
