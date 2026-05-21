# Phrase-Aware Long Audio Architecture (Scaffold)

## Why not transcribe an hour in one request

- Long single-shot transcription is fragile: one failure can waste the entire run.
- Remote GPU cost becomes harder to control because retries are all-or-nothing.
- Observability is weaker: it is harder to localize quality issues to specific portions.
- Resume behavior is poor: partial progress cannot be reused cleanly.

## Why fixed-time chunks are not enough

- Musical phrases rarely align to rigid 60-second boundaries.
- Hard cuts can split notes, phrase endings, and section transitions.
- Blind fixed chunks reduce musical continuity for downstream analysis and retrieval.

## Two distinct concepts

1. **musical_segment**
   - Semantically meaningful unit (phrase/section/gesture boundary candidate).
   - Represents musical intent and timeline continuity.

2. **transcription_window**
   - Practical audio slice sent to YourMT3 with max-duration constraints.
   - Includes optional pre/post context padding for boundary robustness.

A musical segment may map 1:1, 1:many, or many:1 with transcription windows.

## Phrase-aware boundary candidates (future hybrid)

- Silence or low-energy gaps
- Onset-density shifts
- Harmonic/chroma change points
- Beat/bar and tempo grid transitions
- Recurrence/self-similarity novelty peaks
- Repeated motif or section boundary signals

This scaffold keeps these as strategy targets and does not overclaim full phrase detection quality yet.

## Safe fallback strategy

- Use fixed windows with context when phrase confidence is low or unavailable.
- Manifest should clearly mark fallback strategy, for example:
  - `fixed_with_context`
  - `hybrid_scaffold`

## Length and overlap guidance

- Suggested core window target: 45-90 seconds
- Suggested max window length: 90 seconds
- Suggested minimum meaningful segment: 10-15 seconds
- Suggested context padding: 3-8 seconds (pre and post)

## Timeline integrity

- Every segment/window stores global offsets from performance start.
- Preserve both:
  - core interval (`core_start_seconds`, `core_end_seconds`)
  - padded transcription interval (`global_start_seconds`, `global_end_seconds`)

## Context-aware retrieval design (future DB-ready contract)

- Store `previous_segment_id` / `next_segment_id` for linear neighbors.
- Store optional context graph relations for non-linear links (repetition, variation, call-response).
- Retrieval should return:
  - target segment
  - immediate neighbors
  - parent performance metadata
  - window-level transcription artifacts and quality/state flags

## Future MIDI stitching and overlap de-duplication

- Keep per-window MIDI artifacts first.
- Stitching layer should:
  - align overlapping windows on global offsets
  - remove duplicate events in overlap spans
  - preserve source window provenance for debugging

## Modal cost/resume strategy

- Manifest is the source of truth for resumability.
- Each window has explicit status (`pending`, `running`, `success`, `failed`).
- Resume should skip successful windows unless forced.
- Process small batches (`--max-windows`) to cap spend and validate quality early.
