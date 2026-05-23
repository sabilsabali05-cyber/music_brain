# Symbolic Generation Plan

- dataset_folder: `C:/Users/izzyo/ai-composer/music_brain/datasets/generative_training/20260521T204653698972_Kanye_West_performs_Ghost_Town_with_070_33667a7b59/20260521T204750163461_audio_structure_v1`
- requested_task: `continuation`
- prompt: ``
- example_count_for_task: `10`
- provider_fallback_order: `['example_retrieval', 'moonbeam', 'musicbert']`

## Provider Plan
- `example_retrieval` available=`True` generation_allowed=`True` limitations=`[]`
- `moonbeam` available=`False` generation_allowed=`False` limitations=`['Moonbeam weights/runtime are optional and not included in this repository.', 'Adapter currently performs capability/availability reporting only.', 'No model inference is executed when backend is unavailable.']`
- `musicbert` available=`False` generation_allowed=`False` limitations=`['MusicBERT model weights are not bundled with this repository.', 'This adapter intentionally avoids heavyweight runtime imports at module load time.', 'Generation is disabled because MusicBERT is treated as an evaluator/understanding witness.']`

## Fallback Policy
- existing example generator
- Moonbeam for continuation/infill
- MIDI-GPT for multitrack/controls
- Text2MIDI for prompt-only
- MusicBERT for ranking/evaluation
