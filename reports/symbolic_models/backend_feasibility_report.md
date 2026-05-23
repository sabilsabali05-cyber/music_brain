# Symbolic Backend Feasibility Report

- generated_at_utc: `2026-05-23T04:19:53.248360+00:00`
- recommended_first_backend: `moonbeam`
- confidence: `medium`

## Recommendation
- reason: Most aligned with continuation/infill goals and has explicit public code + pretrained checkpoint documentation for symbolic generation.

## Backend Findings

### Moonbeam (`moonbeam`)
- expected_input_format: Tokenized symbolic sequences using Moonbeam's custom absolute+relative attribute tokenizer and checkpoint/tokenizer files.
- expected_output_format: Generated symbolic token sequences decoded back to MIDI (continuation, conditional generation, and infilling workflows).
- public_code_installable: `yes`
- pretrained_weights_required: `yes`
- license_usage_status: `clear`
- midi_tokenization_compatibility: `partially_compatible`
- estimated_integration_difficulty: `high`
- usable_with_current_repo_state: `False`
- evidence:
  - [Moonbeam GitHub repository](https://github.com/guozixunnicolas/moonbeam-midi-foundation-model) - Repository includes dependency installation instructions and checkpoint download instructions.
  - [Moonbeam project page](https://aim-qmul.github.io/moonbeam-midi-foundation-model/) - States paper/code/pretrained weights release and Apache License 2.0 status.
  - [Moonbeam paper](https://arxiv.org/html/2505.15559) - Describes custom tokenization and downstream continuation/infilling tasks.

### MIDI-GPT (`midigpt`)
- expected_input_format: MIDI-GPT event/token representation for multitrack bar/track infilling with attribute controls.
- expected_output_format: Multitrack MIDI generation/infill outputs from model checkpoint and tokenizer config.
- public_code_installable: `yes`
- pretrained_weights_required: `yes`
- license_usage_status: `unknown`
- midi_tokenization_compatibility: `partially_compatible`
- estimated_integration_difficulty: `high`
- usable_with_current_repo_state: `False`
- evidence:
  - [MIDI-GPT GitHub repository](https://github.com/Metacreation-Lab/MIDI-GPT) - Describes controllable multitrack generation/infill and bundled model checkpoints in repository artifacts.
  - [MIDI-GPT AAAI paper](https://ojs.aaai.org/index.php/AAAI/article/view/32138) - Explains controllable multitrack architecture and infill tasks.
  - [MIDI-GPT Python package](https://pypi.org/project/midigpt/) - Shows packaged tokenizer/model runtime and checkpoint format expectations.
- unknowns: `{"license_usage_status": "unknown"}`

### Text2MIDI (`text2midi`)
- expected_input_format: Natural-language prompt with T5 encoder and REMI-based decoder vocabulary/config.
- expected_output_format: Generated symbolic token sequence decoded to MIDI conditioned on text prompt.
- public_code_installable: `yes`
- pretrained_weights_required: `yes`
- license_usage_status: `unknown`
- midi_tokenization_compatibility: `partially_compatible`
- estimated_integration_difficulty: `medium`
- usable_with_current_repo_state: `False`
- evidence:
  - [Text2MIDI GitHub repository](https://github.com/AMAAI-Lab/Text2midi) - Provides code and loading instructions tied to HuggingFace-hosted weights and REMI vocab.
  - [Text2MIDI HuggingFace model card](https://huggingface.co/amaai-lab/text2midi) - Documents pretrained weight files and runtime loading process.
- unknowns: `{"license_usage_status": "unknown"}`

### MusicBERT (`musicbert`)
- expected_input_format: OctupleMIDI symbolic encoding for music understanding tasks using fairseq-style checkpoints.
- expected_output_format: Embeddings, classification/similarity/reranking signals; not primarily a MIDI generator backend.
- public_code_installable: `yes`
- pretrained_weights_required: `yes`
- license_usage_status: `unknown`
- midi_tokenization_compatibility: `incompatible`
- estimated_integration_difficulty: `high`
- usable_with_current_repo_state: `False`
- evidence:
  - [MusicBERT README](https://github.com/microsoft/muzic/blob/main/musicbert/README.md) - Describes symbolic understanding scope, OctupleMIDI encoding, and checkpoint requirements.
  - [Muzic project page](https://microsoft.github.io/muzic/musicbert/) - Confirms understanding/evaluation orientation and pretrained checkpoint usage.
- unknowns: `{"license_usage_status": "unknown"}`
