# Theory and Model Sources

This document defines how theory references and model/tool providers are used in this project.

## Core Principle

- Theory sources and model outputs are **evidence and framing**, not automatic ground truth.
- External models are treated as **witnesses**.
- Weak labels can only be upgraded through stronger evidence, consensus, and/or human review.

## Theory Sources

Theory references are registered in `features/theory_sources.py` with:

- `source_id`
- bibliographic info (`title`, `author`)
- domain and concepts
- targeted feature families
- supported label types
- limitations and trust policy

Covered areas include rhythm/time, harmony/pitch movement, counterpoint, post-tonal analysis, and microtonal frameworks.

## Model Sources

Model/tool providers are registered in `features/model_sources.py` with:

- provider metadata (`provider_id`, `provider_name`)
- input/output types
- strengths and weaknesses
- trust policy
- implementation/dependency status
- local availability status

Included providers:

- YourMT3 (transcription backbone)
- pretty_midi (symbolic MIDI parser)
- librosa (transparent baseline)
- Essentia (descriptor witness)
- BeatNet/madmom/beat tracker witness
- music21 (symbolic theory witness)
- musicnn / Essentia TF (semantic witnesses)
- Omnizart (optional comparison witness)
- Groove MIDI Dataset / E-GMD (calibration reference; no automatic download)

## Trust Mapping

- `raw_observation` / `derived_observation`: direct parse/feature evidence
- `model_prediction` / `weak_label`: interpretive or model-level candidates
- `external_witness`: corroborative provider output
- `calibration_reference`: fixture/evaluation guidance

## Safety and Compliance

- No unauthorized audio extraction.
- No third-party API upload by default.
- No automatic dependency installation.
- No automatic dataset download.
