# Through-Composed Story v2 to v3 Plan

## Sections with strongest personality
- `breakthrough` score `3.894` (offbeat `0.577`, density `43.75`)
- `conflict` score `3.868` (offbeat `0.574`, density `43.417`)
- `lift` score `3.67` (offbeat `0.512`, density `42.4`)

## Best chord movement
- bars `8-9`: root `45 -> 53` (8 semitones)
- bars `38-39`: root `57 -> 50` (-7 semitones)
- bars `30-31`: root `52 -> 58` (6 semitones)
- bars `4-5`: root `45 -> 50` (5 semitones)
- bars `11-12`: root `57 -> 52` (-5 semitones)
- bars `16-17`: root `57 -> 52` (-5 semitones)

## Interesting rhythms
- source bar `20` cell `[0.0, 0.5, 1.0, 1.5, 1.5, 2.0]`; develop via `repeat with one displaced rest and one anticipation`
- source bar `41` cell `[0.0, 0.0, 0.5, 1.0, 1.0, 1.5]`; develop via `repeat with one displaced rest and one anticipation`
- source bar `21` cell `[0.0, 0.5, 0.5, 1.0, 1.25, 1.75]`; develop via `repeat with one displaced rest and one anticipation`
- source bar `17` cell `[0.0, 0.0, 0.0, 0.5, 1.0, 1.0]`; develop via `repeat with one displaced rest and one anticipation`

## Too-busy sections
- bar_01_intro_tension
- bar_02_intro_tension
- bar_03_intro_tension
- bar_04_intro_tension
- bar_05_intro_tension
- bar_06_intro_tension
- bar_07_intro_tension
- bar_08_intro_tension
- bar_09_lift
- bar_10_lift
- bar_11_lift
- bar_12_lift
- bar_13_lift
- bar_14_lift

## Accidental clashes
- bar `24` tracks `Bass, Melody` interval_class `6` overlap_beats `0.65`
- bar `30` tracks `Bass, Melody` interval_class `6` overlap_beats `0.65`
- bar `24` tracks `Melody, MotionHarmony` interval_class `6` overlap_beats `0.421`
- bar `30` tracks `Melody, MotionHarmony` interval_class `2` overlap_beats `0.421`
- bar `30` tracks `Bass, Melody` interval_class `1` overlap_beats `1.25`
- bar `24` tracks `Bass, Melody` interval_class `1` overlap_beats `0.75`
- bar `24` tracks `Bass, Melody` interval_class `1` overlap_beats `0.5`
- bar `23` tracks `Melody, MotionHarmony` interval_class `1` overlap_beats `0.421`
- bar `24` tracks `Bass, Melody` interval_class `1` overlap_beats `0.5`
- bar `30` tracks `Melody, MotionHarmony` interval_class `6` overlap_beats `0.421`
- bar `24` tracks `Bass, Melody` interval_class `10` overlap_beats `0.9`
- bar `20` tracks `Bass, Melody` interval_class `2` overlap_beats `0.75`
- bar `30` tracks `Bass, Melody` interval_class `10` overlap_beats `0.75`
- bar `30` tracks `Bass, Melody` interval_class `1` overlap_beats `0.5`
- bar `26` tracks `Bass, Melody` interval_class `2` overlap_beats `0.4`
- bar `24` tracks `Melody, MotionHarmony` interval_class `1` overlap_beats `0.421`

## Clashes that can be intentional tensions
- bar `1` tracks `Bass, Melody` interval_class `10` overlap_beats `0.85`
- bar `2` tracks `Bass, Melody` interval_class `2` overlap_beats `0.9`
- bar `6` tracks `Melody, MotionHarmony` interval_class `2` overlap_beats `0.421`
- bar `6` tracks `Bass, Melody` interval_class `2` overlap_beats `0.5`
- bar `6` tracks `Melody, PadSwells` interval_class `2` overlap_beats `0.25`
- bar `6` tracks `Melody, PadSwells` interval_class `2` overlap_beats `0.5`
- bar `6` tracks `Melody, MotionHarmony` interval_class `10` overlap_beats `0.25`
- bar `6` tracks `Melody, MotionHarmony` interval_class `10` overlap_beats `0.25`
- bar `6` tracks `Melody, PadSwells` interval_class `11` overlap_beats `0.5`
- bar `7` tracks `Melody, PadSwells` interval_class `1` overlap_beats `1.0`
- bar `7` tracks `Melody, MotionHarmony` interval_class `2` overlap_beats `0.171`
- bar `7` tracks `Melody, PadSwells` interval_class `2` overlap_beats `0.5`
- bar `9` tracks `Melody, PadSwells` interval_class `1` overlap_beats `0.75`
- bar `9` tracks `Counterline, Melody` interval_class `1` overlap_beats `0.4`
- bar `9` tracks `Bass, MotionHarmony` interval_class `1` overlap_beats `0.171`
- bar `9` tracks `Bass, PadSwells` interval_class `1` overlap_beats `0.9`

## Register-separation opportunities
- Keep Bass mostly <= MIDI 55 while Melody remains >= MIDI 60 in dense bars.
- Push pad and sustained harmony toward middle register (MIDI 48-76) under lead peaks.
- Use Counterline as high-mid response voice to avoid masking Melody attacks.

## Velocity-reduction opportunities
- Reduce supportive layers (PadSwells/Counterline) by 8-16 velocity in bars with polyphony > 5.
- Keep dominant voice accents while lowering duplicate harmony attacks.
- Trim stacked peak hits where combined velocity pressures exceed 120.

## Motifs to preserve
- appears `3`x, example bar `20`, positions `[0.0, 0.5, 1.0, 1.5, 1.5, 2.0]`
- appears `2`x, example bar `41`, positions `[0.0, 0.0, 0.5, 1.0, 1.0, 1.5]`
- appears `2`x, example bar `21`, positions `[0.0, 0.5, 0.5, 1.0, 1.25, 1.75]`
- appears `1`x, example bar `17`, positions `[0.0, 0.0, 0.0, 0.5, 1.0, 1.0]`

## Rhythmic cells to develop
- bar `20` positions `[0.0, 0.5, 1.0, 1.5, 1.5, 2.0]`
- bar `41` positions `[0.0, 0.0, 0.5, 1.0, 1.0, 1.5]`
- bar `21` positions `[0.0, 0.5, 0.5, 1.0, 1.25, 1.75]`
- bar `17` positions `[0.0, 0.0, 0.0, 0.5, 1.0, 1.0]`

## Harmonic gestures to extend
- bars `8-9` gesture `root move 8 semitones` strategy `approach upper-extension voicing before arrival`
- bars `38-39` gesture `root move -7 semitones` strategy `approach upper-extension voicing before arrival`
- bars `30-31` gesture `root move 6 semitones` strategy `approach upper-extension voicing before arrival`
- bars `4-5` gesture `root move 5 semitones` strategy `approach upper-extension voicing before arrival`
- bars `11-12` gesture `root move -5 semitones` strategy `approach upper-extension voicing before arrival`
