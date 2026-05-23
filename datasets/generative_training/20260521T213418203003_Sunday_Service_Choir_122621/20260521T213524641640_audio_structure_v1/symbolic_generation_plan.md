# Symbolic Generation Plan

- dataset_folder: `<PRIVATE_LOCAL_PATH>/ai-composer/music_brain/datasets/generative_training/20260521T213418203003_Sunday_Service_Choir_122621/20260521T213524641640_audio_structure_v1`
- requested_task: `call_response`
- prompt: ``
- example_count_for_task: `45`
- provider_fallback_order: `['example_retrieval', 'midigpt', 'musicbert']`

## Provider Plan
- `example_retrieval` available=`True` generation_allowed=`True` limitations=`[]`
- `midigpt` available=`False` generation_allowed=`False` limitations=`['MIDI-GPT weights/runtime are optional and not included in this repository.', 'Adapter currently performs capability/availability reporting only.', 'No model inference is executed when backend is unavailable.']`
- `musicbert` available=`False` generation_allowed=`False` limitations=`['MusicBERT model weights are not bundled with this repository.', 'This adapter intentionally avoids heavyweight runtime imports at module load time.', 'Generation is disabled because MusicBERT is treated as an evaluator/understanding witness.']`

## Fallback Policy
- existing example generator
- Moonbeam for continuation/infill
- MIDI-GPT for multitrack/controls
- Text2MIDI for prompt-only
- MusicBERT for ranking/evaluation
