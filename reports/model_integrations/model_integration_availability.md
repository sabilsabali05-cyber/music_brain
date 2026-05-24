# Model Integration Availability

- config_source: `config/model_integrations/model_integrations.local.json`
- configured_count: `0`
- available_count: `0`
- model_training_has_occurred: `False`

## Model Status
- `ableton_exporter` configured=`False` available=`False` reason=`disabled_in_local_config` role=`DAW export bridge for arrangement handoff.`
  - next_setup_step: Set models.ableton_exporter.enabled=true in local config after policy review.
- `audiocraft` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Reference-only audio generation tooling family.`
  - next_setup_step: Set models.audiocraft.enabled=true in local config after policy review.
- `basic_pitch` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Secondary witness transcription model for agreement checks.`
  - next_setup_step: Set models.basic_pitch.enabled=true in local config after policy review.
- `clap` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Audio-text retrieval embedding model.`
  - next_setup_step: Set models.clap.enabled=true in local config after policy review.
- `demucs` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Source separation backend for weak evidence stems.`
  - next_setup_step: Set models.demucs.enabled=true in local config after policy review.
- `essentia` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Feature extraction baseline for timbre/rhythm descriptors.`
  - next_setup_step: Set models.essentia.enabled=true in local config after policy review.
- `max_for_live_bridge` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Max for Live control bridge.`
  - next_setup_step: Set models.max_for_live_bridge.enabled=true in local config after policy review.
- `mert` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Audio representation model for retrieval and context features.`
  - next_setup_step: Set models.mert.enabled=true in local config after policy review.
- `midigpt` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Controllable multitrack symbolic variation backend.`
  - next_setup_step: Set models.midigpt.enabled=true in local config after policy review.
- `moonbeam` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Primary symbolic composition and continuation backend.`
  - next_setup_step: Set models.moonbeam.enabled=true in local config after policy review.
- `mulan_style` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Style-aware retrieval embedding model.`
  - next_setup_step: Set models.mulan_style.enabled=true in local config after policy review.
- `muq` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Audio understanding encoder for semantic tagging.`
  - next_setup_step: Set models.muq.enabled=true in local config after policy review.
- `musicbert` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Symbolic representation, similarity, and ranking model.`
  - next_setup_step: Set models.musicbert.enabled=true in local config after policy review.
- `musicgen` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Reference-only audio generator for inspiration baselines.`
  - next_setup_step: Set models.musicgen.enabled=true in local config after policy review.
- `musicgen_stem` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Stem-oriented reference audio generation backend.`
  - next_setup_step: Set models.musicgen_stem.enabled=true in local config after policy review.
- `puredata_plugdata_bridge` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Pure Data / PlugData integration bridge.`
  - next_setup_step: Set models.puredata_plugdata_bridge.enabled=true in local config after policy review.
- `synplant_patch_ranker` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Synplant patch ranking model for manual outcomes.`
  - next_setup_step: Set models.synplant_patch_ranker.enabled=true in local config after policy review.
- `synplant_seed_selector` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Synplant seed suggestion ranker under policy constraints.`
  - next_setup_step: Set models.synplant_seed_selector.enabled=true in local config after policy review.
- `text2midi` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Prompt-to-sketch symbolic draft backend.`
  - next_setup_step: Set models.text2midi.enabled=true in local config after policy review.
- `texture_embedding_model` configured=`False` available=`False` reason=`disabled_in_local_config` role=`Texture embedding model for sound palette fit.`
  - next_setup_step: Set models.texture_embedding_model.enabled=true in local config after policy review.
- `yourmt3` configured=`False` available=`False` reason=`disabled_in_local_config` role=`External witness transcription model.`
  - next_setup_step: Set models.yourmt3.enabled=true in local config after policy review.

## Limitations
- No heavyweight dependencies are imported unless a backend is explicitly enabled in local config.
- No model downloads are triggered by this checker.
- Absence of optional models does not fail this checker.
