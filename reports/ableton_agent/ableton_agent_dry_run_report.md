# Ableton Agent Dry Run Report

- status: `dry_run_completed`
- ableton_connected: `False`
- live_set_modified: `False`
- commands_generated: `True`
- commands_executed: `False`
- human_review_required: `True`
- model_generation_performed: `False`
- audio_processing_performed: `False`
- training_performed: `False`

## Human Review Checklist
- Confirm proposed commands match musical intent.
- Confirm destructive edits are explicitly approved.
- Confirm generated candidates include provenance metadata.
- Confirm source-separated/transcribed evidence is treated as witness_not_truth.
- Confirm no private paths are present in reports.
- Confirm no real Ableton execution is requested.

## Proposed Ableton Commands
- `insert_generated_bridge` generated_candidate=`True`
- `thin_arrangement` generated_candidate=`False`
- `set_track_volume` generated_candidate=`False`
- `automate_device_parameter` generated_candidate=`False`

## Risk Warnings
- Dry-run only; no real Ableton connection or Live Set mutation.
- Destructive changes (thin_arrangement) require explicit human review.
- Unknown device/parameter targets are warnings for review, not execution success.
- Clamped set_track_volume from 1.2 to 1.0.
- Clamped automate_device_parameter point 0 value from -0.1 to 0.0.
- Clamped automate_device_parameter point 1 value from 1.4 to 1.0.
- Unknown device `Unknown_Device_X`; command kept as warning for manual review.
- Unknown parameter `Macro 9`; command kept as warning for manual review.
