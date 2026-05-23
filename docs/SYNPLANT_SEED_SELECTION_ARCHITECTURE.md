# Synplant Seed Selection Architecture

## Intent

Synplant is treated as a local sound-growing and synth-patch engine, not as a fully automated replacement for composition-aware sound design. The architecture prioritizes selecting strong source samples from a local sample library before asking Synplant to generate candidate patches.

## Core Flow

1. AI selects source audio seeds from a local sample library for a composition role.
2. Synplant uses those seeds to generate multiple candidate patches.
3. A human, a model, or a hybrid process ranks and selects the best patch.
4. Max for Live and Ableton consume the selected Synplant patch for the target track role.
5. The full loop is logged for future training and quality review.

## Why Seed-First Instead of Direct Synthesis

- It keeps texture generation grounded in known, authorized local material.
- It avoids brittle "generate every sound from scratch" assumptions.
- It makes human-in-the-loop review practical while automation remains partial.
- It creates reusable supervision signals: seed choice quality, candidate ranking quality, and role-to-mix fit quality.

## Data To Capture For Training

Training data should capture this chain in each session:

- `seed` -> chosen source sample from local library
- `synplant_candidates` -> candidate patch refs and rendered previews
- `selected_patch` -> chosen patch + selection reason
- `song_role` -> bass/lead/pad/percussion/etc.
- `rendered_result` -> rendered patch audio reference used in arrangement
- `feedback` -> human/model ratings and fit-to-role/mix signals

## Human-In-The-Loop Requirement

The system must support manual sessions because Synplant automation may be unavailable or incomplete. Generation methods are tracked as:

- `manual`
- `semi_automated`
- `automated_unknown`

## Integration Boundary

This phase defines schema and architecture only. It does not automate Synplant, does not process audio, and does not modify existing MIDI generation or transcription logic.
