# Symbolic Backend Install Plan

- automatic_clone_performed: `False`
- automatic_download_performed: `False`
- automatic_install_performed: `False`
- cloud_called: `False`
- modal_called: `False`
- model_training_has_occurred: `False`

## Manual Steps
- `text2midi`
  - Clone repository manually into a local-only model repository folder (do not commit repo).
  - Place model/tokenizer weights manually in local-only weight/cache folders (do not commit weights).
  - Set config/model_integrations/model_integrations.local.json values.
  - Run scripts/dev.cmd run-text2midi-smoke-test for real local probe.
- `moonbeam`
  - Clone repository manually into a local-only model repository folder (do not commit repo).
  - Place model/tokenizer weights manually in local-only weight/cache folders (do not commit weights).
  - Set config/model_integrations/model_integrations.local.json values.
  - Run scripts/dev.cmd run-moonbeam-smoke-test for real local probe.
- `midigpt`
  - Clone repository manually into a local-only model repository folder (do not commit repo).
  - Place model/tokenizer weights manually in local-only weight/cache folders (do not commit weights).
  - Set config/model_integrations/model_integrations.local.json values.
  - Run scripts/dev.cmd run-midigpt-smoke-test for real local probe.
- `musicbert`
  - Clone repository manually into a local-only model repository folder (do not commit repo).
  - Place model/tokenizer weights manually in local-only weight/cache folders (do not commit weights).
  - Set config/model_integrations/model_integrations.local.json values.
  - Run scripts/dev.cmd run-musicbert-smoke-test for real local probe.
