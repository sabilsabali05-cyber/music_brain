# Sound Selection Training Data Plan

## Objective

Build training-ready supervision for sound/texture decisions that map composition context to practical seed selection, Synplant candidate ranking, and Ableton routing outcomes.

## Future Training Tasks

1. `role_to_sample_seed_retrieval`
   - Predict which local sample seeds best match a composition role and texture request.
2. `sample_seed_to_synplant_success_prediction`
   - Predict which seeds are likely to yield high-quality Synplant candidates.
3. `synplant_candidate_ranking`
   - Rank generated Synplant patch candidates using role and mix-fit criteria.
4. `midi_part_to_texture_request`
   - Infer texture requests from MIDI part behavior and arrangement context.
5. `composition_context_to_sound_palette`
   - Recommend cohesive sound palettes across roles for a full composition.
6. `max_for_live_macro_control_prediction`
   - Predict macro/routing controls for selected patches in Max for Live.

## What The Serious Model Should Learn

- What sound seed to choose for each role.
- Why a seed fits the role (feature profile + context evidence).
- Which Synplant candidate to pick from session outputs.
- How to route/control selected patches inside Ableton and Max for Live.
- How texture choices affect composition-level coherence and mix fit.

## Required Data Signals

- Sample seed metadata and feature profiles.
- Synplant session logs (including manual sessions).
- Candidate patch outputs and ranking outcomes.
- Selection reasons and human/model feedback.
- Arrangement role context and rendered usage references.
- Routing and macro control plans used in production sessions.

## Scope Note

This document is planning-only. It does not start model training, Synplant automation, or audio processing workflows.
