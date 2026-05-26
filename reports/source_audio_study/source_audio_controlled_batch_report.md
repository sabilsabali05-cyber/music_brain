# Source Audio Controlled Batch Report

- max_items_for_controlled_batch: `25`
- controlled_batch_size: `25`
- analysis_allowed_count: `25`

## Policy notes
- Controlled batch prioritizes analysis-allowed rows first.
- Batch is capped by local max_items_for_controlled_batch.
- No raw absolute paths are written to committed outputs.
