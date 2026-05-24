# Ableton Agent Change Plan

- status: `planned_dry_run_only`
- ableton_connected: `False`
- live_set_modified: `False`
- commands_generated: `True`
- commands_executed: `False`
- human_review_required: `True`

## Interpreted Musical Intent
- Increase contrast and lift before the ending chorus.

## Proposed Arrangement Changes
- Target sections for edits: bridge, chorus_2.
- Reserve an 8-bar bridge lane for candidate insertion and transition shaping.
- Preserve existing chorus anchors while previewing structural changes in dry-run only.

## Proposed Generated Candidates Needed
- `bridge_candidate_001` (generated_candidate_not_final)

## Proposed Ableton Commands
- `insert_generated_bridge` review_required=`True`
- `thin_arrangement` review_required=`True`
- `set_track_volume` review_required=`True`
- `automate_device_parameter` review_required=`True`

## Risk Warnings
- Dry-run only; no real Ableton connection or Live Set mutation.
- Destructive changes (thin_arrangement) require explicit human review.
- Unknown device/parameter targets are warnings for review, not execution success.
