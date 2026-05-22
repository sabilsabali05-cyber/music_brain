# External Model Witness Architecture

This architecture adds optional external witness outputs without turning them into truth labels.

## Roles

- **YourMT3**: transcription backbone (audio -> MIDI)
- **pretty_midi**: MIDI event observation parser
- **librosa**: transparent baseline features
- **Essentia**: MIR descriptor witness
- **BeatNet/madmom**: beat/downbeat/meter witness
- **music21**: symbolic theory witness
- **musicnn / Essentia TF**: semantic witness
- **Omnizart**: optional comparison witness
- **Groove MIDI Dataset (E-GMD)**: calibration reference only

## Adapter Contract

Adapters in `features/external_analyzers/` implement:

- `check_available()`
- `analyze_audio(audio_path, context)`
- `analyze_midi(midi_path, context)` (optional)

Each output is structured as:

- provider identity
- status (`success`, `unavailable`, `failed`, `skipped`)
- compact feature payload
- warnings/limitations
- dependency info
- model source reference

## Orchestration

Use scripts:

- `scripts/check_model_sources.py`
- `scripts/check_external_analyzers.py`
- `scripts/run_external_witnesses.py`
- `scripts/compare_model_witnesses.py`
- `scripts/build_model_consensus.py`

`run_external_witnesses` writes provider outputs under:

- `features/performances/<performance_id>/<segment_run_id>/external_model_features/`

Expected files:

- `essentia_features.json`
- `musicnn_features.json`
- `beat_tracker_features.json`
- `music21_features.json`
- `omnizart_availability.json`
- `model_witness_comparison.json`
- `model_consensus.json`

## Consensus Policy

Consensus outputs are recommendations:

- agreements
- disagreements
- confidence boosts/penalties
- unresolved conflicts
- provider limitations
- recommended review items

Consensus does **not** convert witness outputs to ground truth.

## Data Discipline

- Export layers keep references and compact summaries only.
- Large vectors/arrays are not embedded per JSONL record.
- External witness absence should not break the pipeline.
