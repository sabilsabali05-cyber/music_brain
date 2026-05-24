# Canonical Music Corpus Schema

This document defines the canonical schema used to normalize DB-like music artifacts into a policy-gated corpus for retrieval and future training preparation.

## Canonical Fields

The canonical row must contain exactly the following fields:

- `item_id`
- `source_artifact`
- `source_type`
- `source_path_redacted`
- `authorization_status`
- `training_allowed`
- `production_use_allowed`
- `retrieval_allowed`
- `review_status`
- `review_reason`
- `policy_status`
- `excluded_reason`
- `split`
- `human_rating`
- `keep_reject_label`
- `harmony_quality`
- `melody_quality`
- `rhythm_quality`
- `texture_quality`
- `arrangement_quality`
- `emotional_quality`
- `weirdness_quality`
- `musicality_quality`
- `tags`
- `provenance`
- `created_at`
- `normalized_at`

## Policy Defaults (Strict)

- Missing `training_allowed` defaults to `false`.
- Missing `authorization_status` defaults to `review_required`.
- Missing `review_status` defaults to `review_required`.
- Missing label fields remain explicitly unlabeled (`keep_reject_label=unlabeled`, numeric labels null).
- Splice/production-only sources are retrieval-only by default (`retrieval_allowed=true`, `training_allowed=false`) unless explicit override exists.
- Generated MIDI is only eligible for preference/ranker uses after human review; supervised training remains blocked by default.
- Public reports must not contain raw private/local paths; all source paths are redacted.

## Promotion Rules

- Train/validation can only include accepted + reviewed rows.
- Train/validation can only include rows where `training_allowed=true`.
- Rows with missing policy fields cannot enter train/validation.
- Rows with sparse or missing labels are routed to retrieval-only or review/ranker pools.
- Split assignment must be deterministic and provenance-preserving.

