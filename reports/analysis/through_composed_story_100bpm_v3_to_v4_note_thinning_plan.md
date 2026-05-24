# Through-Composed Story v3 to v4 Note Thinning Plan

## Classification counts
- `essential_chord_tone`: `86`
- `emotional_tension`: `448`
- `melodic_anchor`: `67`
- `rhythmic_identity`: `782`
- `transition_voiceleading`: `148`
- `texture_support`: `160`
- `passing_tone`: `11`
- `ornament`: `12`
- `duplicate`: `15`
- `clutter`: `0`
- `accidental_clash`: `179`
- `low_emotional_value`: `61`

## Pre-thinning density by section
- `intro_tension`: `250` notes
- `lift`: `433` notes
- `conflict`: `543` notes
- `breakthrough`: `360` notes
- `resolution`: `383` notes

## Accidental clashes (target for fixes)
- bar `6` tracks `Bass, Melody` interval `2` overlap `0.5`
- bar `9` tracks `Bass, MotionHarmony` interval `10` overlap `0.65`
- bar `9` tracks `Melody, MotionHarmony` interval `2` overlap `0.45`
- bar `9` tracks `Melody, MotionHarmony` interval `10` overlap `0.421`
- bar `10` tracks `Bass, Melody` interval `10` overlap `0.85`
- bar `10` tracks `Bass, Melody` interval `10` overlap `0.5`
- bar `10` tracks `Bass, Melody` interval `10` overlap `0.5`
- bar `10` tracks `Bass, Melody` interval `10` overlap `0.5`
- bar `10` tracks `Melody, MotionHarmony` interval `10` overlap `0.421`
- bar `10` tracks `Melody, MotionHarmony` interval `6` overlap `0.421`
- bar `10` tracks `Melody, MotionHarmony` interval `6` overlap `0.421`
- bar `10` tracks `Melody, MotionHarmony` interval `6` overlap `0.421`

## Intentional dissonances to keep
- bar `1` tracks `Melody, PadSwells` interval `2` overlap `0.24`
- bar `1` tracks `Melody, PadSwells` interval `2` overlap `0.24`
- bar `1` tracks `Melody, PadSwells` interval `10` overlap `0.24`
- bar `1` tracks `Melody, PadSwells` interval `10` overlap `0.24`
- bar `1` tracks `Melody, MotionHarmony` interval `10` overlap `0.171`
- bar `1` tracks `Bass, Melody` interval `10` overlap `0.5`
- bar `1` tracks `Bass, Melody` interval `10` overlap `0.85`
- bar `2` tracks `MotionHarmony, PadSwells` interval `1` overlap `0.421`
- bar `2` tracks `Bass, Melody` interval `2` overlap `0.4`
- bar `2` tracks `Melody, PadSwells` interval `2` overlap `0.5`
- bar `2` tracks `Bass, Melody` interval `2` overlap `0.75`
- bar `2` tracks `Melody, PadSwells` interval `2` overlap `0.75`

## Rhythmic cells preserved
- bar `21` positions `[0.0, 0.0, 0.0, 0.5, 0.5, 0.5]` count `8`
- bar `13` positions `[0.0, 0.0, 0.0, 0.5, 0.5, 1.0]` count `5`
- bar `11` positions `[0.0, 0.0, 0.0, 0.0, 0.5, 1.0]` count `4`
- bar `2` positions `[0.0, 0.0, 0.0, 0.5, 1.0, 1.0]` count `4`
- bar `17` positions `[0.0, 0.0, 0.0, 0.0, 0.0, 0.5]` count `2`
- bar `10` positions `[0.0, 0.0, 0.0, 0.0, 0.5, 0.5]` count `2`

## Harmonic/chord movement preserved
- bars `1-2` root `50 -> 48` (`-2` semitones)
- bars `2-3` root `48 -> 46` (`-2` semitones)
- bars `4-5` root `45 -> 50` (`5` semitones)
- bars `5-6` root `50 -> 48` (`-2` semitones)
- bars `6-7` root `48 -> 46` (`-2` semitones)
- bars `8-9` root `45 -> 53` (`8` semitones)
- bars `9-10` root `53 -> 55` (`2` semitones)
- bars `10-11` root `55 -> 57` (`2` semitones)
- bars `11-12` root `57 -> 52` (`-5` semitones)
- bars `12-13` root `52 -> 50` (`-2` semitones)

## Thinning policy execution order
1. Keep core emotional/harmonic/rhythmic classes.
2. Keep only resolving passing tones.
3. Reduce masking support textures.
4. Remove duplicate notes unless weight is needed.
5. Remove clutter and low-emotional-value notes.
6. Resolve accidental clashes via soften/shorten/octave/delete.
7. Prefer softening before deletion for color notes.
8. Preserve phrase rests and breath space.
9. In busy bars, prioritize dominant voice and support it.
10. Keep weirdness that contributes to tension/release/groove.
