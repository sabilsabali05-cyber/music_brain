# MIDI Stitching Architecture (Design Scaffold)

## Scope

This document describes a safe stitching architecture for combining per-window YourMT3 MIDI outputs into one performance-level MIDI for phrase-aware segmented runs.

Current segmentation/transcription behavior:

- Each transcription window includes context padding around a core region.
- Window metadata records:
  - `core_start_seconds` / `core_end_seconds`
  - `global_start_seconds` / `global_end_seconds`
  - `midi_path`
  - `status`

## Why Naive Concatenation Fails

Naively appending MIDI files in window order can duplicate or smear notes because:

- Context padding causes overlapping audio content across neighboring windows.
- Notes that begin in context may be re-predicted in adjacent windows.
- Tempo/program/meta events can conflict across window files.

Result: double notes, timing drift, and inconsistent track identity.

## Time Mapping Model

Each MIDI event starts in window-local time and must be mapped to global performance time.

Conceptually:

- `window_local_seconds` -> `global_seconds = window_global_start + window_local_seconds`
- But only events aligned to the window core region should be retained for default stitching.

Required metadata from manifest:

- Core interval: `core_start_seconds`, `core_end_seconds`
- Window interval: `global_start_seconds`, `global_end_seconds`
- Source linkage: `source_segment_ids`

## Core-Region Trimming

Default stitching should trim notes outside core coverage:

1. Convert MIDI ticks -> window-local seconds.
2. Convert window-local seconds -> global seconds.
3. Keep note events only when they intersect core interval.
4. Clip note boundaries at core edges when needed.

This prevents context-only duplicates from being merged as full notes.

## Overlap De-duplication

Even after core trimming, overlaps can happen at boundaries.

Use conservative de-duplication heuristics:

- Group note events by `(program, channel, pitch)`.
- Treat events within a small time tolerance as duplicates.
- Keep the event with stronger confidence proxy (or longer stable duration if confidence unavailable).
- Prefer earlier window for left edge, later window for right edge only when explicitly configured.

## Program/Track Identity Preservation

Merged output should preserve stable instrument identity:

- Keep per-window program changes but normalize to consistent track mapping.
- Preserve channel assignments when possible.
- Normalize duplicate meta messages (tempo, time signature, markers) to one canonical set.

## Artifact Layout

Keep both intermediate and final artifacts:

- Per-window MIDI remains in each track folder (`library/trk_*/midi/full_mix.mid`).
- Stitch report artifact for diagnostics (counts, dropped notes, overlap merges).
- Final merged MIDI stored under manifest run folder (proposed):
  - `samples/segments/<source>/<run_id>/midi/merged_full.mid`

## Failed Window Handling

If some windows fail:

- Do not block whole-run stitching by default.
- Produce partial merged MIDI with explicit warnings.
- Record missing ranges for downstream QA.
- Optionally enforce strict mode that aborts on any failed/missing window.

## Merge Validation

Validation checks should include:

- Monotonic event time ordering.
- No negative note durations.
- Reasonable note-on count vs window totals.
- Coverage report: merged timeline vs manifest duration.
- Parse/readability check with `mido`.

## Future Database Implications

When persistence is introduced later, store:

- Manifest-level merge metadata (version, tolerances, strict/partial mode).
- Per-window contribution stats.
- De-duplication decisions for auditability.
- Final merged MIDI pointer and checksum.

This keeps merge behavior reproducible and debuggable across model/algorithm updates.
