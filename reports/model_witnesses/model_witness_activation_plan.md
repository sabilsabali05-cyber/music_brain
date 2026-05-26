# Model Witness Activation Plan

- generated_from_audit: `reports/model_witnesses/model_witness_audit.json`
- all_witnesses_unavailable: `true`
- witnesses_total: `7`
- witnesses_unavailable: `7`
- policy: `no_auto_install_no_fake_smoke_pass`

## Per-witness actions

- `Moonbeam` (`moonbeam`): missing_config=`true` missing_dependencies=`false` local_only=`true` cloud_required=`false` weights_required=`true` next_action=`Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json, then set models.moonbeam.enabled=true.`
- `MusicBERT` (`musicbert`): missing_config=`true` missing_dependencies=`false` local_only=`true` cloud_required=`false` weights_required=`true` next_action=`Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json, then set models.musicbert.enabled=true.`
- `MIDI-GPT` (`midigpt`): missing_config=`true` missing_dependencies=`false` local_only=`true` cloud_required=`false` weights_required=`true` next_action=`Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json, then set models.midigpt.enabled=true.`
- `Text2MIDI` (`text2midi`): missing_config=`true` missing_dependencies=`false` local_only=`true` cloud_required=`false` weights_required=`true` next_action=`Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json, then set models.text2midi.enabled=true.`
- `Transcription witnesses` (`transcription_witnesses`): missing_config=`true` missing_dependencies=`true` local_only=`true` cloud_required=`false` weights_required=`true` next_action=`Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json and keep both witnesses disabled by default.`
- `Source separation witness` (`source_separation_witness`): missing_config=`true` missing_dependencies=`true` local_only=`true` cloud_required=`false` weights_required=`true` next_action=`Copy config/model_integrations/model_integrations.example.json to config/model_integrations/model_integrations.local.json, then set models.demucs.enabled=true only when explicit witness execution is intentionally enabled.`
- `Texture witness` (`texture_witness`): missing_config=`true` missing_dependencies=`true` local_only=`true` cloud_required=`false` weights_required=`true` next_action=`Configure a local texture witness backend and smoke-test it before use.`
