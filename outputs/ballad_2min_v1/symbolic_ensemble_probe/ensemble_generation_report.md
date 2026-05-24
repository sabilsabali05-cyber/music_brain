# Symbolic Ensemble Generation Report

- prompt_text: `Emotional dark melodic minor ballad, sparse drums, vocal space, 2-minute structure.`
- selected_candidate_backend: `example_retrieval`
- example_retrieval_fallback: `True`
- no_real_symbolic_backend_available: `True`
- not_model_trained_on_user_data: `True`

## Backend Steps
- `text2midi` status=`unavailable` reason=`text2midi_prompt_sketch_not_wired_no_fake_generation`
- `moonbeam` status=`unavailable` reason=`disabled_or_missing_local_config`
- `midigpt` status=`unavailable` reason=`midigpt_multitrack_infill_not_wired`
- `example_retrieval` status=`ok` reason=`fallback_candidate_generated`

## Selected Output
- MIDI: `outputs/ballad_2min_v1/symbolic_ensemble_probe/selected_candidate.mid`
- IR: `outputs/ballad_2min_v1/symbolic_ensemble_probe/selected_candidate_ir.json`
