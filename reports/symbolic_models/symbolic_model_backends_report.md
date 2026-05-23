# Symbolic Model Backend Availability

- stub_mode: `False`

## Providers
- `musicbert` (MusicBERT) role `evaluator_understanding_witness` capabilities `['symbolic_embedding', 'style_classification', 'similarity_scoring', 'reranking', 'accompaniment_suggestion', 'explanation']`
- `moonbeam` (Moonbeam) role `foundation_symbolic_generator` capabilities `['midi_continuation', 'midi_infill', 'symbolic_embedding', 'controllable_generation', 'explanation']`
- `midigpt` (MIDI-GPT) role `controllable_composer_backend` capabilities `['multitrack_generation', 'controllable_generation', 'midi_infill', 'midi_continuation', 'explanation']`
- `text2midi` (Text2MIDI) role `prompt_sketch_generator` capabilities `['text_to_midi', 'controllable_generation', 'explanation']`

## Availability
- `musicbert` available=`False` role_hint=`Use for symbolic understanding, embeddings, similarity, reranking, and evaluation.` installation_hint=`Install optional dependencies (e.g. torch + transformers) and set MUSICBERT_MODEL_PATH.` limitations=`['MusicBERT model weights are not bundled with this repository.', 'This adapter intentionally avoids heavyweight runtime imports at module load time.', 'Generation is disabled because MusicBERT is treated as an evaluator/understanding witness.']`
- `moonbeam` available=`False` role_hint=`Use for MIDI continuation/infill and conditional symbolic generation.` installation_hint=`Install Moonbeam runtime and set MOONBEAM_MODEL_PATH.` limitations=`['Moonbeam weights/runtime are optional and not included in this repository.', 'Adapter currently performs capability/availability reporting only.', 'No model inference is executed when backend is unavailable.']`
- `midigpt` available=`False` role_hint=`Use for controllable multitrack symbolic composition and infill.` installation_hint=`Install MIDI-GPT runtime and set MIDIGPT_MODEL_PATH.` limitations=`['MIDI-GPT weights/runtime are optional and not included in this repository.', 'Adapter currently performs capability/availability reporting only.', 'No model inference is executed when backend is unavailable.']`
- `text2midi` available=`False` role_hint=`Use for text prompt to symbolic sketch generation.` installation_hint=`Install Text2MIDI runtime and set TEXT2MIDI_MODEL_PATH.` limitations=`['Text2MIDI weights/runtime are optional and not included in this repository.', 'Adapter currently performs capability/availability reporting only.', 'No model inference is executed when backend is unavailable.']`
