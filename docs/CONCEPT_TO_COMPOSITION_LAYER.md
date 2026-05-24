# Concept To Composition Layer

## Purpose

This layer converts conversation text into a structured `SongConceptBrief`, maps language to musical controls, and generates three local MIDI candidates with transparent evaluation reports.

## Pipeline

1. `conversation.md` is parsed by `features/concept_to_composition/conversation_parser.py`.
2. The parsed content becomes a validated `SongConceptBrief` in `concept_schema.py`.
3. Interpreter modules map language to theory, rhythm, and texture hooks:
   - `concept_interpreter.py`
   - `concept_to_theory.py`
   - `concept_to_texture.py`
   - `concept_to_generation_controls.py`
4. `concept_midi_generator.py` renders:
   - `candidate_01_harmony_first`
   - `candidate_02_rhythm_first`
   - `candidate_03_weird_but_musical`
5. Each candidate emits:
   - `full.mid`
   - stem MIDIs (`chords`, `bass`, `lead`, `texture`)
   - generation/alignment/provenance reports (`json` + `md`)
   - `review_sheet.md`
6. `scripts/evaluate_concept_generation.py` produces a comparative score report.

## Safety And Provenance Guarantees

- No cloud calls are used.
- No model training is performed.
- No model downloads are performed.
- No fake model execution claims are made.
- No audio processing is required.
- No private user paths are written to reports/docs.
- No Ableton or VST rendering is required.
- Real symbolic backend use is reported as `false` unless explicitly integrated with a smoke pass.

## Commands

- `scripts\dev.cmd create-song-concept-brief`
- `scripts\dev.cmd generate-midi-from-concept`
- `scripts\dev.cmd evaluate-concept-generation`
