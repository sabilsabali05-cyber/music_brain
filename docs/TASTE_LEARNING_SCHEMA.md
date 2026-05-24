# Taste Learning Schema

## Core Labels

`love`, `like`, `neutral`, `dislike`, `reject`

## Feedback Fields

- `feedback_id`
- `generation_id`
- `candidate_id`
- `authorization_status`
- `source_authorized_for_learning`
- `reviewer`
- `taste_label`
- `accepted`
- `musicality_score`
- `groove_score`
- `harmony_score`
- `notes`
- `tags`
- `blocked_by_policy`

## Rules

- Unauthorized rows are blocked from learning.
- Invalid labels are rejected.
- Scores are clamped to `[0.0, 1.0]`.
- No cloud calls or private-path expansion in ingestion/training artifacts.
