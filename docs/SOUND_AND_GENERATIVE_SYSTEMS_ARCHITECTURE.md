# Sound And Generative Systems Architecture

## System Components

The architecture separates composition intelligence from sound-system control so the model can learn musical intent and production execution together.

- **Composition brain:** plans song form, arrangement intent, and MIDI-level structure.
- **Sound seed selection brain:** chooses local sample-library material as seed inputs for downstream sound systems.
- **Synplant engine:** treated as a local patch-generation and sound-growing engine driven by selected sample seeds.
- **Pure Data engine:** treated as a generative patch and control-system engine for rhythm, texture, modulation, and transformations.
- **Max for Live/Ableton host:** routes MIDI/audio/control, hosts devices, and renders stems/final outputs.

## End-To-End Flow

1. Composition brain produces arrangement and role intent.
2. Sound seed selection chooses role-aligned local samples.
3. Synplant generates candidate patches from selected seeds.
4. Pure Data templates or generated candidates are selected/configured for track roles.
5. Human/model ranking picks best Synplant and/or Pure Data candidates.
6. Max for Live/Ableton handles routing, control mapping, and rendering.
7. Feedback from rendered stems and ratings is logged for future learning.

## Feedback Loop

Training data should capture:

- selected seed sample and reasoning
- Synplant candidate set and chosen patch
- Pure Data template/candidate and chosen parameters
- Ableton/Max routing and macro controls
- rendered stems and mix outcomes
- human ratings and model ratings for role fit and mix fit

## Why This Goes Beyond MIDI

MIDI alone does not encode timbre architecture, patch behavior, control topology, or production routing decisions. A serious model should learn:

- sound seed selection quality
- patch/system candidate ranking quality
- parameter/control mapping decisions
- routing/rendering consequences in the host environment

This is why the architecture focuses on sound selection and patch/system control alongside note generation.
