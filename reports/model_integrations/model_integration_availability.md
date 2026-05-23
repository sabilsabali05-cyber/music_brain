# Model Integration Availability

- config_source: `config/model_integrations/model_integrations.example.json`
- configured_count: `0`
- available_count: `0`
- model_training_has_occurred: `False`

## Model Status
- `ableton_exporter` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`DAW export bridge for arrangement handoff.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `audiocraft` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Reference-only audio generation tooling family.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `basic_pitch` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Secondary witness transcription model for agreement checks.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `clap` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Audio-text retrieval embedding model.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `demucs` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Source separation backend for weak evidence stems.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `essentia` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Feature extraction baseline for timbre/rhythm descriptors.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `max_for_live_bridge` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Max for Live control bridge.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `mert` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Audio representation model for retrieval and context features.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `midigpt` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Controllable multitrack symbolic variation backend.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `moonbeam` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Primary symbolic composition and continuation backend.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `mulan_style` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Style-aware retrieval embedding model.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `muq` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Audio understanding encoder for semantic tagging.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `musicbert` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Symbolic representation, similarity, and ranking model.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `musicgen` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Reference-only audio generator for inspiration baselines.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `musicgen_stem` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Stem-oriented reference audio generation backend.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `puredata_plugdata_bridge` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Pure Data / PlugData integration bridge.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `synplant_patch_ranker` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Synplant patch ranking model for manual outcomes.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `synplant_seed_selector` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Synplant seed suggestion ranker under policy constraints.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `text2midi` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Prompt-to-sketch symbolic draft backend.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `texture_embedding_model` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`Texture embedding model for sound palette fit.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.
- `yourmt3` configured=`False` available=`False` reason=`disabled_by_default_no_local_config` role=`External witness transcription model.`
  - next_setup_step: Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and enable this model explicitly.

## Limitations
- No heavyweight dependencies are imported unless a backend is explicitly enabled in local config.
- No model downloads are triggered by this checker.
- Absence of optional models does not fail this checker.
