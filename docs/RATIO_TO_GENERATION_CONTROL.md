# Ratio To Generation Control

This layer maps evidence-backed ratio observations to controllable composition actions.

## Principles

- Evidence-only: controls are derived from observed symbolic/features data.
- Honest unknowns: missing data remains `unavailable` or `unknown` and is not fabricated.
- No forced universal ratio: `golden_ratio_phi` is optional and only applied when supported.
- Ratio guidance is bounded: musicality and battle appeal remain primary unless feedback supports stronger ratio weighting.

## Domain Mapping

- `section` -> timeline anchors (climax/pivot boundaries)
- `phrase` -> phrase-length proportionality
- `rhythm` -> subdivision and groove weighting
- `harmonic` -> harmonic rhythm / interval pacing
- `motif` -> motif return spacing / arrangement density hints

## Control Surface

The generator consumes `GenerationControlSpec` + `RatioControl` objects to expose:

- target ratios and tolerance windows
- strict vs soft guidance modes
- confidence-based weighting
- provenance (`source_observation_ids`)

## Confidence And Implication

- High confidence + within tolerance -> stronger control update.
- Medium confidence -> soft influence only.
- Unavailable/unknown evidence -> no hard control; attach metadata notes.

